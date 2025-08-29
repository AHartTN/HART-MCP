"""Essential tools using only basic Python dependencies."""
import os
import json
import asyncio
import tempfile
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
import mimetypes
import re
import time

from .tool_base import Tool, AsyncTool
from utils.error_handlers import ErrorCode, safe_execute


class BasicFileIOTool(AsyncTool):
    """File I/O tool using only standard library."""
    
    def __init__(self):
        super().__init__(
            name="basic_file_io",
            description="Basic file operations: read, write, list files using standard library."
        )
        # Security: restrict to specific directories
        self.allowed_paths = [
            Path("./data"),
            Path("./temp"), 
            Path("./uploads"),
            Path("./outputs")
        ]
        
        # Ensure directories exist
        for path in self.allowed_paths:
            path.mkdir(exist_ok=True)
    
    def validate_input(self, **kwargs) -> Optional[str]:
        operation = kwargs.get("operation")
        if not operation or operation not in ["read", "write", "list", "mkdir", "delete", "exists"]:
            return "Operation must be one of: read, write, list, mkdir, delete, exists"
        
        file_path = kwargs.get("file_path")
        if not file_path:
            return "file_path parameter is required"
        
        # Security check
        try:
            path_obj = Path(file_path).resolve()
            allowed = any(
                str(path_obj).startswith(str(allowed.resolve())) 
                for allowed in self.allowed_paths
            )
            if not allowed:
                return f"Access denied. Path must be within: {[str(p) for p in self.allowed_paths]}"
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
                
                def read_file():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return f.read()
                
                content = await asyncio.to_thread(read_file)
                
                return self._create_success_response({
                    "content": content,
                    "size": len(content),
                    "path": str(file_path),
                    "mime_type": mimetypes.guess_type(str(file_path))[0]
                })
            
            elif operation == "write":
                content = kwargs["content"]
                mode = kwargs.get("mode", "w")
                
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                def write_file():
                    with open(file_path, mode, encoding='utf-8') as f:
                        f.write(content)
                
                await asyncio.to_thread(write_file)
                
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
            
            elif operation == "exists":
                exists = file_path.exists()
                return self._create_success_response({
                    "path": str(file_path),
                    "exists": exists,
                    "type": "directory" if file_path.is_dir() else "file" if exists else None
                })
        
        except Exception as e:
            return self._create_error_response(f"File operation failed: {str(e)}", "FILE_ERROR")


class BasicWebFetchTool(AsyncTool):
    """Basic web fetching using urllib."""
    
    def __init__(self):
        super().__init__(
            name="basic_web_fetch",
            description="Basic web content fetching using urllib."
        )
    
    def validate_input(self, **kwargs) -> Optional[str]:
        url = kwargs.get("url")
        if not url:
            return "url parameter is required"
        
        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return "Invalid URL format"
            if parsed.scheme not in ['http', 'https']:
                return "Only HTTP/HTTPS URLs are allowed"
        except Exception:
            return "Invalid URL"
        
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    async def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        url = kwargs["url"]
        timeout = kwargs.get("timeout", 30)
        
        try:
            def fetch_url():
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'HART-MCP/1.0 (AI Agent System)'}
                )
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    content = response.read().decode('utf-8', errors='ignore')
                    return {
                        "content": content,
                        "status_code": response.getcode(),
                        "headers": dict(response.headers),
                        "url": response.geturl(),
                        "content_length": len(content)
                    }
            
            result = await asyncio.to_thread(fetch_url)
            
            # Basic text extraction for HTML
            content_type = result["headers"].get("content-type", "")
            if "html" in content_type.lower():
                # Simple HTML tag removal
                text = re.sub(r'<[^>]+>', ' ', result["content"])
                text = re.sub(r'\s+', ' ', text).strip()
                result["extracted_text"] = text[:5000]  # Limit to 5000 chars
            
            return self._create_success_response(result)
        
        except Exception as e:
            return self._create_error_response(f"Web fetch failed: {str(e)}", "WEB_FETCH_ERROR")


