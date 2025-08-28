"""Essential production tools that every AI agent system needs."""
import os
import json
import asyncio
import aiohttp
import aiofiles
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urlparse, urljoin
import mimetypes
import hashlib

from .tool_base import Tool, AsyncTool
from utils.error_handlers import ErrorCode, safe_execute


class FileIOTool(AsyncTool):
    """Tool for file system operations - read, write, list, etc."""
    
    def __init__(self):
        super().__init__(
            name="file_io",
            description="Performs file system operations: read, write, list files, create directories."
        )
        # Security: restrict to specific directories
        self.allowed_paths = [
            Path("./data"),
            Path("./temp"), 
            Path("./uploads"),
            Path("./outputs")
        ]
    
    def validate_input(self, **kwargs) -> Optional[str]:
        operation = kwargs.get("operation")
        if not operation or operation not in ["read", "write", "list", "mkdir", "delete", "exists"]:
            return "Operation must be one of: read, write, list, mkdir, delete, exists"
        
        file_path = kwargs.get("file_path")
        if not file_path:
            return "file_path parameter is required"
        
        # Security check: ensure path is within allowed directories
        try:
            path_obj = Path(file_path).resolve()
            allowed = any(
                str(path_obj).startswith(str(allowed.resolve())) 
                for allowed in self.allowed_paths
            )
            if not allowed:
                return f"Access denied. Path must be within allowed directories: {[str(p) for p in self.allowed_paths]}"
        except Exception:
            return "Invalid file path"
        
        if operation == "write" and not kwargs.get("content"):
            return "content parameter required for write operation"
        
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    async def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        operation = kwargs["operation"]
        file_path = Path(kwargs["file_path"])
        
        try:
            if operation == "read":
                if not file_path.exists():
                    return self._create_error_response("File does not exist", "FILE_NOT_FOUND")
                
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                
                return self._create_success_response({
                    "content": content,
                    "size": len(content),
                    "path": str(file_path),
                    "mime_type": mimetypes.guess_type(str(file_path))[0]
                })
            
            elif operation == "write":
                content = kwargs["content"]
                mode = kwargs.get("mode", "w")  # w for overwrite, a for append
                
                # Create directory if it doesn't exist
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                async with aiofiles.open(file_path, mode, encoding='utf-8') as f:
                    await f.write(content)
                
                return self._create_success_response({
                    "path": str(file_path),
                    "size": len(content),
                    "operation": "written"
                })
            
            elif operation == "list":
                if not file_path.exists():
                    return self._create_error_response("Directory does not exist", "DIR_NOT_FOUND")
                
                if not file_path.is_dir():
                    return self._create_error_response("Path is not a directory", "NOT_DIRECTORY")
                
                files = []
                for item in file_path.iterdir():
                    stat = item.stat()
                    files.append({
                        "name": item.name,
                        "path": str(item),
                        "type": "directory" if item.is_dir() else "file",
                        "size": stat.st_size,
                        "modified": stat.st_mtime
                    })
                
                return self._create_success_response({
                    "files": files,
                    "count": len(files),
                    "directory": str(file_path)
                })
            
            elif operation == "mkdir":
                file_path.mkdir(parents=True, exist_ok=True)
                return self._create_success_response({
                    "path": str(file_path),
                    "operation": "directory_created"
                })
            
            elif operation == "delete":
                if not file_path.exists():
                    return self._create_error_response("File/directory does not exist", "NOT_FOUND")
                
                if file_path.is_dir():
                    import shutil
                    await asyncio.to_thread(shutil.rmtree, file_path)
                else:
                    file_path.unlink()
                
                return self._create_success_response({
                    "path": str(file_path),
                    "operation": "deleted"
                })
            
            elif operation == "exists":
                exists = file_path.exists()
                return self._create_success_response({
                    "path": str(file_path),
                    "exists": exists,
                    "type": "directory" if file_path.is_dir() else "file" if exists else None
                })
        
        except Exception as e:
            return self._create_error_response(f"File operation failed: {str(e)}", "FILE_ERROR")


