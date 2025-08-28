from .tool_base import Tool, AsyncTool
from typing import List, Dict, Any, Optional
import asyncio
import os
import json
from utils.error_handlers import ErrorCode, safe_execute, ToolErrorHandler
import logging

logger = logging.getLogger(__name__)

class CheckForClarificationsTool(Tool):
    """A tool for checking if a query needs clarification."""

    def __init__(self):
        super().__init__(
            name="check_for_clarifications",
            description="Checks if a query needs clarification.",
        )

    def validate_input(self, **kwargs) -> Optional[str]:
        query = kwargs.get("query")
        if not query or not isinstance(query, str):
            return "Query parameter is required and must be a string"
        return None

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        query = kwargs.get("query") or (args[0] if args else None)
        
        # Enhanced clarification logic
        clarification_indicators = [
            len(query.split()) < 3,  # Very short queries
            "?" in query and not any(q in query.lower() for q in ["what", "how", "when", "where", "why", "who"]),  # Question without interrogative
            any(word in query.lower() for word in ["unclear", "vague", "not sure", "maybe", "perhaps"]),  # Uncertainty indicators
            query.count("?") > 2,  # Multiple questions
        ]
        
        needs_clarification = any(clarification_indicators)
        confidence_score = sum(clarification_indicators) / len(clarification_indicators)
        
        return self._create_success_response({
            "needs_clarification": needs_clarification,
            "confidence_score": confidence_score,
            "query_length": len(query.split()),
            "indicators_triggered": sum(clarification_indicators)
        })


class SQLQueryTool(AsyncTool):
    """
    Tool for executing read-only SQL queries against the SQL Server SSoT.
    """

    def __init__(self):
        super().__init__(
            name="sql_query",
            description="Executes read-only SQL queries against the SQL Server SSoT.",
        )

    def validate_input(self, **kwargs) -> Optional[str]:
        sql_query = kwargs.get("sql_query")
        if not sql_query or not isinstance(sql_query, str):
            return "sql_query parameter is required and must be a string"
        
        query_lower = sql_query.strip().lower()
        if not query_lower.startswith("select"):
            return "Only SELECT queries are allowed for security reasons"
        
        # Additional security checks
        dangerous_keywords = ["drop", "delete", "insert", "update", "alter", "create", "truncate"]
        if any(keyword in query_lower for keyword in dangerous_keywords):
            return f"Query contains dangerous keywords. Only SELECT operations allowed"
            
        return None

    @safe_execute(ErrorCode.DATABASE_QUERY)
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        sql_query = kwargs.get("sql_query") or (args[0] if args else None)
        
        try:
            from db_connectors import get_sql_server_connection
            from query_utils import execute_sql_query, sql_server_connection_context
            
            connection_manager = await get_sql_server_connection()
            async with connection_manager as conn:
                async with sql_server_connection_context(conn) as (conn, cursor):
                    await asyncio.to_thread(execute_sql_query, cursor, sql_query)
                    rows = await asyncio.to_thread(cursor.fetchall)
                    columns = (
                        [desc[0] for desc in cursor.description]
                        if cursor.description
                        else []
                    )
                    results = [dict(zip(columns, row, strict=False)) for row in rows]
                    
                    return self._create_success_response({
                        "query": sql_query,
                        "results": results,
                        "row_count": len(results),
                        "columns": columns
                    })
        except Exception as e:
            from utils.error_handlers import DatabaseErrorHandler
            error = DatabaseErrorHandler.handle_query_error(e, sql_query, "SQL Server")
            return error.to_dict()


