from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from .utils import (
    SolanaAgentState, 
    think_node, 
    act_node, 
    observe_node, 
    should_continue, 
    create_system_message
)


def create_solana_agent() -> StateGraph:
    """Create a Solana agent using LangGraph"""
    
    # Create the state graph
    workflow = StateGraph(SolanaAgentState)
    
    # Add nodes
    workflow.add_node("think", think_node)
    workflow.add_node("act", act_node)
    workflow.add_node("observe", observe_node)
    
    # Set entry point
    workflow.set_entry_point("think")
    
    # Add edges
    workflow.add_edge("think", "act")
    workflow.add_edge("act", "observe")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "observe",
        should_continue,
        {
            "continue": "think",
            "end": END
        }
    )
    
    return workflow.compile()


def run_solana_agent(user_input: str, **kwargs) -> dict:
    """Run the Solana agent with user input"""
    
    # Get configuration
    network = kwargs.get("network", "mainnet-beta")
    rpc_url = kwargs.get("rpc_url", "https://api.mainnet-beta.solana.com")
    max_iterations = kwargs.get("max_iterations", 10)
    session_id = kwargs.get("session_id")
    user_id = kwargs.get("user_id")
    
    # Create agent
    agent = create_solana_agent()
    
    # Initialize state
    initial_state = SolanaAgentState(
        messages=[create_system_message(), HumanMessage(content=user_input)],
        context={},
        tools_used=[],
        iteration_count=0,
        max_iterations=max_iterations,
        current_step="initialized",
        intent=None,
        session_id=session_id,
        user_id=user_id,
        solana_context={},
        network=network,
        rpc_url=rpc_url,
        last_balance_check=None,
        last_transaction=None
    )
    
    # Run agent
    try:
        final_state = agent.invoke(initial_state)
        
        # Extract response
        ai_messages = [msg for msg in final_state["messages"] 
                      if hasattr(msg, 'content') and not isinstance(msg, HumanMessage)]
        response = ai_messages[-1].content if ai_messages else "No response generated"
        
        return {
            "response": response,
            "context": final_state["context"],
            "tools_used": final_state["tools_used"],
            "iterations": final_state["iteration_count"],
            "intent": final_state.get("intent"),
            "solana_context": final_state["solana_context"]
        }
    
    except Exception as e:
        return {
            "response": f"Error running agent: {str(e)}",
            "context": {"error": True},
            "tools_used": [],
            "iterations": 0,
            "intent": None,
            "solana_context": {}
        }


# Alias for the main graph export
graph = create_solana_agent()