class WebScrapingTool(AsyncTool):
    """Tool for web scraping and content extraction."""
    
    def __init__(self):
        super().__init__(
            name="web_scraping", 
            description="Scrapes web content from URLs, extracts text, handles different formats."
        )
    
    def validate_input(self, **kwargs) -> Optional[str]:
        url = kwargs.get("url")
        if not url:
            return "url parameter is required"
        
        # Basic URL validation
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return "Invalid URL format"
        except Exception:
            return "Invalid URL"
        
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    async def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        url = kwargs["url"]
        extract_text = kwargs.get("extract_text", True)
        follow_redirects = kwargs.get("follow_redirects", True)
        timeout = kwargs.get("timeout", 30)
        
        try:
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            headers = {
                "User-Agent": "HART-MCP/1.0 (AI Agent System)"
            }
            
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.get(url, headers=headers, allow_redirects=follow_redirects) as response:
                    content_type = response.headers.get("content-type", "")
                    content = await response.text()
                    
                    result = {
                        "url": str(response.url),
                        "status_code": response.status,
                        "content_type": content_type,
                        "content_length": len(content),
                        "headers": dict(response.headers)
                    }
                    
                    if extract_text and "html" in content_type.lower():
                        # Extract text from HTML
                        try:
                            from bs4 import BeautifulSoup
                            soup = BeautifulSoup(content, 'html.parser')
                            
                            # Remove script and style elements
                            for script in soup(["script", "style"]):
                                script.decompose()
                            
                            # Extract text
                            text = soup.get_text()
                            lines = (line.strip() for line in text.splitlines())
                            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                            text = ' '.join(chunk for chunk in chunks if chunk)
                            
                            result["extracted_text"] = text
                            result["title"] = soup.title.string if soup.title else None
                            
                            # Extract links
                            links = []
                            for link in soup.find_all('a', href=True):
                                absolute_url = urljoin(url, link['href'])
                                links.append({
                                    "text": link.get_text(strip=True),
                                    "url": absolute_url
                                })
                            result["links"] = links[:50]  # Limit to first 50 links
                            
                        except ImportError:
                            result["extracted_text"] = "BeautifulSoup not available for HTML parsing"
                        except Exception as e:
                            result["extracted_text"] = f"Text extraction failed: {str(e)}"
                    else:
                        result["raw_content"] = content
                    
                    return self._create_success_response(result)
        
        except aiohttp.ClientError as e:
            return self._create_error_response(f"HTTP request failed: {str(e)}", "HTTP_ERROR")
        except Exception as e:
            return self._create_error_response(f"Web scraping failed: {str(e)}", "SCRAPING_ERROR")


class APIIntegrationTool(AsyncTool):
    """Tool for calling external REST APIs."""
    
    def __init__(self):
        super().__init__(
            name="api_integration",
            description="Makes HTTP requests to external APIs with proper authentication and error handling."
        )
    
    def validate_input(self, **kwargs) -> Optional[str]:
        url = kwargs.get("url")
        if not url:
            return "url parameter is required"
        
        method = kwargs.get("method", "GET").upper()
        if method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            return "Invalid HTTP method"
        
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    async def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        url = kwargs["url"]
        method = kwargs.get("method", "GET").upper()
        headers = kwargs.get("headers", {})
        data = kwargs.get("data")
        params = kwargs.get("params")
        timeout = kwargs.get("timeout", 30)
        auth = kwargs.get("auth")  # {"type": "bearer", "token": "..."} or {"type": "basic", "username": "...", "password": "..."}
        
        try:
            # Setup authentication
            if auth:
                if auth.get("type") == "bearer":
                    headers["Authorization"] = f"Bearer {auth.get('token')}"
                elif auth.get("type") == "basic":
                    import base64
                    credentials = f"{auth.get('username')}:{auth.get('password')}"
                    encoded = base64.b64encode(credentials.encode()).decode()
                    headers["Authorization"] = f"Basic {encoded}"
            
            timeout_obj = aiohttp.ClientTimeout(total=timeout)
            
            async with aiohttp.ClientSession(timeout=timeout_obj) as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=data if isinstance(data, (dict, list)) else None,
                    data=data if isinstance(data, (str, bytes)) else None,
                    params=params
                ) as response:
                    
                    # Try to parse JSON response
                    try:
                        content = await response.json()
                    except:
                        content = await response.text()
                    
                    return self._create_success_response({
                        "url": str(response.url),
                        "method": method,
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "content": content,
                        "success": 200 <= response.status < 300
                    })
        
        except aiohttp.ClientError as e:
            return self._create_error_response(f"API request failed: {str(e)}", "API_ERROR")
        except Exception as e:
            return self._create_error_response(f"API integration failed: {str(e)}", "INTEGRATION_ERROR")


