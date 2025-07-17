"""Router node for determining tool calls based on plan"""
from typing import Dict, Any, List, Optional
from .state import AgentState


async def tool_router(state: AgentState) -> Dict[str, Any]:
    """
    Router node: Analyze plan and determine which tools to call
    
    Args:
        state: Current agent state with plan
        
    Returns:
        Updated state with tool parameters
    """
    plan = state.get("plan", "")
    event_type = state.get("event_type", "general")
    
    if not plan:
        return {
            "result": {"error": "계획이 없어 도구를 선택할 수 없습니다."},
            "tool_calls": []
        }
    
    # 계획을 분석하여 필요한 도구 결정
    tools_to_call = determine_tools_from_plan(plan, event_type)
    
    # 도구 호출 파라미터 생성
    tool_params = generate_tool_parameters(tools_to_call, event_type)
    
    # 기존 상태 유지하면서 업데이트
    updated_state = dict(state)
    updated_state.update({
        "tool_calls": tools_to_call,
        "tool_parameters": tool_params,
        "messages": state.get("messages", []) + [
            {"role": "assistant", "content": f"도구 선택됨: {', '.join(tools_to_call)}"}
        ]
    })
    
    return updated_state


def determine_tools_from_plan(plan: str, event_type: str) -> List[str]:
    """
    Determine which tools to call based on the plan content
    
    Args:
        plan: Generated plan text
        event_type: Detected event type
        
    Returns:
        List of tool names to call
    """
    tools_to_call = []
    plan_lower = plan.lower()
    
    # 항상 이벤트 데이터 수집이 필요
    tools_to_call.append("collect_event_data")
    
    # 손해율 계산 키워드 확인
    loss_keywords = [
        "손해율", "위험", "확률", "빈도", "피해",
        "loss", "ratio", "risk", "probability", "damage"
    ]
    
    if any(keyword in plan_lower for keyword in loss_keywords):
        tools_to_call.append("calculate_loss_ratio")
    else:
        # 기본적으로 손해율 계산 포함
        tools_to_call.append("calculate_loss_ratio")
    
    return tools_to_call


def generate_tool_parameters(tools: List[str], event_type: str) -> Dict[str, Dict[str, Any]]:
    """
    Generate parameters for each tool call
    
    Args:
        tools: List of tool names
        event_type: Detected event type
        
    Returns:
        Dictionary mapping tool names to their parameters
    """
    params = {}
    
    for tool in tools:
        if tool == "collect_event_data":
            params[tool] = {
                "event_type": event_type
            }
        elif tool == "calculate_loss_ratio":
            # calculate_loss_ratio는 collect_event_data의 결과를 사용하므로
            # 실제 실행 시점에서 파라미터가 결정됨
            params[tool] = {
                "requires_event_data": True
            }
    
    return params


def should_call_tool(tool_name: str, plan: str, event_type: str) -> bool:
    """
    Determine if a specific tool should be called
    
    Args:
        tool_name: Name of the tool
        plan: Generated plan text
        event_type: Detected event type
        
    Returns:
        Boolean indicating if tool should be called
    """
    plan_lower = plan.lower()
    
    tool_keywords = {
        "collect_event_data": [
            "데이터", "정보", "수집", "조사", "통계",
            "data", "information", "collect", "gather"
        ],
        "calculate_loss_ratio": [
            "손해율", "계산", "위험도", "확률", "비율",
            "loss", "ratio", "calculate", "risk", "probability"
        ]
    }
    
    if tool_name in tool_keywords:
        keywords = tool_keywords[tool_name]
        return any(keyword in plan_lower for keyword in keywords)
    
    return False