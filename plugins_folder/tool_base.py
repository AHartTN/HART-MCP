from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
import asyncio
import logging

logger = logging.getLogger(__name__)


class Tool(ABC):
    """Abstract base class for all tools in the system."""
    
    def __init__(self, name: str = "", description: str = "", is_async: bool = False):
        self.name = name
        self.description = description
        self.is_async = is_async
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """Execute the tool with the given arguments.
        
        Returns:
            Dict containing 'status' (success/error) and relevant data
        """
        pass

    async def async_execute(self, *args, **kwargs) -> Dict[str, Any]:
        """Async wrapper for tool execution."""
        if self.is_async:
            return await self.execute(*args, **kwargs)
        else:
            return await asyncio.to_thread(self.execute, *args, **kwargs)

    def validate_input(self, **kwargs) -> Optional[str]:
        """Validate input parameters. Return error message if invalid, None if valid."""
        return None

    def _create_success_response(self, data: Any = None, **extra) -> Dict[str, Any]:
        """Helper to create standardized success response."""
        response = {"status": "success"}
        if data is not None:
            response["data"] = data
        response.update(extra)
        return response

    def _create_error_response(self, message: str, error_code: str = "GENERIC_ERROR") -> Dict[str, Any]:
        """Helper to create standardized error response."""
        self._logger.error(f"Tool {self.name} error: {message}")
        return {"status": "error", "message": message, "error_code": error_code}


class AsyncTool(Tool):
    """Base class for asynchronous tools."""
    
    def __init__(self, name: str = "", description: str = ""):
        super().__init__(name, description, is_async=True)

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """Async execution method."""
        pass