class WriteFileTool(Tool):
    """A tool for writing content to a file."""

    def __init__(self):
        super().__init__(
            name="write_file",
            description="Writes content to a specified file. Requires 'file_path' and 'content' as arguments.",
        )

    def validate_input(self, **kwargs) -> Optional[str]:
        file_path = kwargs.get("file_path")
        content = kwargs.get("content")
        
        if not file_path or not isinstance(file_path, str):
            return "file_path parameter is required and must be a string"
        if content is None:
            return "content parameter is required"
        if not isinstance(content, str):
            return "content parameter must be a string"
            
        # Basic security check - prevent writing to system directories
        dangerous_paths = ["/etc/", "/sys/", "/proc/", "C:\\Windows", "C:\\System32"]
        if any(dangerous in file_path for dangerous in dangerous_paths):
            return "Cannot write to system directories for security reasons"
            
        return None

    @safe_execute(ErrorCode.FILE_OPERATION)
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        file_path = kwargs.get("file_path") or (args[0] if args else None)
        content = kwargs.get("content") or (args[1] if len(args) > 1 else None)
        
        try:
            # Ensure directory exists
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            file_size = os.path.getsize(file_path)
            return self._create_success_response({
                "file_path": file_path,
                "bytes_written": len(content.encode('utf-8')),
                "file_size": file_size,
                "encoding": "utf-8"
            })
        except Exception as e:
            error = ToolErrorHandler.handle_tool_error(e, self.name, kwargs)
            return error.to_dict()


class ListFilesTool(Tool):
    """A tool for listing files and directories within a specified path."""

    def __init__(self):
        super().__init__(
            name="list_files",
            description="Lists files and directories within a specified path. Requires 'path' as an argument.",
        )

    def validate_input(self, **kwargs) -> Optional[str]:
        path = kwargs.get("path", ".")
        if not isinstance(path, str):
            return "path parameter must be a string"
        return None

    @safe_execute(ErrorCode.FILE_OPERATION)
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        path = kwargs.get("path") or (args[0] if args else ".")
        
        try:
            if not os.path.exists(path):
                return self._create_error_response(f"Path not found: {path}", ErrorCode.FILE_OPERATION.value)
            
            if not os.path.isdir(path):
                return self._create_error_response(f"Path is not a directory: {path}", ErrorCode.FILE_OPERATION.value)
            
            entries = os.listdir(path)
            files = []
            directories = []
            
            for entry in entries:
                entry_path = os.path.join(path, entry)
                if os.path.isfile(entry_path):
                    file_size = os.path.getsize(entry_path)
                    files.append({"name": entry, "size": file_size})
                elif os.path.isdir(entry_path):
                    directories.append({"name": entry})
            
            return self._create_success_response({
                "path": path,
                "files": files,
                "directories": directories,
                "total_files": len(files),
                "total_directories": len(directories)
            })
        except PermissionError:
            return self._create_error_response(f"Permission denied accessing: {path}", ErrorCode.FILE_OPERATION.value)
        except Exception as e:
            error = ToolErrorHandler.handle_tool_error(e, self.name, kwargs)
            return error.to_dict()


class ReadFileTool(Tool):
    """A tool for reading content from a file."""

    def __init__(self):
        super().__init__(
            name="read_file",
            description="Reads content from a specified file. Requires 'file_path' as an argument.",
        )

    def validate_input(self, **kwargs) -> Optional[str]:
        file_path = kwargs.get("file_path")
        if not file_path or not isinstance(file_path, str):
            return "file_path parameter is required and must be a string"
        return None

    @safe_execute(ErrorCode.FILE_OPERATION)
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        file_path = kwargs.get("file_path") or (args[0] if args else None)

        try:
            if not os.path.exists(file_path):
                return self._create_error_response(f"File not found: {file_path}", ErrorCode.FILE_OPERATION.value)
            
            if not os.path.isfile(file_path):
                return self._create_error_response(f"Path is not a file: {file_path}", ErrorCode.FILE_OPERATION.value)
            
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB limit
                return self._create_error_response(f"File too large: {file_size} bytes. Maximum allowed: 10MB", ErrorCode.FILE_OPERATION.value)
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            return self._create_success_response({
                "file_path": file_path,
                "content": content,
                "file_size": file_size,
                "encoding": "utf-8",
                "line_count": len(content.splitlines())
            })
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            try:
                with open(file_path, "r", encoding="latin-1") as f:
                    content = f.read()
                return self._create_success_response({
                    "file_path": file_path,
                    "content": content,
                    "file_size": os.path.getsize(file_path),
                    "encoding": "latin-1",
                    "line_count": len(content.splitlines())
                })
            except Exception as e:
                error = ToolErrorHandler.handle_tool_error(e, self.name, kwargs)
                return error.to_dict()
        except Exception as e:
            error = ToolErrorHandler.handle_tool_error(e, self.name, kwargs)
            return error.to_dict()


