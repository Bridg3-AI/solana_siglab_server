"""LangGraph agents package"""
# V0.1 Implementation - Import new insurance agent
try:
    from .insurance_agent import InsuranceAgent, run_insurance_agent
    __all__ = ["InsuranceAgent", "run_insurance_agent"]
except ImportError:
    # Fallback for old implementation
    from .agent import create_solana_agent, run_solana_agent, graph
    from .utils import (
        AgentState,
        SolanaAgentState,
        ConversationState,
        AgentConfig,
        get_solana_tools,
        get_tool_by_name
    )

    __all__ = [
        "create_solana_agent",
        "run_solana_agent", 
        "graph",
        "AgentState",
        "SolanaAgentState",
        "ConversationState", 
        "AgentConfig",
        "get_solana_tools",
        "get_tool_by_name"
    ]