class CodeExecutionTool(AsyncTool):
    """Tool for safe code execution (Python only for now)."""
    
    def __init__(self):
        super().__init__(
            name="code_execution",
            description="Safely executes Python code snippets in a controlled environment."
        )
        self.restricted_imports = {
            "os", "subprocess", "sys", "importlib", "__import__",
            "open", "file", "execfile", "reload", "input", "raw_input"
        }
    
    def validate_input(self, **kwargs) -> Optional[str]:
        code = kwargs.get("code")
        if not code:
            return "code parameter is required"
        
        if not isinstance(code, str):
            return "code must be a string"
        
        # Basic security checks
        if any(restricted in code for restricted in self.restricted_imports):
            return f"Code contains restricted imports: {self.restricted_imports}"
        
        dangerous_patterns = ["exec(", "eval(", "compile(", "__"]
        if any(pattern in code for pattern in dangerous_patterns):
            return "Code contains potentially dangerous patterns"
        
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    async def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        code = kwargs["code"]
        timeout = kwargs.get("timeout", 10)  # 10 second limit
        
        try:
            # Create restricted environment
            import io
            import contextlib
            from RestrictedPython import compile_restricted, safe_globals
            
            # Compile the code with restrictions
            compiled_code = compile_restricted(code, filename="<agent_code>", mode="exec")
            if compiled_code is None:
                return self._create_error_response("Code compilation failed - security restriction", "COMPILATION_ERROR")
            
            # Capture stdout
            output_buffer = io.StringIO()
            
            # Safe execution environment
            exec_globals = safe_globals.copy()
            exec_globals.update({
                "__builtins__": {
                    "abs": abs, "all": all, "any": any, "bool": bool, "chr": chr,
                    "dict": dict, "enumerate": enumerate, "float": float, "int": int,
                    "len": len, "list": list, "max": max, "min": min, "ord": ord,
                    "range": range, "reversed": reversed, "round": round, "set": set,
                    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple, "type": type,
                    "zip": zip, "print": lambda *args, **kwargs: print(*args, **kwargs, file=output_buffer)
                },
                "json": json,
                "math": __import__("math")
            })
            
            # Execute with timeout
            def execute_code():
                exec(compiled_code, exec_globals)
                return output_buffer.getvalue()
            
            output = await asyncio.wait_for(
                asyncio.to_thread(execute_code),
                timeout=timeout
            )
            
            return self._create_success_response({
                "output": output,
                "execution_time": timeout,
                "success": True
            })
        
        except ImportError:
            return self._create_error_response("RestrictedPython not available for safe execution", "DEPENDENCY_ERROR")
        except asyncio.TimeoutError:
            return self._create_error_response("Code execution timed out", "TIMEOUT_ERROR")
        except Exception as e:
            return self._create_error_response(f"Code execution failed: {str(e)}", "EXECUTION_ERROR")