class BasicValidationTool(Tool):
    """Basic validation tool using only standard library."""
    
    def __init__(self):
        super().__init__(
            name="basic_validation",
            description="Basic data validation using standard library."
        )
    
    def validate_input(self, **kwargs) -> Optional[str]:
        data = kwargs.get("data")
        if data is None:
            return "data parameter is required"
        
        validation_type = kwargs.get("validation_type")
        if not validation_type:
            return "validation_type parameter is required"
        
        if validation_type not in ["type_check", "format_check", "range_check", "length_check"]:
            return "validation_type must be one of: type_check, format_check, range_check, length_check"
        
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        data = kwargs["data"]
        validation_type = kwargs["validation_type"]
        
        try:
            if validation_type == "type_check":
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
                
                format_patterns = {
                    "email": r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
                    "url": r'^https?://[^\s/$.?#].[^\s]*$',
                    "uuid": r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
                    "phone": r'^\+?1?-?\(?[0-9]{3}\)?-?[0-9]{3}-?[0-9]{4}$',
                    "ip_address": r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
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
            
            elif validation_type == "length_check":
                min_length = kwargs.get("min_length")
                max_length = kwargs.get("max_length")
                
                if min_length is None and max_length is None:
                    return self._create_error_response("Either min_length or max_length required", "MISSING_LENGTH")
                
                try:
                    data_length = len(data)
                    errors = []
                    
                    if min_length is not None and data_length < min_length:
                        errors.append(f"Length {data_length} is less than minimum {min_length}")
                    
                    if max_length is not None and data_length > max_length:
                        errors.append(f"Length {data_length} is greater than maximum {max_length}")
                    
                    return self._create_success_response({
                        "valid": len(errors) == 0,
                        "errors": errors,
                        "length": data_length,
                        "min_length": min_length,
                        "max_length": max_length
                    })
                
                except TypeError:
                    return self._create_error_response("Data type does not support length check", "INVALID_DATA")
        
        except Exception as e:
            return self._create_error_response(f"Validation failed: {str(e)}", "VALIDATION_ERROR")


class BasicSystemInfoTool(Tool):
    """Basic system information tool."""
    
    def __init__(self):
        super().__init__(
            name="basic_system_info",
            description="Gets basic system information: platform, Python version, memory, disk."
        )
    
    def validate_input(self, **kwargs) -> Optional[str]:
        return None  # No validation needed for system info
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    def execute(self, **kwargs) -> Dict[str, Any]:
        try:
            import platform
            import sys
            
            system_info = {
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor(),
                    "architecture": platform.architecture()
                },
                "python": {
                    "version": sys.version,
                    "version_info": sys.version_info[:3],
                    "executable": sys.executable,
                    "platform": sys.platform
                },
                "timestamp": time.time()
            }
            
            # Add memory info if available
            try:
                import psutil
                memory = psutil.virtual_memory()
                system_info["memory"] = {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": memory.percent
                }
                
                disk = psutil.disk_usage('/')
                system_info["disk"] = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "percent_used": round((disk.used / disk.total) * 100, 2)
                }
                
                system_info["cpu"] = {
                    "count": psutil.cpu_count(),
                    "percent": psutil.cpu_percent(interval=1)
                }
            except ImportError:
                system_info["memory"] = "psutil not available"
            
            return self._create_success_response(system_info)
        
        except Exception as e:
            return self._create_error_response(f"System info collection failed: {str(e)}", "SYSTEM_INFO_ERROR")


class BasicDataProcessingTool(Tool):
    """Basic data processing operations."""
    
    def __init__(self):
        super().__init__(
            name="basic_data_processing",
            description="Basic data operations: JSON parsing, CSV processing, text manipulation."
        )
    
    def validate_input(self, **kwargs) -> Optional[str]:
        operation = kwargs.get("operation")
        if not operation:
            return "operation parameter is required"
        
        if operation not in ["json_parse", "json_stringify", "csv_parse", "text_clean", "text_split"]:
            return "operation must be one of: json_parse, json_stringify, csv_parse, text_clean, text_split"
        
        data = kwargs.get("data")
        if data is None:
            return "data parameter is required"
        
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        operation = kwargs["operation"]
        data = kwargs["data"]
        
        try:
            if operation == "json_parse":
                if isinstance(data, str):
                    parsed = json.loads(data)
                else:
                    return self._create_error_response("Data must be string for JSON parsing", "INVALID_DATA")
                
                return self._create_success_response({
                    "parsed_data": parsed,
                    "type": type(parsed).__name__,
                    "keys": list(parsed.keys()) if isinstance(parsed, dict) else None
                })
            
            elif operation == "json_stringify":
                stringified = json.dumps(data, indent=2)
                return self._create_success_response({
                    "json_string": stringified,
                    "length": len(stringified)
                })
            
            elif operation == "csv_parse":
                if not isinstance(data, str):
                    return self._create_error_response("Data must be string for CSV parsing", "INVALID_DATA")
                
                import csv
                import io
                
                reader = csv.DictReader(io.StringIO(data))
                rows = list(reader)
                
                return self._create_success_response({
                    "rows": rows,
                    "count": len(rows),
                    "columns": reader.fieldnames if reader.fieldnames else []
                })
            
            elif operation == "text_clean":
                if not isinstance(data, str):
                    return self._create_error_response("Data must be string for text cleaning", "INVALID_DATA")
                
                # Basic text cleaning
                cleaned = data.strip()
                cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace
                cleaned = re.sub(r'[^\w\s\-.,!?;:()\[\]{}"\']', '', cleaned)  # Remove special chars
                
                return self._create_success_response({
                    "original_length": len(data),
                    "cleaned_text": cleaned,
                    "cleaned_length": len(cleaned),
                    "chars_removed": len(data) - len(cleaned)
                })
            
            elif operation == "text_split":
                if not isinstance(data, str):
                    return self._create_error_response("Data must be string for text splitting", "INVALID_DATA")
                
                delimiter = kwargs.get("delimiter", " ")
                max_splits = kwargs.get("max_splits")
                
                if max_splits:
                    parts = data.split(delimiter, max_splits)
                else:
                    parts = data.split(delimiter)
                
                return self._create_success_response({
                    "parts": parts,
                    "count": len(parts),
                    "delimiter": delimiter
                })
        
        except json.JSONDecodeError as e:
            return self._create_error_response(f"JSON parsing error: {str(e)}", "JSON_ERROR")
        except Exception as e:
            return self._create_error_response(f"Data processing failed: {str(e)}", "PROCESSING_ERROR")