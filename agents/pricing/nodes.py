"""
LangGraph Nodes for LLM-Lite Parametric Pricing

LangGraph 워크플로에서 사용할 노드 함수들을 정의합니다.
"""

from typing import Dict, Any, List
import asyncio

from .peril_canvas import PerilCanvasGenerator
from .prior_extraction import PriorExtractor
from .scenario_generator import SyntheticScenarioGenerator
from .monte_carlo_pricer import MonteCarloPricer
from .pricing_reporter import PricingReporter
from .models.base import PerilCanvas, FrequencyPrior, SeverityPrior, PricingResult
from ..core.state import AgentState


async def peril_canvas_node(state: AgentState) -> Dict[str, Any]:
    """
    Peril Canvas 생성 노드 (STEP 0)
    
    Args:
        state: 현재 에이전트 상태
        
    Returns:
        업데이트된 상태 (peril_canvas 포함)
    """
    
    print("🎯 [NODE] peril_canvas_node 시작")
    
    # 사용자 입력 추출
    if not state.get("messages"):
        return {
            "result": {"error": "사용자 메시지가 없습니다."},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": "사용자 입력이 필요합니다."}
            ]
        }
    
    last_message = state["messages"][-1]
    user_input = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)
    
    try:
        # Peril Canvas 생성
        print(f"🔧 [NODE] PerilCanvasGenerator 생성 중...")
        generator = PerilCanvasGenerator()
        print(f"🔧 [NODE] Canvas 생성 시작: {user_input}")
        canvas = await generator.generate_canvas_from_input(user_input)
        print(f"🔧 [NODE] Canvas 생성 완료: {type(canvas)}")
        
        # Canvas 검증
        is_valid, validation_errors = await generator.validate_canvas(canvas)
        
        if not is_valid:
            return {
                "result": {"error": f"Canvas 검증 실패: {', '.join(validation_errors)}"},
                "messages": state.get("messages", []) + [
                    {"role": "assistant", "content": f"Canvas 생성 실패: {validation_errors[0] if validation_errors else '알 수 없는 오류'}"}
                ]
            }
        
        # 상태 업데이트
        updated_state = dict(state)
        updated_state.update({
            "peril_canvas": canvas.dict(),
            "event_type": canvas.peril,
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"Peril Canvas 생성 완료: {canvas.peril} ({canvas.region})"}
            ]
        })
        
        print(f"🎯 [NODE] peril_canvas_node 완료: {canvas.peril}")
        return updated_state
        
    except Exception as e:
        error_msg = f"Peril Canvas 생성 중 오류: {str(e)}"
        updated_state = dict(state)
        updated_state.update({
            "result": {"error": error_msg},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": error_msg}
            ]
        })
        return updated_state


async def prior_extraction_node(state: AgentState) -> Dict[str, Any]:
    """
    Prior 추출 노드 (STEP 1)
    
    Args:
        state: 현재 에이전트 상태 (peril_canvas 필요)
        
    Returns:
        업데이트된 상태 (frequency_prior, severity_prior 포함)
    """
    
    print("📊 [NODE] prior_extraction_node 시작")
    
    # Peril Canvas 확인
    canvas_data = state.get("peril_canvas")
    if not canvas_data:
        return {
            "result": {"error": "Peril Canvas가 없습니다."},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": "Prior 추출을 위해 Peril Canvas가 필요합니다."}
            ]
        }
    
    try:
        # Peril Canvas 객체 복원
        canvas = PerilCanvas(**canvas_data)
        
        # Prior 추출
        extractor = PriorExtractor()
        frequency_prior, severity_prior = await extractor.extract_priors(canvas)
        
        # 상태 업데이트
        updated_state = dict(state)
        updated_state.update({
            "frequency_prior": frequency_prior.dict(),
            "severity_prior": severity_prior.dict(),
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"Prior 추출 완료: {frequency_prior.distribution} (빈도), {severity_prior.distribution} (심도)"}
            ]
        })
        
        print(f"📊 [NODE] prior_extraction_node 완료: {frequency_prior.distribution}, {severity_prior.distribution}")
        return updated_state
        
    except Exception as e:
        error_msg = f"Prior 추출 중 오류: {str(e)}"
        print(f"❌ [NODE] prior_extraction_node 에러: {error_msg}")
        import traceback
        traceback.print_exc()
        
        updated_state = dict(state)
        updated_state.update({
            "result": {"error": error_msg},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": error_msg}
            ]
        })
        return updated_state


