"""Insurance Agent V0.1 - LangGraph Implementation"""
import asyncio
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from .core.state import AgentState
from .core.planner import planner_node
from .core.router import tool_router
from .core.executor import executor_layer


class InsuranceAgent:
    """Insurance Agent V0.1 using LangGraph"""
    
    def __init__(self):
        self.graph = self._create_graph()
        self.agent = self.graph.compile()
    
    def _create_graph(self) -> StateGraph:
        """Create and configure the LangGraph"""
        graph = StateGraph(AgentState)
        
        # Add nodes
        graph.add_node("planner", planner_node)
        graph.add_node("tool_router", tool_router)
        graph.add_node("executor", executor_layer)
        
        # Add edges
        graph.add_edge("planner", "tool_router")
        graph.add_edge("tool_router", "executor")
        graph.add_edge("executor", END)
        
        # Set entry point
        graph.set_entry_point("planner")
        
        return graph
    
    async def run(self, user_input: str) -> Dict[str, Any]:
        """
        Run the insurance agent with user input
        
        Args:
            user_input: User's natural language request
            
        Returns:
            Final result from the agent
        """
        # Initialize state
        initial_state = {
            "messages": [{"role": "user", "content": user_input}],
            "plan": "",
            "result": None,
            "event_type": None,
            "tool_calls": None,
            "tool_parameters": None,
            "event_data": None,
            "loss_ratio": None
        }
        
        try:
            # Run the graph
            result = await self.agent.ainvoke(initial_state)
            
            # Extract final result
            final_result = result.get("result", {})
            loss_ratio = result.get("loss_ratio")
            
            # Format response for CLI
            if loss_ratio is not None:
                return {
                    "loss_ratio": loss_ratio,
                    "summary": final_result.get("summary", {}),
                    "event_data": final_result.get("event_data", {}),
                    "status": "success"
                }
            elif "loss_ratio" in final_result:
                return {
                    "loss_ratio": final_result["loss_ratio"],
                    "summary": final_result.get("summary", {}),
                    "event_data": final_result.get("event_data", {}),
                    "status": "success"
                }
            else:
                return {
                    "error": final_result.get("error", "Unknown error"),
                    "status": "error"
                }
                
        except Exception as e:
            return {
                "error": f"Agent execution failed: {str(e)}",
                "status": "error"
            }
    
    def get_graph_image(self) -> str:
        """Get graph visualization (for debugging)"""
        try:
            return self.graph.get_graph().draw_mermaid()
        except:
            return "Graph visualization not available"


# Convenience function for direct usage
async def run_insurance_agent(user_input: str) -> Dict[str, Any]:
    """
    Run the insurance agent with user input
    
    Args:
        user_input: User's natural language request
        
    Returns:
        Final result from the agent
    """
    agent = InsuranceAgent()
    return await agent.run(user_input)


# Test function
async def test_agent():
    """Test the agent with sample input"""
    test_input = "태풍 손해율을 계산해줘"
    result = await run_insurance_agent(test_input)
    print(f"Test result: {result}")


if __name__ == "__main__":
    asyncio.run(test_agent())