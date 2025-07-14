"""
Centralized logging configuration
Following Firebase 2025 monitoring best practices
"""
import logging
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import traceback


class FirebaseLogger:
    """Firebase-optimized logger for Cloud Functions"""
    
    def __init__(self, name: str = __name__):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplication
        for handler in self.logger.handlers:
            self.logger.removeHandler(handler)
        
        # Create console handler for Firebase Functions
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # Firebase-friendly JSON formatter
        formatter = FirebaseJSONFormatter()
        handler.setFormatter(formatter)
        
        self.logger.addHandler(handler)
        self.logger.propagate = False
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        extra = {"extra_data": kwargs} if kwargs else {}
        self.logger.info(message, extra=extra)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with exception details"""
        extra_data = kwargs.copy()
        if error:
            extra_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc()
            })
        extra = {"extra_data": extra_data} if extra_data else {}
        self.logger.error(message, extra=extra)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        extra = {"extra_data": kwargs} if kwargs else {}
        self.logger.warning(message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        extra = {"extra_data": kwargs} if kwargs else {}
        self.logger.debug(message, extra=extra)


class FirebaseJSONFormatter(logging.Formatter):
    """JSON formatter optimized for Firebase Cloud Logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "function_name": getattr(record, 'funcName', ''),
            "line_number": getattr(record, 'lineno', '')
        }
        
        # Add extra data if present
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


# Global logger instance
logger = FirebaseLogger("solana_siglab")

# Convenience functions
def log_function_call(func_name: str, args: Dict[str, Any] = None, user_id: str = None):
    """Log function call with parameters"""
    logger.info(f"Function called: {func_name}", 
                function=func_name, 
                args=args or {}, 
                user_id=user_id)

def log_agent_interaction(session_id: str, user_input: str, agent_response: str, 
                         tools_used: list = None, iterations: int = 0):
    """Log agent interaction details"""
    logger.info("Agent interaction completed",
                session_id=session_id,
                user_input=user_input[:100] + "..." if len(user_input) > 100 else user_input,
                response_length=len(agent_response),
                tools_used=tools_used or [],
                iterations=iterations)

def log_solana_operation(operation: str, address: str = None, network: str = None, 
                        success: bool = True, error: str = None):
    """Log Solana blockchain operation"""
    logger.info(f"Solana operation: {operation}",
                operation=operation,
                address=address,
                network=network,
                success=success,
                error=error)

def log_performance(operation: str, duration_ms: float, **kwargs):
    """Log performance metrics"""
    logger.info(f"Performance: {operation}",
                operation=operation,
                duration_ms=duration_ms,
                **kwargs)

def log_error(error: Exception, context: str = "", **kwargs):
    """Log error with full context"""
    logger.error(f"Error in {context}" if context else "Error occurred", 
                error=error, **kwargs)