async def scenario_generation_node(state: AgentState) -> Dict[str, Any]:
    """
    시나리오 생성 노드 (STEP 2)
    
    Args:
        state: 현재 에이전트 상태 (peril_canvas, frequency_prior, severity_prior 필요)
        
    Returns:
        업데이트된 상태 (scenarios 포함)
    """
    
    # 필요한 데이터 확인
    canvas_data = state.get("peril_canvas")
    frequency_data = state.get("frequency_prior")
    severity_data = state.get("severity_prior")
    
    if not all([canvas_data, frequency_data, severity_data]):
        missing = []
        if not canvas_data: missing.append("peril_canvas")
        if not frequency_data: missing.append("frequency_prior")
        if not severity_data: missing.append("severity_prior")
        
        return {
            "result": {"error": f"시나리오 생성에 필요한 데이터가 없습니다: {', '.join(missing)}"},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"시나리오 생성 실패: {', '.join(missing)} 데이터 필요"}
            ]
        }
    
    try:
        # 객체 복원
        canvas = PerilCanvas(**canvas_data)
        frequency_prior = FrequencyPrior(**frequency_data)
        severity_prior = SeverityPrior(**severity_data)
        
        # 시나리오 생성
        generator = SyntheticScenarioGenerator(random_seed=42)  # 재현가능한 결과
        scenarios_df = await generator.generate_scenarios(
            canvas, frequency_prior, severity_prior, years=1000
        )
        
        # 시나리오 요약 통계
        scenario_summary = generator.get_scenario_summary(scenarios_df)
        
        # DataFrame을 JSON 직렬화 가능한 형태로 변환
        scenarios_data = {
            "summary": scenario_summary,
            "data": scenarios_df.to_dict('records')  # 리스트 형태로 변환
        }
        
        # 상태 업데이트
        updated_state = dict(state)
        updated_state.update({
            "scenarios": scenarios_data,
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"시나리오 생성 완료: {len(scenarios_df):,}년 시뮬레이션, 평균 연간 손실 ${scenario_summary['mean_annual_loss']:,.0f}"}
            ]
        })
        
        return updated_state
        
    except Exception as e:
        error_msg = f"시나리오 생성 중 오류: {str(e)}"
        updated_state = dict(state)
        updated_state.update({
            "result": {"error": error_msg},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": error_msg}
            ]
        })
        return updated_state


async def pricing_calculation_node(state: AgentState) -> Dict[str, Any]:
    """
    가격 계산 노드 (STEP 3)
    
    Args:
        state: 현재 에이전트 상태 (scenarios 필요)
        
    Returns:
        업데이트된 상태 (pricing_result 포함)
    """
    
    # 시나리오 데이터 확인
    scenarios_data = state.get("scenarios")
    event_type = state.get("event_type", "unknown")
    
    if not scenarios_data:
        return {
            "result": {"error": "시나리오 데이터가 없습니다."},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": "가격 계산을 위해 시나리오 데이터가 필요합니다."}
            ]
        }
    
    try:
        # DataFrame 복원
        import pandas as pd
        scenarios_df = pd.DataFrame(scenarios_data["data"])
        
        # 가격 계산
        pricer = MonteCarloPricer()
        pricing_result = pricer.calculate_pricing(
            scenarios_df,
            peril=event_type,
            market_risk_premium=0.15,
            enable_tail_padding=True
        )
        
        # 상태 업데이트
        updated_state = dict(state)
        updated_state.update({
            "pricing_result": pricing_result.dict(),
            "loss_ratio": pricing_result.expected_loss / pricing_result.gross_premium if pricing_result.gross_premium > 0 else 0,
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"가격 계산 완료: EL ${pricing_result.expected_loss:,.0f}, 보험료 ${pricing_result.gross_premium:,.0f}, 리스크 레벨 {pricing_result.risk_level.value}"}
            ]
        })
        
        return updated_state
        
    except Exception as e:
        error_msg = f"가격 계산 중 오류: {str(e)}"
        updated_state = dict(state)
        updated_state.update({
            "result": {"error": error_msg},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": error_msg}
            ]
        })
        return updated_state


