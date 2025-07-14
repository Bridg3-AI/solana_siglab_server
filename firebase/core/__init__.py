"""
Firebase core functionality
"""

from .firebase_init import get_db, get_storage, verify_token, firebase_app
from .exceptions import *
from .logging import logger, log_function_call, log_agent_interaction, log_error

__all__ = [
    "get_db",
    "get_storage",
    "verify_token", 
    "firebase_app",
    "logger",
    "log_function_call",
    "log_agent_interaction", 
    "log_error",
    # Exceptions
    "SolanaError",
    "AgentError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ServiceUnavailableError",
    "RateLimitError",
    "NetworkError"
]