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