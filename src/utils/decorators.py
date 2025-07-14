"""
Utility decorators for Firebase Functions
Following Firebase 2025 best practices
"""
import functools
import time
import sys
import os
from typing import Callable, Any
from firebase_functions import https_fn

# Add Firebase module to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from firebase.core.logging import logger, log_performance, log_error
from firebase.core.exceptions import ValidationError, AuthenticationError, ServiceUnavailableError
from firebase import AuthMiddleware
from .response import ResponseBuilder


def performance_monitor(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            op_name = operation_name or func.__name__
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                log_performance(op_name, duration_ms, success=True)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                log_performance(op_name, duration_ms, success=False, error=str(e))
                raise
        
        return wrapper
    return decorator


def error_handler(func: Callable) -> Callable:
    """Decorator to handle errors and return proper HTTP responses"""
    @functools.wraps(func)
    def wrapper(req: https_fn.Request) -> https_fn.Response:
        try:
            return func(req)
        
        except ValidationError as e:
            log_error(e, context=func.__name__, request_path=req.path)
            return ResponseBuilder.validation_error(e.message, {"field": e.field})
        
        except AuthenticationError as e:
            log_error(e, context=func.__name__, request_path=req.path)
            return ResponseBuilder.error(e.message, 401)
        
        except ServiceUnavailableError as e:
            log_error(e, context=func.__name__, request_path=req.path, service=e.service)
            return ResponseBuilder.error(e.message, 503)
        
        except Exception as e:
            log_error(e, context=func.__name__, request_path=req.path)
            return ResponseBuilder.internal_error("An unexpected error occurred")
    
    return wrapper


def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication"""
    @functools.wraps(func)
    def wrapper(req: https_fn.Request) -> https_fn.Response:
        auth_error = AuthMiddleware.require_auth(req)
        if auth_error:
            return auth_error
        
        # Add user info to request for downstream use
        user_info = AuthMiddleware.get_user_from_request(req)
        req.user = user_info  # Add user to request object
        
        return func(req)
    
    return wrapper


def validate_method(*allowed_methods: str):
    """Decorator to validate HTTP methods"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(req: https_fn.Request) -> https_fn.Response:
            if req.method not in allowed_methods:
                return ResponseBuilder.method_not_allowed(req.method)
            return func(req)
        return wrapper
    return decorator


def validate_json(func: Callable) -> Callable:
    """Decorator to validate JSON request body"""
    @functools.wraps(func)
    def wrapper(req: https_fn.Request) -> https_fn.Response:
        if req.method in ['POST', 'PUT', 'PATCH']:
            try:
                req.json_data = req.get_json()
                if req.json_data is None:
                    raise ValidationError("Request body must contain valid JSON")
            except Exception as e:
                raise ValidationError("Invalid JSON in request body")
        
        return func(req)
    
    return wrapper


def rate_limit(requests_per_minute: int = 60):
    """Basic rate limiting decorator (for demonstration - use Firebase App Check in production)"""
    def decorator(func: Callable) -> Callable:
        # In production, implement proper rate limiting with Redis or Firestore
        # This is a simplified version for demonstration
        @functools.wraps(func)
        def wrapper(req: https_fn.Request) -> https_fn.Response:
            # Rate limiting logic would go here
            # For now, just log the request
            logger.info(f"Rate limit check for {func.__name__}", 
                       limit=requests_per_minute,
                       client_ip=req.headers.get('X-Forwarded-For', 'unknown'))
            return func(req)
        return wrapper
    return decorator


def log_request(func: Callable) -> Callable:
    """Decorator to log HTTP requests"""
    @functools.wraps(func)
    def wrapper(req: https_fn.Request) -> https_fn.Response:
        logger.info(f"HTTP Request: {func.__name__}",
                   method=req.method,
                   path=req.path,
                   user_agent=req.headers.get('User-Agent', ''),
                   content_type=req.headers.get('Content-Type', ''))
        
        response = func(req)
        
        logger.info(f"HTTP Response: {func.__name__}",
                   status_code=response.status_code,
                   response_size=len(response.data) if response.data else 0)
        
        return response
    
    return wrapper