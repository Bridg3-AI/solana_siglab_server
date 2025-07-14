"""
Response utilities for consistent API responses
"""
from firebase_functions import https_fn
import json
from typing import Dict, Any, Optional


class ResponseBuilder:
    @staticmethod
    def success(data: Any, status: int = 200) -> https_fn.Response:
        """Build successful response"""
        return https_fn.Response(
            json.dumps(data),
            status=status,
            headers={"Content-Type": "application/json"}
        )
    
    @staticmethod
    def error(message: str, status: int = 400, details: Optional[Dict[str, Any]] = None) -> https_fn.Response:
        """Build error response"""
        response_data = {"error": message}
        if details:
            response_data.update(details)
        
        return https_fn.Response(
            json.dumps(response_data),
            status=status,
            headers={"Content-Type": "application/json"}
        )
    
    @staticmethod
    def not_found(message: str = "Resource not found") -> https_fn.Response:
        """Build 404 response"""
        return ResponseBuilder.error(message, 404)
    
    @staticmethod
    def method_not_allowed(method: str) -> https_fn.Response:
        """Build 405 response"""
        return ResponseBuilder.error(f"Method {method} not allowed", 405)
    
    @staticmethod
    def internal_error(message: str = "Internal server error") -> https_fn.Response:
        """Build 500 response"""
        return ResponseBuilder.error(message, 500)
    
    @staticmethod
    def validation_error(message: str, errors: Optional[Dict[str, Any]] = None) -> https_fn.Response:
        """Build validation error response"""
        details = {"validation_errors": errors} if errors else None
        return ResponseBuilder.error(message, 422, details)