async def pricing_report_node(state: AgentState) -> Dict[str, Any]:
    """
    가격책정 리포트 노드 (STEP 4)
    
    Args:
        state: 현재 에이전트 상태 (모든 데이터 필요)
        
    Returns:
        최종 상태 (result 포함)
    """
    
    # 필요한 데이터 확인
    canvas_data = state.get("peril_canvas")
    pricing_data = state.get("pricing_result")
    scenarios_data = state.get("scenarios")
    
    if not all([canvas_data, pricing_data, scenarios_data]):
        missing = []
        if not canvas_data: missing.append("peril_canvas")
        if not pricing_data: missing.append("pricing_result")
        if not scenarios_data: missing.append("scenarios")
        
        return {
            "result": {"error": f"리포트 생성에 필요한 데이터가 없습니다: {', '.join(missing)}"},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"리포트 생성 실패: {', '.join(missing)} 데이터 필요"}
            ]
        }
    
    try:
        # 객체 복원
        import pandas as pd
        canvas = PerilCanvas(**canvas_data)
        pricing_result = PricingResult(**pricing_data)
        scenarios_df = pd.DataFrame(scenarios_data["data"])
        
        # 리포트 생성
        reporter = PricingReporter()
        
        # Sanity Dashboard 생성
        dashboard = reporter.generate_sanity_dashboard(pricing_result)
        
        # 가격책정 테이블 생성
        pricing_table = reporter.generate_pricing_table([pricing_result])
        
        # 경영진 요약 생성
        executive_summary = reporter.generate_executive_summary(pricing_result, canvas, dashboard)
        
        # 최종 결과 구성
        final_result = {
            "status": "success",
            "pricing_result": pricing_result.dict(),
            "dashboard": dashboard,
            "pricing_table": pricing_table.to_dict('records'),
            "executive_summary": executive_summary,
            "validation_passed": all(dashboard["validation_checks"].values()),
            
            # 기존 형식과의 호환성을 위한 필드들
            "loss_ratio": pricing_result.expected_loss / pricing_result.gross_premium if pricing_result.gross_premium > 0 else 0,
            "summary": {
                "event_type": pricing_result.peril,
                "risk_level": pricing_result.risk_level.value,
                "recommendation": pricing_result.recommendation
            },
            "event_data": {
                "expected_loss": pricing_result.expected_loss,
                "coefficient_of_variation": pricing_result.coefficient_of_variation,
                "simulation_years": pricing_result.simulation_years,
                "data_source": "LLM-Lite Parametric Pricing"
            }
        }
        
        # 상태 업데이트
        updated_state = dict(state)
        updated_state.update({
            "result": final_result,
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"리포트 생성 완료: {pricing_result.peril} 보험 상품 설계 및 가격책정 완료"}
            ]
        })
        
        return updated_state
        
    except Exception as e:
        error_msg = f"리포트 생성 중 오류: {str(e)}"
        updated_state = dict(state)
        updated_state.update({
            "result": {"error": error_msg, "status": "error"},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": error_msg}
            ]
        })
        return updated_state


# 편의 함수들
async def run_full_pricing_pipeline(user_input: str) -> Dict[str, Any]:
    """
    전체 LLM-Lite Pricing 파이프라인을 순차 실행하는 편의 함수
    
    Args:
        user_input: 사용자 입력
        
    Returns:
        최종 결과
    """
    
    # 초기 상태
    state = {
        "messages": [{"role": "user", "content": user_input}],
        "plan": "",
        "result": None,
        "event_type": None
    }
    
    try:
        # 1단계: Peril Canvas 생성
        state = await peril_canvas_node(state)
        if state.get("result", {}).get("error"):
            return state["result"]
        
        # 2단계: Prior 추출
        state = await prior_extraction_node(state)
        if state.get("result", {}).get("error"):
            return state["result"]
        
        # 3단계: 시나리오 생성
        state = await scenario_generation_node(state)
        if state.get("result", {}).get("error"):
            return state["result"]
        
        # 4단계: 가격 계산
        state = await pricing_calculation_node(state)
        if state.get("result", {}).get("error"):
            return state["result"]
        
        # 5단계: 리포트 생성
        state = await pricing_report_node(state)
        
        return state.get("result", {"error": "알 수 없는 오류", "status": "error"})
        
    except Exception as e:
        return {"error": f"파이프라인 실행 중 오류: {str(e)}", "status": "error"}


async def test_pricing_nodes():
    """노드들의 기본 동작 테스트"""
    
    test_input = "태풍 보험 상품을 설계해줘"
    
    print("🚀 LLM-Lite Parametric Pricing 노드 테스트 시작")
    print(f"입력: {test_input}")
    print("=" * 50)
    
    result = await run_full_pricing_pipeline(test_input)
    
    if result.get("status") == "success":
        print("✅ 파이프라인 실행 성공!")
        print(f"이벤트 타입: {result['summary']['event_type']}")
        print(f"기댓값 손실: ${result['pricing_result']['expected_loss']:,.0f}")
        print(f"권장 보험료: ${result['pricing_result']['gross_premium']:,.0f}")
        print(f"리스크 레벨: {result['summary']['risk_level']}")
        print(f"검증 통과: {result['validation_passed']}")
    else:
        print("❌ 파이프라인 실행 실패")
        print(f"오류: {result.get('error', '알 수 없는 오류')}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_pricing_nodes())