"""
Agent interaction models
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class AgentRequest(BaseModel):
    message: str
    session_id: Optional[str] = "anonymous"
    user_id: Optional[str] = None
    network: str = "mainnet-beta"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    response: str
    context: Dict[str, Any] = Field(default_factory=dict)
    tools_used: List[str] = Field(default_factory=list)
    iterations: int = 0
    intent: Optional[str] = None
    session_id: Optional[str] = None
    error: Optional[str] = None


class ConversationMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationHistory(BaseModel):
    session_id: str
    conversation: List[ConversationMessage] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthCheck(BaseModel):
    status: str = "healthy"
    timestamp: Optional[str] = None
    agents_available: bool = False
    services: Dict[str, bool] = Field(default_factory=dict)