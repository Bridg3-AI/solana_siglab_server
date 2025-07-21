"""
Structlog-based logging system for LangGraph agents
CLAUDE.md P6 원칙: 관찰 가능성 - structlog 기반 노드별 logging
"""

import structlog
import logging
from typing import Any, Dict, Optional
import sys
from datetime import datetime


def configure_structlog():
    """Configure structlog for LangGraph agents"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(sort_keys=True)
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "langgraph_agent") -> structlog.BoundLogger:
    """Get configured structlog logger"""
    return structlog.get_logger(name)


def log_node_start(logger: structlog.BoundLogger, node_name: str, **kwargs):
    """Log node execution start"""
    logger.info(
        "node_execution_started",
        node=node_name,
        event="node_start",
        **kwargs
    )


def log_node_success(logger: structlog.BoundLogger, node_name: str, **kwargs):
    """Log node execution success"""
    logger.info(
        "node_execution_completed",
        node=node_name,
        event="node_success",
        **kwargs
    )


def log_node_error(logger: structlog.BoundLogger, node_name: str, error: str, **kwargs):
    """Log node execution error"""
    logger.error(
        "node_execution_failed",
        node=node_name,
        event="node_error",
        error=error,
        **kwargs
    )


def log_state_transition(logger: structlog.BoundLogger, node_name: str, 
                        before_keys: set, after_keys: set, **kwargs):
    """Log state transitions for debugging"""
    added_keys = after_keys - before_keys
    removed_keys = before_keys - after_keys
    
    logger.debug(
        "state_transition",
        node=node_name,
        event="state_change",
        added_keys=list(added_keys),
        removed_keys=list(removed_keys),
        **kwargs
    )


def log_tool_execution(logger: structlog.BoundLogger, tool_name: str, 
                      status: str, **kwargs):
    """Log tool execution"""
    logger.info(
        "tool_execution",
        tool=tool_name,
        event="tool_call",
        status=status,
        **kwargs
    )


def log_llm_call(logger: structlog.BoundLogger, model: str, 
                prompt_length: int, response_length: int, **kwargs):
    """Log LLM API calls"""
    logger.info(
        "llm_api_call",
        event="llm_call",
        model=model,
        prompt_length=prompt_length,
        response_length=response_length,
        **kwargs
    )


# Initialize structlog configuration
configure_structlog()

# Export default logger
default_logger = get_logger("langgraph_pricing_agent")