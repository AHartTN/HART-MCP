import os
from abc import ABC, abstractmethod
import asyncio
from typing import List

class Tool(ABC):
    """Abstract base class for all tools."""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    @abstractmethod
    def execute(self, *args, **kwargs):
        """Executes the tool's functionality."""
        pass

class ReadFileTool(Tool):
    """A tool for reading the content of a file."""
    def __init__(self):
        super().__init__(
            name="read_file",
            description="Reads the content of a specified file. Requires 'file_path' as an argument."
        )

    def execute(self, file_path: str):
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            return {"status": "success", "content": content}
        except FileNotFoundError:
            return {"status": "error", "message": f"File not found: {file_path}"}
        except Exception as e:
            return {"status": "error", "message": f"Error reading file {file_path}: {e}"}

class WriteFileTool(Tool):
    """A tool for writing content to a file."""
    def __init__(self):
        super().__init__(
            name="write_file",
            description="Writes content to a specified file. Requires 'file_path' and 'content' as arguments."
        )

    def execute(self, file_path: str, content: str):
        try:
            with open(file_path, 'w') as f:
                f.write(content)
            return {"status": "success", "message": f"Content successfully written to {file_path}"}
        except Exception as e:
            return {"status": "error", "message": f"Error writing to file {file_path}: {e}"}

class ListFilesTool(Tool):
    """A tool for listing files and directories within a specified path."""
    def __init__(self):
        super().__init__(
            name="list_files",
            description="Lists files and directories within a specified path. Requires 'path' as an argument."
        )

    def execute(self, path: str = "."):
        try:
            entries = os.listdir(path)
            files = [e for e in entries if os.path.isfile(os.path.join(path, e))]
            directories = [e for e in entries if os.path.isdir(os.path.join(path, e))]
            return {"status": "success", "files": files, "directories": directories}
        except FileNotFoundError:
            return {"status": "error", "message": f"Path not found: {path}"}
        except Exception as e:
            return {"status": "error", "message": f"Error listing files in {path}: {e}"}

class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register_tool(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool(self, tool_name: str) -> Tool:
        return self._tools.get(tool_name)

    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    async def use_tool(self, tool_name: str, **kwargs):
        tool = self.get_tool(tool_name)
        if tool:
            # Assuming execute can be async or sync
            if asyncio.iscoroutinefunction(tool.execute):
                return await tool.execute(**kwargs)
            else:
                return tool.execute(**kwargs)
        else:
            raise ValueError(f"Tool '{tool_name}' not found in registry.")
