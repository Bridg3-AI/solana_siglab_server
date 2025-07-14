"""
Custom exceptions for the application
Following Firebase 2025 error handling best practices
"""
from typing import Optional, Dict, Any


class SolanaError(Exception):
    """Base exception for Solana-related errors"""
    def __init__(self, message: str, code: str = "SOLANA_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class AgentError(Exception):
    """Base exception for agent-related errors"""
    def __init__(self, message: str, code: str = "AGENT_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(Exception):
    """Exception for validation errors"""
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.field = field
        self.code = "VALIDATION_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(Exception):
    """Exception for authentication errors"""
    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = "AUTH_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class AuthorizationError(Exception):
    """Exception for authorization errors"""
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = "AUTHZ_ERROR"
        self.details = details or {}
        super().__init__(self.message)


class ServiceUnavailableError(Exception):
    """Exception for service unavailability"""
    def __init__(self, service: str, message: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.service = service
        self.message = message or f"Service {service} is currently unavailable"
        self.code = "SERVICE_UNAVAILABLE"
        self.details = details or {}
        super().__init__(self.message)


class RateLimitError(Exception):
    """Exception for rate limiting"""
    def __init__(self, message: str = "Rate limit exceeded", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = "RATE_LIMIT"
        self.details = details or {}
        super().__init__(self.message)


class NetworkError(Exception):
    """Exception for network-related errors"""
    def __init__(self, message: str, network: str = "mainnet-beta", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.network = network
        self.code = "NETWORK_ERROR"
        self.details = details or {}
        super().__init__(self.message)