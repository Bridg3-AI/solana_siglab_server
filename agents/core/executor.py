"""Executor node for running tools and processing results"""
from typing import Dict, Any, List, Optional
from ..tools.insurance import collect_event_data, calculate_loss_ratio
from .state import AgentState


async def executor_layer(state: AgentState) -> Dict[str, Any]:
    """
    Executor node: Execute tools based on router decisions
    
    Args:
        state: Current agent state with tool parameters
        
    Returns:
        Updated state with execution results
    """
    tool_calls = state.get("tool_calls", [])
    tool_parameters = state.get("tool_parameters", {})
    
    if not tool_calls:
        return {
            "result": {"error": "실행할 도구가 없습니다."},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": "실행할 도구가 없습니다."}
            ]
        }
    
    # 도구 실행 결과 저장
    execution_results = {}
    event_data = None
    
    try:
        # 순차적으로 도구 실행
        for tool_name in tool_calls:
            result = await execute_tool(tool_name, tool_parameters, event_data)
            execution_results[tool_name] = result
            
            # collect_event_data 결과를 다음 도구에서 사용
            if tool_name == "collect_event_data":
                event_data = result
        
        # 최종 결과 구성
        final_result = prepare_final_result(execution_results, tool_calls)
        
        # 기존 상태 유지하면서 업데이트
        updated_state = dict(state)
        updated_state.update({
            "result": final_result,
            "event_data": event_data,
            "loss_ratio": execution_results.get("calculate_loss_ratio"),
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": f"도구 실행 완료: {len(tool_calls)}개 도구 실행됨"}
            ]
        })
        
        return updated_state
        
    except Exception as e:
        error_msg = f"도구 실행 중 오류 발생: {str(e)}"
        updated_state = dict(state)
        updated_state.update({
            "result": {"error": error_msg},
            "messages": state.get("messages", []) + [
                {"role": "assistant", "content": error_msg}
            ]
        })
        return updated_state


async def execute_tool(tool_name: str, tool_parameters: Dict[str, Any], event_data: Optional[Dict[str, Any]] = None) -> Any:
    """
    Execute a specific tool with given parameters
    
    Args:
        tool_name: Name of the tool to execute
        tool_parameters: Parameters for the tool
        event_data: Event data from previous tool execution
        
    Returns:
        Tool execution result
    """
    tool_params = tool_parameters.get(tool_name, {})
    
    if tool_name == "collect_event_data":
        event_type = tool_params.get("event_type", "general")
        return await collect_event_data.ainvoke({"event_type": event_type})
    
    elif tool_name == "calculate_loss_ratio":
        if event_data is None:
            raise ValueError("calculate_loss_ratio requires event_data from collect_event_data")
        return await calculate_loss_ratio.ainvoke({"event_data": event_data})
    
    else:
        raise ValueError(f"Unknown tool: {tool_name}")


def prepare_final_result(execution_results: Dict[str, Any], tool_calls: List[str]) -> Dict[str, Any]:
    """
    Prepare final result from all tool executions
    
    Args:
        execution_results: Results from all tool executions
        tool_calls: List of called tools
        
    Returns:
        Final formatted result
    """
    result = {
        "tools_executed": tool_calls,
        "timestamp": "2024-07-17T10:30:00Z"
    }
    
    # 이벤트 데이터 포함
    if "collect_event_data" in execution_results:
        result["event_data"] = execution_results["collect_event_data"]
    
    # 손해율 포함
    if "calculate_loss_ratio" in execution_results:
        result["loss_ratio"] = execution_results["calculate_loss_ratio"]
    
    # 요약 정보 생성
    if "loss_ratio" in result:
        result["summary"] = {
            "event_type": result.get("event_data", {}).get("event_type", "unknown"),
            "loss_ratio": result["loss_ratio"],
            "risk_level": classify_risk_level(result["loss_ratio"]),
            "recommendation": generate_recommendation(result["loss_ratio"])
        }
    
    return result


def classify_risk_level(loss_ratio: float) -> str:
    """
    Classify risk level based on loss ratio
    
    Args:
        loss_ratio: Calculated loss ratio
        
    Returns:
        Risk level classification
    """
    if loss_ratio < 0.1:
        return "low"
    elif loss_ratio < 0.3:
        return "medium"
    elif loss_ratio < 0.6:
        return "high"
    else:
        return "very_high"


def generate_recommendation(loss_ratio: float) -> str:
    """
    Generate recommendation based on loss ratio
    
    Args:
        loss_ratio: Calculated loss ratio
        
    Returns:
        Recommendation text
    """
    if loss_ratio < 0.1:
        return "낮은 위험도: 보험 상품 출시 권장"
    elif loss_ratio < 0.3:
        return "중간 위험도: 추가 분석 후 신중한 출시"
    elif loss_ratio < 0.6:
        return "높은 위험도: 보험료 조정 필요"
    else:
        return "매우 높은 위험도: 보험 상품 출시 비권장"