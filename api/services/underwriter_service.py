"""
Underwriter Service
UnderwriterAgent를 API 환경에 맞게 래핑하는 서비스
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Awaitable
import traceback

from agents.core.logging import get_logger
from agents.underwriter_agent import UnderwriterAgent
from ..models import UnderwriteRequest, UnderwriteResult, ProcessingStep, TaskStatus
from ..config import get_api_settings
from .task_manager import get_task_manager, TaskInfo

settings = get_api_settings()
logger = get_logger("underwriter_service")


class UnderwriterService:
    """인수심사 서비스"""
    
    def __init__(self):
        self.task_manager = get_task_manager()
        logger.info("underwriter_service_initialized")
    
    async def process_underwrite_request(self, task_id: str, request: UnderwriteRequest) -> Dict[str, Any]:
        """
        인수심사 요청 처리
        
        Args:
            task_id: 작업 ID
            request: 인수심사 요청
            
        Returns:
            처리 결과
        """
        
        logger.info("underwrite_processing_started", 
                   task_id=task_id, 
                   request_id=request.request_id,
                   user_input_length=len(request.user_input))
        
        # 진행률 콜백 함수
        async def progress_callback(step_name: str, percentage: float, step_result: Optional[Dict] = None):
            task_info = await self.task_manager.get_task_status(task_id)
            if task_info:
                task_info.update_progress(step_name, percentage)
                
                if step_result:
                    # 단계 완료 정보 추가
                    processing_step = ProcessingStep(
                        name=step_name,
                        status="completed" if percentage >= 100 else "processing",
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow() if percentage >= 100 else None
                    )
                    task_info.add_step_info(processing_step)
                
                logger.info("progress_updated", 
                           task_id=task_id,
                           step=step_name, 
                           percentage=percentage)
        
        try:
            # UnderwriterAgent 생성
            agent = UnderwriterAgent(
                simulation_years=request.options.simulation_years,
                enable_audit_trail=request.options.enable_audit_trail
            )
            
            await progress_callback("initializing", 5.0)
            
            # 디버그 모드에 따른 실행 방식 선택
            if request.options.debug_mode:
                result = await self._run_debug_mode(agent, request, progress_callback)
            else:
                result = await self._run_normal_mode(agent, request, progress_callback)
            
            await progress_callback("completed", 100.0)
            
            # API 형태로 결과 변환
            api_result = await self._convert_to_api_result(result, request)
            
            logger.info("underwrite_processing_completed", 
                       task_id=task_id,
                       success=api_result.get("status") == "success")
            
            return api_result
            
        except asyncio.CancelledError:
            logger.info("underwrite_processing_cancelled", task_id=task_id)
            raise
        except Exception as e:
            logger.error("underwrite_processing_failed", 
                        task_id=task_id,
                        error=str(e),
                        traceback=traceback.format_exc())
            
            # 에러 결과 반환
            return await self._create_error_result(str(e), request)
    
    async def _run_normal_mode(
        self, 
        agent: UnderwriterAgent, 
        request: UnderwriteRequest,
        progress_callback: Callable
    ) -> Dict[str, Any]:
        """일반 모드 실행"""
        
        await progress_callback("processing", 10.0)
        
        # 일반 모드로 실행 (내부적으로 step-by-step 사용)
        result = await agent.run(request.user_input)
        
        return result
    
    async def _run_debug_mode(
        self, 
        agent: UnderwriterAgent, 
        request: UnderwriteRequest,
        progress_callback: Callable
    ) -> Dict[str, Any]:
        """디버그 모드 실행 (단계별 진행률 업데이트)"""
        
        steps = [
            ("peril_canvas", "Peril Canvas 생성", 20.0),
            ("prior_extraction", "Prior 추출", 40.0),
            ("scenario_generation", "시나리오 생성", 60.0),
            ("pricing_calculation", "가격 계산", 80.0),
            ("pricing_report", "리포트 생성", 95.0)
        ]
        
        step_results = await agent.run_step_by_step(request.user_input)
        
        # 각 단계 결과를 확인하며 진행률 업데이트
        for step_key, step_name, percentage in steps:
            step_result = step_results.get(f"step{len([s for s in steps if s[2] <= percentage])}_{step_key}")
            
            if step_result:
                await progress_callback(step_name, percentage, step_result)
                
                if step_result.get("status") == "error":
                    raise RuntimeError(f"{step_name} 실패: {step_result.get('error')}")
        
        # 최종 결과 확인
        final_step = step_results.get("step5_pricing_report")
        if final_step and final_step["status"] == "success":
            return final_step["final_result"]
        else:
            raise RuntimeError("디버그 모드에서 최종 결과를 생성하지 못했습니다")
    
    async def _convert_to_api_result(self, agent_result: Dict[str, Any], request: UnderwriteRequest) -> Dict[str, Any]:
        """에이전트 결과를 API 형태로 변환"""
        
        if agent_result.get("status") != "success":
            return await self._create_error_result(
                agent_result.get("error", "Unknown error"), 
                request
            )
        
        # UnderwriteResult 모델에 맞게 변환
        api_result = {
            "status": "success",
            "expected_loss": agent_result.get("expected_loss"),
            "gross_premium": agent_result.get("gross_premium"),
            "risk_level": agent_result.get("risk_level"),
            "loss_ratio": agent_result.get("loss_ratio"),
            "coefficient_of_variation": agent_result.get("coefficient_of_variation"),
            "var_99": agent_result.get("var_99"),
            "tvar_99": agent_result.get("tvar_99"),
            "simulation_years": agent_result.get("simulation_years"),
            
            "validation_passed": agent_result.get("validation_passed", False),
            "validation_checks": agent_result.get("dashboard", {}).get("validation_checks"),
            "alerts": agent_result.get("dashboard", {}).get("alerts"),
            
            "event_type": agent_result.get("summary", {}).get("event_type"),
            "recommendation": agent_result.get("summary", {}).get("recommendation"),
            "executive_summary": agent_result.get("executive_summary"),
            
            "audit_trail": agent_result.get("audit_trail") if request.options.enable_audit_trail else None
        }
        
        # 전체 결과도 포함 (호환성을 위해)
        api_result["_raw_result"] = agent_result
        
        return api_result
    
    async def _create_error_result(self, error_message: str, request: UnderwriteRequest) -> Dict[str, Any]:
        """에러 결과 생성"""
        
        return {
            "status": "error",
            "error": error_message,
            "expected_loss": None,
            "gross_premium": None,
            "risk_level": None,
            "loss_ratio": None,
            "coefficient_of_variation": None,
            "var_99": None,
            "tvar_99": None,
            "simulation_years": request.options.simulation_years,
            "validation_passed": False,
            "validation_checks": None,
            "alerts": [f"Processing failed: {error_message}"],
            "event_type": None,
            "recommendation": "Please review the input and try again",
            "executive_summary": None,
            "audit_trail": None,
            "error_details": {
                "timestamp": datetime.utcnow().isoformat(),
                "user_input": request.user_input,
                "options": request.options.dict()
            }
        }
    
    async def validate_request(self, request: UnderwriteRequest) -> Optional[str]:
        """요청 검증"""
        
        try:
            # 기본 검증은 Pydantic에서 처리되므로 비즈니스 로직 검증만
            
            # 사용자 입력 길이 검증
            if len(request.user_input.strip()) < 5:
                return "User input is too short (minimum 5 characters)"
            
            if len(request.user_input) > 2000:
                return "User input is too long (maximum 2000 characters)"
            
            # 시뮬레이션 연수 검증
            if request.options.simulation_years < 10:
                return "Simulation years too low (minimum 10)"
            
            if request.options.simulation_years > 50000:
                return "Simulation years too high (maximum 50,000)"
            
            # 리스크 프리미엄 검증
            if not (0.0 <= request.options.market_risk_premium <= 2.0):
                return "Market risk premium must be between 0.0 and 2.0"
            
            # Webhook URL 검증 (설정된 경우)
            if (request.callback.type == "webhook" and 
                request.callback.webhook and 
                request.callback.webhook.url):
                
                url = str(request.callback.webhook.url)
                if not (url.startswith("http://") or url.startswith("https://")):
                    return "Invalid webhook URL scheme (must be http or https)"
                
                # localhost는 프로덕션에서 제한할 수 있음
                if "localhost" in url or "127.0.0.1" in url:
                    if not settings.debug:
                        return "Localhost webhook URLs are not allowed in production"
            
            return None  # 검증 통과
            
        except Exception as e:
            logger.error("request_validation_error", error=str(e))
            return f"Request validation failed: {str(e)}"
    
    async def estimate_processing_time(self, request: UnderwriteRequest) -> int:
        """예상 처리 시간 계산 (초)"""
        
        base_time = 60  # 기본 1분
        
        # 시뮬레이션 연수에 따른 추가 시간
        if request.options.simulation_years > 1000:
            additional_time = (request.options.simulation_years - 1000) // 1000 * 10
            base_time += min(additional_time, 300)  # 최대 5분 추가
        
        # 디버그 모드는 약간 더 오래 걸림
        if request.options.debug_mode:
            base_time = int(base_time * 1.2)
        
        # 감사 추적 활성화 시 추가 시간
        if request.options.enable_audit_trail:
            base_time += 10
        
        return min(base_time, settings.task_timeout_seconds - 30)  # 타임아웃 30초 전


# 전역 UnderwriterService 인스턴스
_underwriter_service: Optional[UnderwriterService] = None


def get_underwriter_service() -> UnderwriterService:
    """UnderwriterService 싱글톤 인스턴스 반환"""
    global _underwriter_service
    if _underwriter_service is None:
        _underwriter_service = UnderwriterService()
    return _underwriter_service