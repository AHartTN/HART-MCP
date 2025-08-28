from plugins_folder.tool_base import Tool
from typing import List
import asyncio
import os


class CheckForClarificationsTool(Tool):
    """A tool for checking if a query needs clarification."""

    def __init__(self):
        super().__init__(
            name="check_for_clarifications",
            description="Checks if a query needs clarification.",
        )

    def execute(self, *args, **kwargs):
        query = kwargs.get("query") or (args[0] if args else None)
        if not query:
            return {"status": "error", "message": "No query provided."}
        # Placeholder logic for clarification check
        needs_clarification = "?" in query or len(query.split()) < 3
        return {"status": "success", "needs_clarification": needs_clarification}


class SQLQueryTool(Tool):
    """
    Tool for executing read-only SQL queries against the SQL Server SSoT.
    """

    def __init__(self):
        super().__init__(
            name="sql_query",
            description="Executes read-only SQL queries against the SQL Server SSoT.",
        )

    async def execute(self, *args, **kwargs):
        sql_query = kwargs.get("sql_query") or (args[0] if args else None)
        if not sql_query or not sql_query.strip().lower().startswith("select"):
            raise ValueError("Only SELECT queries are allowed.")

        from db_connectors import get_sql_server_connection
        from query_utils import execute_sql_query, sql_server_connection_context
        import asyncio

        try:
            connection_manager = await get_sql_server_connection()
            async with connection_manager as conn:
                async with sql_server_connection_context(conn) as (conn, cursor):
                    await asyncio.to_thread(execute_sql_query, cursor, sql_query)
                    # Fetch all results
                    rows = await asyncio.to_thread(cursor.fetchall)
                    columns = (
                        [desc[0] for desc in cursor.description]
                        if cursor.description
                        else []
                    )
                    return [dict(zip(columns, row, strict=False)) for row in rows]
        except Exception as e:
            return {"status": "error", "message": str(e)}


class WriteFileTool(Tool):
    """A tool for writing content to a file."""

    def __init__(self):
        super().__init__(
            name="write_file",
            description="Writes content to a specified file. Requires 'file_path' and 'content' as arguments.",
        )

    def execute(self, *args, **kwargs):
        file_path = kwargs.get("file_path") or (args[0] if args else None)
        content = kwargs.get("content") or (args[1] if len(args) > 1 else None)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {
                "status": "success",
                "message": f"Content successfully written to {file_path}",
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error writing to file {file_path}: {e}",
            }


class ListFilesTool(Tool):
    """A tool for listing files and directories within a specified path."""

    def __init__(self):
        super().__init__(
            name="list_files",
            description="Lists files and directories within a specified path. Requires 'path' as an argument.",
        )

    def execute(self, *args, **kwargs):
        path = kwargs.get("path") or (args[0] if args else ".")
        try:
            entries = os.listdir(path)
            files = [e for e in entries if os.path.isfile(os.path.join(path, e))]
            directories = [e for e in entries if os.path.isdir(os.path.join(path, e))]
            return {"status": "success", "files": files, "directories": directories}
        except FileNotFoundError:
            return {"status": "error", "message": f"Path not found: {path}"}
        except Exception as e:
            return {"status": "error", "message": f"Error listing files in {path}: {e}"}


class ReadFileTool(Tool):
    """A tool for reading content from a file."""

    def __init__(self):
        super().__init__(
            name="read_file",
            description="Reads content from a specified file. Requires 'file_path' as an argument.",
        )

    def execute(self, *args, **kwargs):
        file_path = kwargs.get("file_path") or (args[0] if args else None)
        if not file_path:
            return {"status": "error", "message": "No file path provided."}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return {"status": "success", "content": content}
        except FileNotFoundError:
            return {"status": "error", "message": f"File not found: {file_path}"}
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error reading file {file_path}: {e}",
            }


class DelegateToSpecialistTool(Tool):
    """A tool for delegating tasks to specialist agents."""

    def __init__(self):
        super().__init__(
            name="delegate_to_specialist",
            description="Delegates tasks to specialist agents.",
        )

    def execute(self, *args, **kwargs):
        # Placeholder implementation
        task = kwargs.get("task") or (args[0] if args else None)
        specialist_type = kwargs.get("specialist_type") or (
            args[1] if len(args) > 1 else "general"
        )
        return {
            "status": "success",
            "message": f"Task '{task}' delegated to {specialist_type} specialist",
        }


class FinishTool(Tool):
    """A tool for marking tasks as finished."""

    def __init__(self):
        super().__init__(
            name="finish", description="Marks a task or process as finished."
        )

    def execute(self, *args, **kwargs):
        result = kwargs.get("result") or (args[0] if args else "Task completed")
        return {"status": "finished", "result": result}


class RAGTool(Tool):
    """A tool for performing RAG (Retrieval-Augmented Generation) operations."""

    def __init__(self):
        super().__init__(
            name="rag",
            description="Performs RAG operations to retrieve and generate responses.",
        )

    def execute(self, *args, **kwargs):
        # Placeholder implementation
        query = kwargs.get("query") or (args[0] if args else None)
        if not query:
            return {
                "status": "error",
                "message": "No query provided for RAG operation.",
            }
        return {
            "status": "success",
            "message": f"RAG operation completed for query: {query}",
            "result": "Generated response based on retrieved context",
        }


class ReadFromSharedStateTool(Tool):
    """A tool for reading from shared state."""

    def __init__(self):
        super().__init__(
            name="read_shared_state",
            description="Reads data from shared state storage.",
        )

    def execute(self, *args, **kwargs):
        key = kwargs.get("key") or (args[0] if args else None)
        if not key:
            return {
                "status": "error",
                "message": "No key provided for reading shared state.",
            }
        # Placeholder implementation
        return {"status": "success", "key": key, "value": "placeholder_value"}


class SendClarificationTool(Tool):
    """A tool for sending clarifications."""

    def __init__(self):
        super().__init__(
            name="send_clarification",
            description="Sends clarification requests or responses.",
        )

    def execute(self, *args, **kwargs):
        message = kwargs.get("message") or (args[0] if args else None)
        if not message:
            return {"status": "error", "message": "No clarification message provided."}
        return {"status": "success", "message": f"Clarification sent: {message}"}


class TreeOfThoughtTool(Tool):
    """A tool for Tree of Thought reasoning operations."""

    def __init__(self):
        super().__init__(
            name="tree_of_thought",
            description="Performs Tree of Thought reasoning operations.",
        )

    def execute(self, *args, **kwargs):
        prompt = kwargs.get("prompt") or (args[0] if args else None)
        if not prompt:
            return {
                "status": "error",
                "message": "No prompt provided for Tree of Thought.",
            }
        # Placeholder implementation
        return {
            "status": "success",
            "prompt": prompt,
            "thoughts": ["Thought 1", "Thought 2", "Thought 3"],
            "best_thought": "Thought 2",
        }


class WriteToSharedStateTool(Tool):
    """A tool for writing to shared state."""

    def __init__(self):
        super().__init__(
            name="write_shared_state",
            description="Writes data to shared state storage.",
        )

    def execute(self, *args, **kwargs):
        key = kwargs.get("key") or (args[0] if args else None)
        value = kwargs.get("value") or (args[1] if len(args) > 1 else None)
        if not key:
            return {
                "status": "error",
                "message": "No key provided for writing to shared state.",
            }
        if value is None:
            return {
                "status": "error",
                "message": "No value provided for writing to shared state.",
            }
        # Placeholder implementation
        return {
            "status": "success",
            "message": f"Written to shared state: {key} = {value}",
        }


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
