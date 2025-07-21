"""
LLM-Lite Parametric Underwriter Agent

실측 데이터 없는 이벤트들에 대해 LLM 전문지식만으로 
파라메트릭 보험 상품을 자동 설계하고 인수심사하는 에이전트입니다.
"""

import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from .core.state import LLMPricingState

# LangGraph와 호환되는 딕셔너리 타입
class PricingStateDict(TypedDict, total=False):
    messages: List[Dict[str, str]]
    plan: str
    result: Optional[Dict[str, Any]]
    event_type: Optional[str]
    tool_calls: Optional[str]
    tool_parameters: Optional[Dict[str, Any]]
    event_data: Optional[Dict[str, Any]]
    loss_ratio: Optional[float]
    
    # Pricing 관련 필드
    peril_canvas: Optional[Dict[str, Any]]
    frequency_prior: Optional[Dict[str, Any]]
    severity_prior: Optional[Dict[str, Any]]
    scenarios: Optional[Dict[str, Any]]
    pricing_result: Optional[Dict[str, Any]]
    audit_trail: Optional[Dict[str, Any]]
    llm_conversations: Optional[List[Dict[str, str]]]
    validation_checks: Optional[Dict[str, bool]]
    
    # 메타데이터
    process_id: Optional[str]
    pricing_mode: Optional[str]
    simulation_years: Optional[int]

from .pricing.nodes import (
    peril_canvas_node,
    prior_extraction_node,
    scenario_generation_node,
    pricing_calculation_node,
    pricing_report_node
)


