from typing import Dict, Any, List, Optional, TypedDict
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


class AgentState(TypedDict):
    """State definition for LangGraph agents"""
    messages: List[BaseMessage]
    context: Dict[str, Any]
    tools_used: List[str]
    iteration_count: int
    max_iterations: int
    current_step: str
    intent: Optional[str]
    session_id: Optional[str]
    user_id: Optional[str]


class SolanaAgentState(AgentState):
    """Extended state for Solana-specific agents"""
    solana_context: Dict[str, Any]
    network: str  # mainnet-beta, devnet, testnet
    rpc_url: str
    last_balance_check: Optional[str]
    last_transaction: Optional[str]


class ConversationState(BaseModel):
    """Conversation state for memory management"""
    session_id: str
    user_id: Optional[str] = None
    created_at: str
    last_updated: str
    message_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    """Configuration for agent behavior"""
    max_iterations: int = 10
    enable_memory: bool = True
    memory_type: str = "local"  # local, firestore
    tools_enabled: List[str] = Field(default_factory=list)
    network: str = "mainnet-beta"
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    debug_mode: bool = False