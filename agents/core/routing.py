"""
Conditional routing system for LangGraph node dependencies
CLAUDE.md 개선사항: 노드간 의존성 검증을 위한 조건부 라우팅 구현
"""

from typing import Dict, Any, List, Optional, Callable
from .state import AgentState
from .logging import get_logger

logger = get_logger("conditional_router")


def validate_state_dependencies(state: AgentState, required_keys: List[str]) -> tuple[bool, List[str]]:
    """
    상태에서 필수 키들이 존재하는지 검증
    
    Args:
        state: 현재 상태
        required_keys: 필수 키 목록
        
    Returns:
        (검증_통과, 누락된_키들)
    """
    missing_keys = []
    for key in required_keys:
        if key not in state or state[key] is None:
            missing_keys.append(key)
    
    return len(missing_keys) == 0, missing_keys


def create_conditional_edge(
    source_node: str,
    condition_func: Callable[[AgentState], str],
    edge_map: Dict[str, str]
) -> Callable[[AgentState], str]:
    """
    조건부 엣지 생성기
    
    Args:
        source_node: 소스 노드 이름
        condition_func: 조건 함수
        edge_map: 조건 결과 -> 다음 노드 매핑
        
    Returns:
        라우팅 함수
    """
    def routing_function(state: AgentState) -> str:
        try:
            condition_result = condition_func(state)
            next_node = edge_map.get(condition_result, "error")
            
            logger.info(
                "conditional_routing",
                source_node=source_node,
                condition_result=condition_result,
                next_node=next_node
            )
            
            return next_node
            
        except Exception as e:
            logger.error(
                "routing_error",
                source_node=source_node,
                error=str(e)
            )
            return "error"
    
    return routing_function


def pricing_pipeline_router(state: AgentState) -> str:
    """
    LLM-Lite Pricing 파이프라인을 위한 조건부 라우터
    
    각 단계의 의존성을 검증하고 다음 노드를 결정
    """
    
    # 1. Peril Canvas 존재 여부 확인
    if not state.get("peril_canvas"):
        logger.info("routing_to_peril_canvas", reason="missing_canvas")
        return "peril_canvas_node"
    
    # 2. Prior 데이터 존재 여부 확인
    if not all([state.get("frequency_prior"), state.get("severity_prior")]):
        is_valid, missing = validate_state_dependencies(
            state, ["peril_canvas"]
        )
        if is_valid:
            logger.info("routing_to_prior_extraction", reason="missing_priors")
            return "prior_extraction_node"
        else:
            logger.warning("dependency_check_failed", 
                         step="prior_extraction", 
                         missing_deps=missing)
            return "error"
    
    # 3. 시나리오 데이터 존재 여부 확인
    if not state.get("scenarios"):
        is_valid, missing = validate_state_dependencies(
            state, ["peril_canvas", "frequency_prior", "severity_prior"]
        )
        if is_valid:
            logger.info("routing_to_scenario_generation", reason="missing_scenarios")
            return "scenario_generation_node"
        else:
            logger.warning("dependency_check_failed", 
                         step="scenario_generation", 
                         missing_deps=missing)
            return "error"
    
    # 4. 가격책정 결과 존재 여부 확인
    if not state.get("pricing_result"):
        is_valid, missing = validate_state_dependencies(
            state, ["scenarios"]
        )
        if is_valid:
            logger.info("routing_to_pricing_calculation", reason="missing_pricing")
            return "pricing_calculation_node"
        else:
            logger.warning("dependency_check_failed", 
                         step="pricing_calculation", 
                         missing_deps=missing)
            return "error"
    
    # 5. 최종 리포트 생성
    is_valid, missing = validate_state_dependencies(
        state, ["peril_canvas", "pricing_result", "scenarios"]
    )
    if is_valid:
        logger.info("routing_to_pricing_report", reason="final_step")
        return "pricing_report_node"
    else:
        logger.warning("dependency_check_failed", 
                     step="pricing_report", 
                     missing_deps=missing)
        return "error"


def error_handler_router(state: AgentState) -> str:
    """
    에러 상황을 위한 라우터
    """
    error_info = state.get("result", {})
    if isinstance(error_info, dict) and error_info.get("error"):
        logger.error("pipeline_error_detected", error=error_info["error"])
        return "END"
    
    return "END"


def create_pricing_pipeline_edges():
    """
    LLM-Lite Pricing 파이프라인을 위한 조건부 엣지 설정
    
    Returns:
        엣지 설정 딕셔너리
    """
    return {
        "START": pricing_pipeline_router,
        "peril_canvas_node": lambda state: (
            "prior_extraction_node" 
            if state.get("peril_canvas") and not state.get("result", {}).get("error")
            else "error"
        ),
        "prior_extraction_node": lambda state: (
            "scenario_generation_node"
            if all([state.get("frequency_prior"), state.get("severity_prior")]) 
               and not state.get("result", {}).get("error")
            else "error"
        ),
        "scenario_generation_node": lambda state: (
            "pricing_calculation_node"
            if state.get("scenarios") and not state.get("result", {}).get("error")
            else "error"
        ),
        "pricing_calculation_node": lambda state: (
            "pricing_report_node"
            if state.get("pricing_result") and not state.get("result", {}).get("error")
            else "error"
        ),
        "pricing_report_node": lambda state: "END",
        "error": error_handler_router
    }


def log_pipeline_state(state: AgentState, step: str):
    """
    파이프라인 상태를 로깅하는 유틸리티 함수
    """
    state_keys = list(state.keys())
    completed_steps = []
    
    if state.get("peril_canvas"):
        completed_steps.append("peril_canvas")
    if state.get("frequency_prior") and state.get("severity_prior"):
        completed_steps.append("prior_extraction")
    if state.get("scenarios"):
        completed_steps.append("scenario_generation")
    if state.get("pricing_result"):
        completed_steps.append("pricing_calculation")
    if state.get("result", {}).get("status") == "success":
        completed_steps.append("pricing_report")
    
    logger.info(
        "pipeline_state_check",
        current_step=step,
        completed_steps=completed_steps,
        total_keys=len(state_keys),
        has_errors=bool(state.get("result", {}).get("error"))
    )