class DelegateToSpecialistTool(AsyncTool):
    """A tool for delegating tasks to specialist agents."""

    def __init__(self, specialist_agent=None, agent_factory=None):
        super().__init__(
            name="delegate_to_specialist",
            description="Delegates tasks to specialist agents.",
        )
        self.specialist_agent = specialist_agent
        self.agent_factory = agent_factory

    def validate_input(self, **kwargs) -> Optional[str]:
        task = kwargs.get("task")
        if not task or not isinstance(task, str):
            return "task parameter is required and must be a string"
        if len(task.strip()) < 5:
            return "task must be at least 5 characters long"
        return None

    @safe_execute(ErrorCode.TOOL_EXECUTION)
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        task = kwargs.get("task") or (args[0] if args else None)
        specialist_type = kwargs.get("specialist_type", "general")
        priority = kwargs.get("priority", "normal")
        
        try:
            if self.agent_factory:
                # Use agent factory to create appropriate specialist
                specialist = await self.agent_factory.create_specialist(specialist_type)
                if specialist:
                    # Execute task with specialist
                    result = await specialist.execute_task(task)
                    return self._create_success_response({
                        "task": task,
                        "specialist_type": specialist_type,
                        "specialist_id": getattr(specialist, 'agent_id', 'unknown'),
                        "result": result,
                        "delegation_successful": True
                    })
                else:
                    return self._create_error_response(f"Failed to create specialist of type: {specialist_type}", ErrorCode.TOOL_EXECUTION.value)
            
            elif self.specialist_agent:
                # Use provided specialist agent
                result = await self.specialist_agent.execute_task(task)
                return self._create_success_response({
                    "task": task,
                    "specialist_type": specialist_type,
                    "result": result,
                    "delegation_successful": True
                })
            
            else:
                # Fallback - queue task for later processing
                return self._create_success_response({
                    "task": task,
                    "specialist_type": specialist_type,
                    "status": "queued",
                    "message": f"Task '{task}' queued for {specialist_type} specialist",
                    "delegation_successful": False,
                    "note": "No specialist agent available - task queued"
                })
                
        except Exception as e:
            error = ToolErrorHandler.handle_tool_error(e, self.name, kwargs)
            return error.to_dict()