class ValidationTool(Tool):
    """Tool for data validation and schema checking."""
    
    def __init__(self):
        super().__init__(
            name="validation",
            description="Validates data against schemas, checks types, formats, constraints."
        )
    
    def validate_input(self, **kwargs) -> Optional[str]:
        data = kwargs.get("data")
        if data is None:
            return "data parameter is required"
        
        validation_type = kwargs.get("validation_type")
        if not validation_type:
            return "validation_type parameter is required (json_schema, type_check, format_check, range_check)"
        
        if validation_type not in ["json_schema", "type_check", "format_check", "range_check"]:
            return "Invalid validation_type"
        
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        data = kwargs["data"]
        validation_type = kwargs["validation_type"]
        
        try:
            if validation_type == "json_schema":
                schema = kwargs.get("schema")
                if not schema:
                    return self._create_error_response("schema parameter required for json_schema validation", "MISSING_SCHEMA")
                
                try:
                    import jsonschema
                    jsonschema.validate(data, schema)
                    return self._create_success_response({
                        "valid": True,
                        "data": data,
                        "validation_type": validation_type
                    })
                except ImportError:
                    return self._create_error_response("jsonschema library not available", "DEPENDENCY_ERROR")
                except jsonschema.ValidationError as e:
                    return self._create_success_response({
                        "valid": False,
                        "errors": [str(e)],
                        "validation_type": validation_type
                    })
            
            elif validation_type == "type_check":
                expected_type = kwargs.get("expected_type")
                if not expected_type:
                    return self._create_error_response("expected_type parameter required", "MISSING_TYPE")
                
                type_map = {
                    "string": str, "str": str,
                    "integer": int, "int": int,
                    "float": float,
                    "boolean": bool, "bool": bool,
                    "list": list,
                    "dict": dict,
                    "none": type(None)
                }
                
                expected = type_map.get(expected_type.lower())
                if not expected:
                    return self._create_error_response(f"Unknown type: {expected_type}", "INVALID_TYPE")
                
                is_valid = isinstance(data, expected)
                return self._create_success_response({
                    "valid": is_valid,
                    "expected_type": expected_type,
                    "actual_type": type(data).__name__,
                    "data": data
                })
            
            elif validation_type == "format_check":
                format_type = kwargs.get("format_type")
                if not format_type:
                    return self._create_error_response("format_type parameter required", "MISSING_FORMAT")
                
                import re
                
                format_patterns = {
                    "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                    "url": r'^https?://[^\s/$.?#].[^\s]*$',
                    "uuid": r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                    "phone": r'^\+?1?-?\(?[0-9]{3}\)?-?[0-9]{3}-?[0-9]{4}$'
                }
                
                pattern = format_patterns.get(format_type)
                if not pattern:
                    return self._create_error_response(f"Unknown format type: {format_type}", "INVALID_FORMAT")
                
                is_valid = bool(re.match(pattern, str(data), re.IGNORECASE))
                return self._create_success_response({
                    "valid": is_valid,
                    "format_type": format_type,
                    "data": data
                })
            
            elif validation_type == "range_check":
                min_val = kwargs.get("min_value")
                max_val = kwargs.get("max_value")
                
                if min_val is None and max_val is None:
                    return self._create_error_response("Either min_value or max_value required", "MISSING_RANGE")
                
                try:
                    numeric_data = float(data)
                    errors = []
                    
                    if min_val is not None and numeric_data < min_val:
                        errors.append(f"Value {numeric_data} is less than minimum {min_val}")
                    
                    if max_val is not None and numeric_data > max_val:
                        errors.append(f"Value {numeric_data} is greater than maximum {max_val}")
                    
                    return self._create_success_response({
                        "valid": len(errors) == 0,
                        "errors": errors,
                        "value": numeric_data,
                        "min_value": min_val,
                        "max_value": max_val
                    })
                
                except (ValueError, TypeError):
                    return self._create_error_response("Data is not numeric for range check", "INVALID_DATA")
        
        except Exception as e:
            return self._create_error_response(f"Validation failed: {str(e)}", "VALIDATION_ERROR")