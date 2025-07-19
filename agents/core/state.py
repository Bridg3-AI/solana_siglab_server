from typing import Dict, Any, List, Optional, TypedDict
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    """V0.1 Minimal Agent State for Insurance MVP"""
    messages: List[Dict[str, Any]]  # 대화 내역
    plan: str  # Planner 생성 Plan
    result: Optional[Dict[str, Any]]  # Tool 실행 결과
    event_type: Optional[str]  # 이벤트 타입
    tool_calls: Optional[List[str]]  # 호출할 도구 목록
    tool_parameters: Optional[Dict[str, Any]]  # 도구 파라미터
    event_data: Optional[Dict[str, Any]]  # 수집된 이벤트 데이터  
    loss_ratio: Optional[float]  # 계산된 손해율


class InsuranceAgentState(AgentState):
    """Extended state for insurance-specific agents"""
    event_type: Optional[str]  # 이벤트 타입 (예: typhoon, flight_delay)
    event_data: Optional[Dict[str, Any]]  # 수집된 이벤트 데이터
    loss_ratio: Optional[float]  # 계산된 손해율
    tool_calls: List[str]  # 호출된 도구 목록


class LLMPricingState(AgentState):
    """LLM-Lite Parametric Pricing을 위한 확장 상태"""
    # Pricing 워크플로 관련 필드
    peril_canvas: Optional[Dict[str, Any]]  # PerilCanvas 데이터
    frequency_prior: Optional[Dict[str, Any]]  # FrequencyPrior 데이터
    severity_prior: Optional[Dict[str, Any]]  # SeverityPrior 데이터
    scenarios: Optional[Dict[str, Any]]  # 시나리오 데이터 (summary + data)
    pricing_result: Optional[Dict[str, Any]]  # PricingResult 데이터
    
    # 감사 추적 관련 필드
    audit_trail: Optional[Dict[str, Any]]  # AuditTrail 데이터
    llm_conversations: Optional[List[Dict[str, str]]]  # LLM 대화 기록
    validation_checks: Optional[Dict[str, bool]]  # 검증 결과
    
    # 추가 메타데이터
    process_id: Optional[str]  # 프로세스 고유 ID
    pricing_mode: Optional[str]  # "llm_lite" | "traditional"
    simulation_years: Optional[int]  # 시뮬레이션 연수 (기본 1000)