class FinishTool(Tool):
    """A tool for marking tasks as finished."""

    def __init__(self):
        super().__init__(
            name="finish", description="Marks a task or process as finished."
        )

    def validate_input(self, **kwargs) -> Optional[str]:
        # Finish tool is very permissive - any input is acceptable
        return None

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        result = kwargs.get("result") or kwargs.get("response") or (args[0] if args else "Task completed successfully")
        summary = kwargs.get("summary", "")
        
        response_data = {
            "result": result,
            "task_completed": True,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        
        if summary:
            response_data["summary"] = summary
            
        return {
            "status": "finished",
            "data": response_data
        }


class RAGTool(AsyncTool):
    """A tool for performing RAG (Retrieval-Augmented Generation) operations."""

    def __init__(self, rag_orchestrator=None):
        super().__init__(
            name="rag",
            description="Performs RAG operations to retrieve and generate responses.",
        )
        self.rag_orchestrator = rag_orchestrator

    def validate_input(self, **kwargs) -> Optional[str]:
        query = kwargs.get("query")
        if not query or not isinstance(query, str):
            return "Query parameter is required and must be a string"
        if len(query.strip()) < 2:
            return "Query must be at least 2 characters long"
        return None

    @safe_execute(ErrorCode.TOOL_EXECUTION)
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        query = kwargs.get("query") or (args[0] if args else None)
        context = kwargs.get("context", {})
        
        if not self.rag_orchestrator:
            # Fallback behavior when no orchestrator available
            return self._create_success_response({
                "message": f"RAG operation queued for query: {query}",
                "query": query,
                "status": "no_orchestrator_available",
                "fallback_response": "Please configure RAG orchestrator for full functionality"
            })
        
        try:
            # Use the actual RAG orchestrator
            result = await self.rag_orchestrator.generate_response(query, context)
            return self._create_success_response(result)
        except Exception as e:
            error = ToolErrorHandler.handle_tool_error(e, self.name, kwargs)
            return error.to_dict()


class ReadFromSharedStateTool(Tool):
    """A tool for reading from shared state."""

    def __init__(self, project_state):
        super().__init__(
            name="read_shared_state",
            description="Reads data from shared state storage.",
        )
        self.project_state = project_state

    def validate_input(self, **kwargs) -> Optional[str]:
        key = kwargs.get("key")
        if not key or not isinstance(key, str):
            return "Key parameter is required and must be a string"
        return None

    @safe_execute(ErrorCode.TOOL_EXECUTION)
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        key = kwargs.get("key") or (args[0] if args else None)
        
        try:
            if self.project_state and hasattr(self.project_state, 'get_state'):
                value = self.project_state.get_state(key)
                if value is not None:
                    return self._create_success_response({"key": key, "value": value})
                else:
                    return self._create_error_response(f"Key '{key}' not found in shared state", ErrorCode.VALIDATION_ERROR.value)
            else:
                # Fallback to in-memory storage if project_state not available
                if not hasattr(self, '_memory_state'):
                    self._memory_state = {}
                
                if key in self._memory_state:
                    return self._create_success_response({"key": key, "value": self._memory_state[key]})
                else:
                    return self._create_error_response(f"Key '{key}' not found in memory state", ErrorCode.VALIDATION_ERROR.value)
        except Exception as e:
            error = ToolErrorHandler.handle_tool_error(e, self.name, kwargs)
            return error.to_dict()


class SendClarificationTool(Tool):
    """A tool for sending clarifications."""

    def __init__(self, callback_handler=None):
        super().__init__(
            name="send_clarification",
            description="Sends clarification requests or responses.",
        )
        self.callback_handler = callback_handler

    def validate_input(self, **kwargs) -> Optional[str]:
        message = kwargs.get("message")
        if not message or not isinstance(message, str):
            return "message parameter is required and must be a string"
        if len(message.strip()) < 3:
            return "message must be at least 3 characters long"
        return None

    @safe_execute(ErrorCode.TOOL_EXECUTION)
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        message = kwargs.get("message") or (args[0] if args else None)
        recipient = kwargs.get("recipient", "user")
        urgency = kwargs.get("urgency", "normal")
        
        try:
            clarification_data = {
                "message": message,
                "recipient": recipient,
                "urgency": urgency,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "type": "clarification_request"
            }
            
            if self.callback_handler:
                # Send through callback handler if available
                success = self.callback_handler.send_clarification(clarification_data)
                if success:
                    return self._create_success_response({
                        "clarification_sent": True,
                        "delivery_method": "callback",
                        **clarification_data
                    })
                else:
                    return self._create_error_response("Failed to send clarification through callback handler", ErrorCode.TOOL_EXECUTION.value)
            else:
                # Fallback - log and queue
                logger.info(f"Clarification queued: {message}")
                return self._create_success_response({
                    "clarification_sent": False,
                    "delivery_method": "queued",
                    "note": "No callback handler available - clarification queued",
                    **clarification_data
                })
                
        except Exception as e:
            error = ToolErrorHandler.handle_tool_error(e, self.name, kwargs)
            return error.to_dict()


class TreeOfThoughtTool(AsyncTool):
    """A tool for Tree of Thought reasoning operations."""

    def __init__(self, llm_client):
        super().__init__(
            name="tree_of_thought",
            description="Performs Tree of Thought reasoning operations.",
        )
        self.llm_client = llm_client

    def validate_input(self, **kwargs) -> Optional[str]:
        prompt = kwargs.get("prompt")
        if not prompt or not isinstance(prompt, str):
            return "Prompt parameter is required and must be a string"
        if len(prompt.strip()) < 5:
            return "Prompt must be at least 5 characters long for meaningful ToT analysis"
        return None

    @safe_execute(ErrorCode.TOOL_EXECUTION)
    async def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        prompt = kwargs.get("prompt") or (args[0] if args else None)
        depth = kwargs.get("depth", 3)  # Number of thought levels
        branches = kwargs.get("branches", 3)  # Number of thoughts per level
        
        if not self.llm_client:
            return self._create_error_response("LLM client not available for Tree of Thought processing", ErrorCode.LLM_CONNECTION.value)
        
        try:
            # Generate initial thoughts
            generation_prompt = f"Given this problem: '{prompt}', generate {branches} distinct approaches or thoughts as a JSON array of strings."
            response = await self.llm_client.invoke(generation_prompt)
            
            try:
                initial_thoughts = json.loads(response)
                if not isinstance(initial_thoughts, list):
                    initial_thoughts = [str(initial_thoughts)]
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                initial_thoughts = [f"Approach 1: {response[:100]}...", 
                                  f"Approach 2: Alternative method", 
                                  f"Approach 3: Creative solution"]
            
            # Evaluate thoughts
            evaluated_thoughts = []
            for i, thought in enumerate(initial_thoughts[:branches]):
                eval_prompt = f"Rate this thought/approach on a scale of 0-1 for solving '{prompt}': '{thought}'. Respond with just a number between 0 and 1."
                try:
                    score_response = await self.llm_client.invoke(eval_prompt)
                    score = float(score_response.strip())
                    if not (0 <= score <= 1):
                        score = 0.5  # Default score if invalid
                except (ValueError, TypeError):
                    score = 0.5  # Default score if parsing fails
                
                evaluated_thoughts.append({
                    "text": thought,
                    "score": score,
                    "id": i
                })
            
            # Sort by score and select best
            evaluated_thoughts.sort(key=lambda x: x["score"], reverse=True)
            best_thought = evaluated_thoughts[0] if evaluated_thoughts else {"text": "No valid thoughts generated", "score": 0, "id": -1}
            
            return self._create_success_response({
                "prompt": prompt,
                "thoughts": evaluated_thoughts,
                "best_thought": best_thought,
                "depth_processed": 1,  # For now, only doing one level
                "branches_generated": len(evaluated_thoughts)
            })
            
        except Exception as e:
            error = ToolErrorHandler.handle_tool_error(e, self.name, kwargs)
            return error.to_dict()


class WriteToSharedStateTool(Tool):
    """A tool for writing to shared state."""

    def __init__(self, project_state):
        super().__init__(
            name="write_shared_state",
            description="Writes data to shared state storage.",
        )
        self.project_state = project_state

    def validate_input(self, **kwargs) -> Optional[str]:
        key = kwargs.get("key")
        value = kwargs.get("value")
        if not key or not isinstance(key, str):
            return "Key parameter is required and must be a string"
        if value is None:
            return "Value parameter is required"
        return None

    @safe_execute(ErrorCode.TOOL_EXECUTION)
    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
            
        key = kwargs.get("key") or (args[0] if args else None)
        value = kwargs.get("value") or (args[1] if len(args) > 1 else None)
        
        try:
            if self.project_state and hasattr(self.project_state, 'set_state'):
                success = self.project_state.set_state(key, value)
                if success:
                    return self._create_success_response({"key": key, "value": value, "stored": True})
                else:
                    return self._create_error_response("Failed to store value in project state", ErrorCode.TOOL_EXECUTION.value)
            else:
                # Fallback to in-memory storage if project_state not available
                if not hasattr(self, '_memory_state'):
                    self._memory_state = {}
                
                self._memory_state[key] = value
                return self._create_success_response({"key": key, "value": value, "stored": True, "storage_type": "memory"})
        except Exception as e:
            error = ToolErrorHandler.handle_tool_error(e, self.name, kwargs)
            return error.to_dict()


class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register_tool(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool(self, tool_name: str) -> Tool:
        tool = self._tools.get(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")
        return tool

    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    async def use_tool(self, tool_name: str, **kwargs):
        tool = self.get_tool(tool_name)
        if asyncio.iscoroutinefunction(tool.execute):
            return await tool.execute(**kwargs)
        else:
            return tool.execute(**kwargs)