class UnderwriterAgent:
    """LLM-Lite Parametric Underwriter 에이전트"""
    
    def __init__(self, simulation_years: int = 1000, enable_audit_trail: bool = True):
        """
        Args:
            simulation_years: Monte Carlo 시뮬레이션 연수
            enable_audit_trail: 감사 추적 활성화 여부
        """
        self.simulation_years = simulation_years
        self.enable_audit_trail = enable_audit_trail
        self.graph = self._create_graph()
        self.agent = self.graph.compile()
    
    def _create_graph(self) -> StateGraph:
        """LLM-Lite Underwriting을 위한 LangGraph 생성"""
        
        graph = StateGraph(PricingStateDict)
        
        # 6단계 노드 추가
        graph.add_node("peril_canvas", peril_canvas_node)
        graph.add_node("prior_extraction", prior_extraction_node)
        graph.add_node("scenario_generation", scenario_generation_node)
        graph.add_node("pricing_calculation", pricing_calculation_node)
        graph.add_node("pricing_report", pricing_report_node)
        
        # 선형 워크플로 연결
        graph.add_edge("peril_canvas", "prior_extraction")
        graph.add_edge("prior_extraction", "scenario_generation")
        graph.add_edge("scenario_generation", "pricing_calculation")
        graph.add_edge("pricing_calculation", "pricing_report")
        graph.add_edge("pricing_report", END)
        
        # 진입점 설정
        graph.set_entry_point("peril_canvas")
        
        return graph
    
    async def run(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """
        LLM-Lite Parametric Underwriting 실행
        
        Args:
            user_input: 사용자의 자연어 요청
            **kwargs: 추가 옵션
                - simulation_years: 시뮬레이션 연수 (기본값 사용 시 생략)
                - market_risk_premium: 시장 리스크 프리미엄 (기본 0.15)
                - enable_tail_scenarios: Tail 시나리오 포함 여부 (기본 True)
                
        Returns:
            최종 인수심사 결과
        """
        
        # 프로세스 ID 생성
        process_id = f"llm_underwriter_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        # 초기 상태 구성
        initial_state = {
            # 기본 필드
            "messages": [{"role": "user", "content": user_input}],
            "plan": "",
            "result": None,
            "event_type": None,
            "tool_calls": None,
            "tool_parameters": None,
            "event_data": None,
            "loss_ratio": None,
            
            # LLM Pricing 확장 필드
            "peril_canvas": None,
            "frequency_prior": None,
            "severity_prior": None,
            "scenarios": None,
            "pricing_result": None,
            "audit_trail": None,
            "llm_conversations": [],
            "validation_checks": None,
            
            # 메타데이터
            "process_id": process_id,
            "pricing_mode": "llm_lite",
            "simulation_years": kwargs.get("simulation_years", self.simulation_years)
        }
        
        try:
            # 임시로 run_step_by_step 사용 (LangGraph ainvoke 문제 우회)
            print("🔄 LangGraph ainvoke 대신 step-by-step 실행 사용")
            step_results = await self.run_step_by_step(user_input)
            
            # 최종 단계 결과 확인
            final_step = step_results.get("step5_pricing_report")
            if final_step and final_step["status"] == "success":
                result = final_step["final_result"]
                
                # 성공 시 감사 추적 생성 (옵션)
                if self.enable_audit_trail:
                    # step-by-step에서는 final_state 대신 결과에서 데이터 추출
                    audit_trail = await self._create_audit_trail_from_result(result, user_input)
                    result["audit_trail"] = audit_trail
                
                # 기존 형식과의 호환성 보장
                return self._format_compatible_result(result)
            else:
                # 단계별 실행에서 실패한 경우
                error_msg = "단계별 실행 실패"
                for step_key, step_result in step_results.items():
                    if isinstance(step_result, dict) and step_result.get("error"):
                        error_msg = step_result["error"]
                        break
                
                return {
                    "status": "error",
                    "error": error_msg,
                    "process_id": process_id,
                    "pricing_mode": "llm_lite"
                }
                
        except Exception as e:
            return {
                "status": "error",
                "error": f"LLM-Lite Underwriting 실행 중 오류: {str(e)}",
                "process_id": process_id,
                "pricing_mode": "llm_lite"
            }
    
    def _format_compatible_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        기존 시스템과의 호환성을 위한 결과 포맷팅
        
        기존 run_agent.py가 기대하는 형식에 맞춰 결과를 구성합니다.
        """
        
        pricing_result = result.get("pricing_result", {})
        
        return {
            # 기존 형식 호환 필드들
            "status": "success",
            "loss_ratio": result.get("loss_ratio", 0),
            "summary": result.get("summary", {}),
            "event_data": result.get("event_data", {}),
            
            # LLM-Lite Pricing 추가 정보
            "pricing_mode": "llm_lite",
            "expected_loss": pricing_result.get("expected_loss", 0),
            "gross_premium": pricing_result.get("gross_premium", 0),
            "risk_level": pricing_result.get("risk_level", "unknown"),
            "coefficient_of_variation": pricing_result.get("coefficient_of_variation", 0),
            "var_99": pricing_result.get("var_99", 0),
            "tvar_99": pricing_result.get("tvar_99", 0),
            "simulation_years": pricing_result.get("simulation_years", 1000),
            
            # 검증 및 품질 정보
            "validation_passed": result.get("validation_passed", False),
            "dashboard": result.get("dashboard", {}),
            "executive_summary": result.get("executive_summary", ""),
            
            # 감사 추적 (옵션)
            "audit_trail": result.get("audit_trail")
        }
    
    async def _create_audit_trail(self, final_state: LLMPricingState, user_input: str) -> Optional[Dict[str, Any]]:
        """감사 추적 정보 생성"""
        
        try:
            from .pricing.pricing_reporter import PricingReporter
            from .pricing.models.base import (
                PerilCanvas, FrequencyPrior, SeverityPrior, PricingResult
            )
            import pandas as pd
            
            # 필요한 데이터 추출
            canvas_data = final_state.get("peril_canvas")
            frequency_data = final_state.get("frequency_prior")
            severity_data = final_state.get("severity_prior")
            scenarios_data = final_state.get("scenarios")
            pricing_data = final_state.get("pricing_result")
            
            if not all([canvas_data, frequency_data, severity_data, scenarios_data, pricing_data]):
                return None
            
            # 객체 복원
            canvas = PerilCanvas(**canvas_data)
            frequency_prior = FrequencyPrior(**frequency_data)
            severity_prior = SeverityPrior(**severity_data)
            scenarios_df = pd.DataFrame(scenarios_data["data"])
            pricing_result = PricingResult(**pricing_data)
            
            # 감사 추적 생성
            reporter = PricingReporter()
            audit_trail = reporter.create_audit_trail(
                process_id=final_state.get("process_id", "unknown"),
                user_input=user_input,
                canvas=canvas,
                frequency_prior=frequency_prior,
                severity_prior=severity_prior,
                scenarios=scenarios_df,
                pricing_result=pricing_result,
                llm_conversations=final_state.get("llm_conversations", [])
            )
            
            return audit_trail.dict()
            
        except Exception as e:
            # 감사 추적 생성 실패 시 None 반환 (핵심 기능에 영향 없음)
            return None
    
    async def _create_audit_trail_from_result(self, result: Dict[str, Any], user_input: str) -> Optional[Dict[str, Any]]:
        """결과 데이터로부터 감사 추적 정보 생성 (step-by-step용)"""
        
        try:
            # step-by-step 실행에서는 감사 추적을 간소화
            return {
                "process_id": result.get("process_id", "unknown"),
                "user_input": user_input,
                "execution_mode": "step_by_step",
                "timestamp": datetime.now().isoformat(),
                "result_summary": {
                    "status": result.get("status"),
                    "expected_loss": result.get("pricing_result", {}).get("expected_loss"),
                    "gross_premium": result.get("pricing_result", {}).get("gross_premium"),
                    "risk_level": result.get("pricing_result", {}).get("risk_level")
                }
            }
            
        except Exception as e:
            # 감사 추적 생성 실패 시 None 반환
            return None
    
    def get_graph_visualization(self) -> str:
        """그래프 시각화 (디버깅용)"""
        try:
            return self.graph.get_graph().draw_mermaid()
        except:
            return """
graph TD
    A[peril_canvas] --> B[prior_extraction]
    B --> C[scenario_generation]
    C --> D[pricing_calculation]
    D --> E[pricing_report]
    E --> F[END]
"""
    
    async def run_step_by_step(self, user_input: str) -> Dict[str, Any]:
        """
        단계별 실행 (디버깅 및 검증용)
        
        각 단계의 중간 결과를 확인할 수 있습니다.
        """
        
        process_id = f"debug_{datetime.now().strftime('%H%M%S')}"
        
        state = {
            "messages": [{"role": "user", "content": user_input}],
            "plan": "",
            "result": None,
            "event_type": None,
            "process_id": process_id,
            "pricing_mode": "llm_lite"
        }
        
        step_results = {}
        
        try:
            # 1단계: Peril Canvas
            print("🎯 1단계: Peril Canvas 생성...")
            state = await peril_canvas_node(state)
            result = state.get("result") or {}
            step_results["step1_peril_canvas"] = {
                "status": "success" if not result.get("error") else "error",
                "canvas": state.get("peril_canvas"),
                "error": result.get("error")
            }
            
            if step_results["step1_peril_canvas"]["status"] == "error":
                return step_results
            
            # 2단계: Prior 추출
            print("📊 2단계: Prior 추출...")
            state = await prior_extraction_node(state)
            result = state.get("result") or {}
            step_results["step2_prior_extraction"] = {
                "status": "success" if not result.get("error") else "error",
                "frequency_prior": state.get("frequency_prior"),
                "severity_prior": state.get("severity_prior"),
                "error": result.get("error")
            }
            
            if step_results["step2_prior_extraction"]["status"] == "error":
                return step_results
            
            # 3단계: 시나리오 생성
            print("🎲 3단계: 시나리오 생성...")
            state = await scenario_generation_node(state)
            result = state.get("result") or {}
            step_results["step3_scenario_generation"] = {
                "status": "success" if not result.get("error") else "error",
                "scenario_summary": state.get("scenarios", {}).get("summary") if state.get("scenarios") else None,
                "error": result.get("error")
            }
            
            if step_results["step3_scenario_generation"]["status"] == "error":
                return step_results
            
            # 4단계: 가격 계산
            print("💰 4단계: 가격 계산...")
            state = await pricing_calculation_node(state)
            result = state.get("result") or {}
            step_results["step4_pricing_calculation"] = {
                "status": "success" if not result.get("error") else "error",
                "pricing_result": state.get("pricing_result"),
                "error": result.get("error")
            }
            
            if step_results["step4_pricing_calculation"]["status"] == "error":
                return step_results
            
            # 5단계: 리포트 생성
            print("📋 5단계: 리포트 생성...")
            state = await pricing_report_node(state)
            result = state.get("result") or {}
            step_results["step5_pricing_report"] = {
                "status": "success" if result.get("status") == "success" else "error",
                "final_result": result,
                "error": result.get("error")
            }
            
            print("✅ 모든 단계 완료!")
            return step_results
            
        except Exception as e:
            step_results["error"] = f"단계별 실행 중 오류: {str(e)}"
            return step_results


# 편의 함수들
async def run_llm_lite_underwriting(user_input: str, **kwargs) -> Dict[str, Any]:
    """간편한 LLM-Lite Underwriting 실행 함수"""
    agent = UnderwriterAgent(**kwargs)
    return await agent.run(user_input)


async def run_underwriting_step_by_step(user_input: str) -> Dict[str, Any]:
    """간편한 단계별 실행 함수"""
    agent = UnderwriterAgent()
    return await agent.run_step_by_step(user_input)


# 테스트 함수
async def test_underwriter_agent():
    """UnderwriterAgent 기본 동작 테스트"""
    
    test_cases = [
        "태풍 보험 상품을 설계해줘",
        "게임 서버 다운타임 보험",
        "항공편 지연에 대한 파라메트릭 보험",
        "지진 위험 보험 상품"
    ]
    
    agent = UnderwriterAgent(simulation_years=100)  # 테스트용 적은 연수
    
    for i, test_input in enumerate(test_cases, 1):
        print(f"\n🧪 테스트 {i}: {test_input}")
        print("=" * 50)
        
        try:
            result = await agent.run(test_input)
            
            if result.get("status") == "success":
                print(f"✅ 성공")
                print(f"   이벤트: {result.get('summary', {}).get('event_type', 'unknown')}")
                print(f"   기댓값 손실: ${result.get('expected_loss', 0):,.0f}")
                print(f"   보험료: ${result.get('gross_premium', 0):,.0f}")
                print(f"   리스크 레벨: {result.get('risk_level', 'unknown')}")
                print(f"   검증 통과: {result.get('validation_passed', False)}")
            else:
                print(f"❌ 실패: {result.get('error', '알 수 없는 오류')}")
                
        except Exception as e:
            print(f"❌ 예외 발생: {str(e)}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_underwriter_agent())