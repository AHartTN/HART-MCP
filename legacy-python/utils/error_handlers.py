import logging
import traceback
from enum import Enum
from typing import Any, Dict, Optional, Type, Union
from fastapi.responses import JSONResponse
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for the system."""
    GENERIC_ERROR = "GENERIC_ERROR"
    DATABASE_CONNECTION = "DATABASE_CONNECTION" 
    DATABASE_QUERY = "DATABASE_QUERY"
    LLM_CONNECTION = "LLM_CONNECTION"
    LLM_RESPONSE = "LLM_RESPONSE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    AGENT_EXECUTION = "AGENT_EXECUTION"
    EMBEDDING_GENERATION = "EMBEDDING_GENERATION"
    FILE_OPERATION = "FILE_OPERATION"
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"


class StandardizedError:
    """Standardized error response structure."""
    
    def __init__(self, 
                 error_code: ErrorCode, 
                 message: str, 
                 details: Optional[Dict[str, Any]] = None,
                 original_exception: Optional[Exception] = None):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "status": "error",
            "error_code": self.error_code.value,
            "message": self.message
        }
        if self.details:
            result["details"] = self.details
        return result
        
    def to_json_response(self, status_code: int = 500) -> JSONResponse:
        """Convert to FastAPI JSONResponse."""
        return JSONResponse(content=self.to_dict(), status_code=status_code)


def find_error_message(exc: Exception, target: str) -> bool:
    """Recursively searches for a target string in an exception chain."""
    while exc:
        msg = str(exc)
        if target in msg:
            return True
        exc = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    return False


def categorize_exception(exc: Exception) -> ErrorCode:
    """Categorize exception into appropriate error code."""
    exc_str = str(exc).lower()
    exc_type = type(exc).__name__.lower()
    
    # Database errors
    if any(term in exc_str for term in ["connection", "database", "sql", "milvus", "neo4j"]):
        if "connection" in exc_str:
            return ErrorCode.DATABASE_CONNECTION
        return ErrorCode.DATABASE_QUERY
    
    # LLM errors
    if any(term in exc_str for term in ["llm", "openai", "anthropic", "model"]):
        if "connection" in exc_str or "timeout" in exc_str:
            return ErrorCode.LLM_CONNECTION
        return ErrorCode.LLM_RESPONSE
    
    # File operations
    if any(term in exc_type for term in ["filenotfounderror", "permissionerror", "ioerror"]):
        return ErrorCode.FILE_OPERATION
    
    # Validation
    if "validation" in exc_str or exc_type in ["valueerror", "typeerror"]:
        return ErrorCode.VALIDATION_ERROR
        
    return ErrorCode.GENERIC_ERROR


async def handle_api_exception(e: Exception, 
                             default_message: str = "Internal server error",
                             context: Optional[Dict[str, Any]] = None) -> JSONResponse:
    """Centralized exception handler for API endpoints."""
    error_code = categorize_exception(e)
    
    # Enhanced logging with context
    log_data = {
        "exception_type": type(e).__name__,
        "exception_message": str(e),
        "error_code": error_code.value,
        "context": context or {}
    }
    logger.error(f"API Exception: {log_data}", exc_info=True)
    
    # Create standardized error
    standardized_error = StandardizedError(
        error_code=error_code,
        message=default_message,
        details={"exception_type": type(e).__name__},
        original_exception=e
    )
    
    return standardized_error.to_json_response()


def safe_execute(error_code: ErrorCode = ErrorCode.GENERIC_ERROR, 
                default_return: Any = None):
    """Decorator for safe execution with standardized error handling."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return await asyncio.to_thread(func, *args, **kwargs)
            except Exception as e:
                logger.error(f"Safe execution failed in {func.__name__}: {e}", exc_info=True)
                if default_return is not None:
                    return default_return
                return StandardizedError(
                    error_code=error_code,
                    message=f"Error in {func.__name__}: {str(e)}",
                    original_exception=e
                ).to_dict()
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Safe execution failed in {func.__name__}: {e}", exc_info=True)
                if default_return is not None:
                    return default_return
                return StandardizedError(
                    error_code=error_code,
                    message=f"Error in {func.__name__}: {str(e)}",
                    original_exception=e
                ).to_dict()
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class DatabaseErrorHandler:
    """Specialized error handler for database operations."""
    
    @staticmethod
    def handle_connection_error(exc: Exception, db_type: str) -> StandardizedError:
        """Handle database connection errors."""
        return StandardizedError(
            error_code=ErrorCode.DATABASE_CONNECTION,
            message=f"Failed to connect to {db_type} database",
            details={"database_type": db_type, "exception": str(exc)},
            original_exception=exc
        )
    
    @staticmethod 
    def handle_query_error(exc: Exception, query: str, db_type: str) -> StandardizedError:
        """Handle database query errors."""
        return StandardizedError(
            error_code=ErrorCode.DATABASE_QUERY,
            message=f"Query execution failed on {db_type}",
            details={"database_type": db_type, "query": query[:100], "exception": str(exc)},
            original_exception=exc
        )


class ToolErrorHandler:
    """Specialized error handler for tool operations."""
    
    @staticmethod
    def handle_tool_error(exc: Exception, tool_name: str, parameters: Dict[str, Any]) -> StandardizedError:
        """Handle tool execution errors."""
        return StandardizedError(
            error_code=ErrorCode.TOOL_EXECUTION,
            message=f"Tool '{tool_name}' execution failed",
            details={"tool_name": tool_name, "parameters": parameters, "exception": str(exc)},
            original_exception=exc
        )