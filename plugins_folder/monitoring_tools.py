"""System monitoring and health check tools for production readiness."""
import asyncio
import time
import psutil
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json

from .tool_base import Tool, AsyncTool
from utils.error_handlers import ErrorCode, safe_execute


@dataclass
class SystemMetrics:
    """System performance metrics."""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_available: int
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    active_connections: int
    process_count: int
    uptime_seconds: float


class SystemMonitoringTool(Tool):
    """Tool for monitoring system health and performance metrics."""
    
    def __init__(self):
        super().__init__(
            name="system_monitoring",
            description="Monitors system health: CPU, memory, disk, network, processes."
        )
        self._boot_time = psutil.boot_time()
    
    def validate_input(self, **kwargs) -> Optional[str]:
        metric_type = kwargs.get("metric_type", "all")
        if metric_type not in ["all", "cpu", "memory", "disk", "network", "processes"]:
            return "metric_type must be one of: all, cpu, memory, disk, network, processes"
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        metric_type = kwargs.get("metric_type", "all")
        
        try:
            current_time = datetime.now().isoformat()
            metrics = {}
            
            if metric_type in ["all", "cpu"]:
                # CPU metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
                
                metrics["cpu"] = {
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "load_average": load_avg
                }
            
            if metric_type in ["all", "memory"]:
                # Memory metrics
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                metrics["memory"] = {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent,
                    "used": memory.used,
                    "free": memory.free,
                    "swap_total": swap.total,
                    "swap_used": swap.used,
                    "swap_percent": swap.percent
                }
            
            if metric_type in ["all", "disk"]:
                # Disk metrics
                disk_usage = psutil.disk_usage('/')
                disk_io = psutil.disk_io_counters()
                
                metrics["disk"] = {
                    "total": disk_usage.total,
                    "used": disk_usage.used,
                    "free": disk_usage.free,
                    "percent": disk_usage.percent,
                    "read_bytes": disk_io.read_bytes if disk_io else 0,
                    "write_bytes": disk_io.write_bytes if disk_io else 0,
                    "read_count": disk_io.read_count if disk_io else 0,
                    "write_count": disk_io.write_count if disk_io else 0
                }
            
            if metric_type in ["all", "network"]:
                # Network metrics
                net_io = psutil.net_io_counters()
                connections = len(psutil.net_connections())
                
                metrics["network"] = {
                    "bytes_sent": net_io.bytes_sent,
                    "bytes_recv": net_io.bytes_recv,
                    "packets_sent": net_io.packets_sent,
                    "packets_recv": net_io.packets_recv,
                    "active_connections": connections
                }
            
            if metric_type in ["all", "processes"]:
                # Process metrics
                processes = list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']))
                process_count = len(processes)
                
                # Top 5 CPU consumers
                top_cpu = sorted(processes, 
                               key=lambda p: p.info.get('cpu_percent', 0), 
                               reverse=True)[:5]
                
                # Top 5 memory consumers
                top_memory = sorted(processes,
                                  key=lambda p: p.info.get('memory_percent', 0),
                                  reverse=True)[:5]
                
                metrics["processes"] = {
                    "total_count": process_count,
                    "top_cpu": [{
                        "pid": p.info['pid'],
                        "name": p.info['name'],
                        "cpu_percent": p.info.get('cpu_percent', 0)
                    } for p in top_cpu],
                    "top_memory": [{
                        "pid": p.info['pid'],
                        "name": p.info['name'],
                        "memory_percent": p.info.get('memory_percent', 0)
                    } for p in top_memory]
                }
            
            # System uptime
            uptime_seconds = time.time() - self._boot_time
            metrics["system"] = {
                "uptime_seconds": uptime_seconds,
                "uptime_human": str(timedelta(seconds=int(uptime_seconds))),
                "boot_time": datetime.fromtimestamp(self._boot_time).isoformat()
            }
            
            return self._create_success_response({
                "timestamp": current_time,
                "metrics": metrics,
                "metric_type": metric_type
            })
        
        except Exception as e:
            return self._create_error_response(f"System monitoring failed: {str(e)}", "MONITORING_ERROR")


class HealthCheckTool(AsyncTool):
    """Tool for comprehensive system health checks."""
    
    def __init__(self):
        super().__init__(
            name="health_check",
            description="Performs comprehensive health checks on system components."
        )
    
    def validate_input(self, **kwargs) -> Optional[str]:
        components = kwargs.get("components", ["all"])
        if isinstance(components, str):
            components = [components]
        
        valid_components = ["all", "database", "llm", "filesystem", "network", "memory"]
        for component in components:
            if component not in valid_components:
                return f"Invalid component '{component}'. Valid: {valid_components}"
        
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    async def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        components = kwargs.get("components", ["all"])
        if isinstance(components, str):
            components = [components]
        
        if "all" in components:
            components = ["database", "llm", "filesystem", "network", "memory"]
        
        health_results = {}
        overall_healthy = True
        
        try:
            # Database health check
            if "database" in components:
                db_health = await self._check_database_health()
                health_results["database"] = db_health
                if not db_health["healthy"]:
                    overall_healthy = False
            
            # LLM health check
            if "llm" in components:
                llm_health = await self._check_llm_health()
                health_results["llm"] = llm_health
                if not llm_health["healthy"]:
                    overall_healthy = False
            
            # Filesystem health check
            if "filesystem" in components:
                fs_health = self._check_filesystem_health()
                health_results["filesystem"] = fs_health
                if not fs_health["healthy"]:
                    overall_healthy = False
            
            # Network health check
            if "network" in components:
                net_health = await self._check_network_health()
                health_results["network"] = net_health
                if not net_health["healthy"]:
                    overall_healthy = False
            
            # Memory health check
            if "memory" in components:
                mem_health = self._check_memory_health()
                health_results["memory"] = mem_health
                if not mem_health["healthy"]:
                    overall_healthy = False
            
            return self._create_success_response({
                "overall_healthy": overall_healthy,
                "timestamp": datetime.now().isoformat(),
                "components_checked": components,
                "results": health_results
            })
        
        except Exception as e:
            return self._create_error_response(f"Health check failed: {str(e)}", "HEALTH_CHECK_ERROR")
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and health."""
        try:
            from services.unified_database_service import EnhancedUnifiedSearchService
            
            service = EnhancedUnifiedSearchService()
            
            # Test basic connectivity
            start_time = time.time()
            result = await service.search_all("health_check", limit=1)
            response_time = time.time() - start_time
            
            return {
                "healthy": True,
                "response_time_seconds": response_time,
                "services_attempted": result.get("services_attempted", []),
                "errors": result.get("errors", [])
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "response_time_seconds": None
            }
    
    async def _check_llm_health(self) -> Dict[str, Any]:
        """Check LLM connectivity and health."""
        try:
            from llm_connector import LLMClient
            
            client = LLMClient()
            
            start_time = time.time()
            response = await client.invoke("Health check: respond with 'OK' if you can process this message.")
            response_time = time.time() - start_time
            
            # Simple validation of response
            is_healthy = len(response) > 0 and isinstance(response, str)
            
            return {
                "healthy": is_healthy,
                "response_time_seconds": response_time,
                "response_length": len(response),
                "response_sample": response[:100] if response else None
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "response_time_seconds": None
            }
    
    def _check_filesystem_health(self) -> Dict[str, Any]:
        """Check filesystem health and permissions."""
        try:
            import tempfile
            import os
            
            # Test write permissions
            with tempfile.NamedTemporaryFile(mode='w', delete=True) as temp_file:
                test_content = "health_check_test"
                temp_file.write(test_content)
                temp_file.flush()
                
                # Test read
                with open(temp_file.name, 'r') as read_file:
                    read_content = read_file.read()
                
                write_test_passed = read_content == test_content
            
            # Check disk space
            disk_usage = psutil.disk_usage('/')
            free_percent = (disk_usage.free / disk_usage.total) * 100
            
            return {
                "healthy": write_test_passed and free_percent > 10,  # Need at least 10% free
                "write_test_passed": write_test_passed,
                "free_space_percent": free_percent,
                "free_space_bytes": disk_usage.free
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def _check_network_health(self) -> Dict[str, Any]:
        """Check network connectivity."""
        try:
            import aiohttp
            
            # Test external connectivity
            test_urls = ["https://httpbin.org/status/200", "https://www.google.com"]
            results = []
            
            for url in test_urls:
                try:
                    start_time = time.time()
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            response_time = time.time() - start_time
                            results.append({
                                "url": url,
                                "status": response.status,
                                "response_time": response_time,
                                "success": 200 <= response.status < 300
                            })
                except Exception as e:
                    results.append({
                        "url": url,
                        "error": str(e),
                        "success": False
                    })
            
            successful_tests = sum(1 for r in results if r.get("success", False))
            healthy = successful_tests > 0  # At least one URL should be reachable
            
            return {
                "healthy": healthy,
                "tests_passed": successful_tests,
                "total_tests": len(results),
                "results": results
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def _check_memory_health(self) -> Dict[str, Any]:
        """Check memory usage and health."""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Memory is healthy if less than 90% used
            memory_healthy = memory.percent < 90
            swap_healthy = swap.percent < 50 if swap.total > 0 else True
            
            return {
                "healthy": memory_healthy and swap_healthy,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "swap_percent": swap.percent if swap.total > 0 else 0,
                "memory_healthy": memory_healthy,
                "swap_healthy": swap_healthy
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }


class PerformanceBenchmarkTool(AsyncTool):
    """Tool for running performance benchmarks."""
    
    def __init__(self):
        super().__init__(
            name="performance_benchmark",
            description="Runs performance benchmarks to test system capabilities."
        )
    
    def validate_input(self, **kwargs) -> Optional[str]:
        benchmark_type = kwargs.get("benchmark_type", "basic")
        if benchmark_type not in ["basic", "cpu", "memory", "io", "network", "database", "llm"]:
            return "benchmark_type must be one of: basic, cpu, memory, io, network, database, llm"
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    async def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        benchmark_type = kwargs.get("benchmark_type", "basic")
        duration = kwargs.get("duration", 10)  # seconds
        
        try:
            if benchmark_type == "basic":
                results = await self._run_basic_benchmark(duration)
            elif benchmark_type == "cpu":
                results = await self._run_cpu_benchmark(duration)
            elif benchmark_type == "memory":
                results = await self._run_memory_benchmark(duration)
            elif benchmark_type == "io":
                results = await self._run_io_benchmark(duration)
            elif benchmark_type == "llm":
                results = await self._run_llm_benchmark(duration)
            else:
                return self._create_error_response(f"Benchmark type '{benchmark_type}' not implemented", "NOT_IMPLEMENTED")
            
            return self._create_success_response({
                "benchmark_type": benchmark_type,
                "duration_seconds": duration,
                "results": results,
                "timestamp": datetime.now().isoformat()
            })
        
        except Exception as e:
            return self._create_error_response(f"Benchmark failed: {str(e)}", "BENCHMARK_ERROR")
    
    async def _run_basic_benchmark(self, duration: int) -> Dict[str, Any]:
        """Run basic system benchmark."""
        start_time = time.time()
        operations = 0
        
        # Simple CPU-bound operations
        while time.time() - start_time < duration:
            # Math operations
            for i in range(1000):
                _ = i ** 2 + i * 3 + 42
            operations += 1000
            
            # Yield control occasionally
            if operations % 10000 == 0:
                await asyncio.sleep(0.001)
        
        actual_duration = time.time() - start_time
        ops_per_second = operations / actual_duration
        
        return {
            "operations_completed": operations,
            "operations_per_second": ops_per_second,
            "actual_duration": actual_duration
        }
    
    async def _run_cpu_benchmark(self, duration: int) -> Dict[str, Any]:
        """Run CPU-intensive benchmark."""
        start_time = time.time()
        calculations = 0
        
        # Prime number calculation
        def is_prime(n):
            if n < 2:
                return False
            for i in range(2, int(n ** 0.5) + 1):
                if n % i == 0:
                    return False
            return True
        
        number = 2
        primes_found = 0
        
        while time.time() - start_time < duration:
            if is_prime(number):
                primes_found += 1
            number += 1
            calculations += 1
            
            # Yield occasionally
            if calculations % 1000 == 0:
                await asyncio.sleep(0.001)
        
        actual_duration = time.time() - start_time
        
        return {
            "calculations_performed": calculations,
            "primes_found": primes_found,
            "calculations_per_second": calculations / actual_duration,
            "largest_number_tested": number - 1,
            "actual_duration": actual_duration
        }
    
    async def _run_memory_benchmark(self, duration: int) -> Dict[str, Any]:
        """Run memory allocation benchmark."""
        start_time = time.time()
        allocations = 0
        total_bytes = 0
        
        arrays = []
        
        while time.time() - start_time < duration:
            # Allocate memory
            size = 1024 * 1024  # 1MB
            array = bytearray(size)
            arrays.append(array)
            allocations += 1
            total_bytes += size
            
            # Clean up periodically to avoid OOM
            if len(arrays) > 100:  # Keep max 100MB
                arrays.pop(0)
            
            await asyncio.sleep(0.01)  # Small delay
        
        actual_duration = time.time() - start_time
        
        return {
            "allocations_performed": allocations,
            "total_bytes_allocated": total_bytes,
            "mb_per_second": (total_bytes / (1024 * 1024)) / actual_duration,
            "peak_arrays_held": len(arrays),
            "actual_duration": actual_duration
        }
    
    async def _run_io_benchmark(self, duration: int) -> Dict[str, Any]:
        """Run I/O benchmark."""
        import tempfile
        
        start_time = time.time()
        operations = 0
        bytes_written = 0
        bytes_read = 0
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = f"{temp_dir}/benchmark.txt"
            test_data = "x" * 1024  # 1KB of data
            
            while time.time() - start_time < duration:
                # Write operation
                with open(test_file, 'w') as f:
                    f.write(test_data)
                bytes_written += len(test_data)
                operations += 1
                
                # Read operation
                with open(test_file, 'r') as f:
                    data = f.read()
                bytes_read += len(data)
                operations += 1
                
                await asyncio.sleep(0.001)  # Small yield
        
        actual_duration = time.time() - start_time
        
        return {
            "io_operations": operations,
            "bytes_written": bytes_written,
            "bytes_read": bytes_read,
            "mb_per_second": ((bytes_written + bytes_read) / (1024 * 1024)) / actual_duration,
            "operations_per_second": operations / actual_duration,
            "actual_duration": actual_duration
        }
    
    async def _run_llm_benchmark(self, duration: int) -> Dict[str, Any]:
        """Run LLM performance benchmark."""
        try:
            from llm_connector import LLMClient
            
            client = LLMClient()
            start_time = time.time()
            requests = 0
            total_response_time = 0
            errors = 0
            
            while time.time() - start_time < duration:
                try:
                    request_start = time.time()
                    response = await client.invoke(f"Benchmark test {requests}: respond with 'OK {requests}'")
                    request_end = time.time()
                    
                    request_time = request_end - request_start
                    total_response_time += request_time
                    requests += 1
                    
                except Exception:
                    errors += 1
                
                # Don't overwhelm the LLM
                await asyncio.sleep(1)
            
            actual_duration = time.time() - start_time
            avg_response_time = total_response_time / requests if requests > 0 else 0
            
            return {
                "requests_completed": requests,
                "requests_failed": errors,
                "average_response_time": avg_response_time,
                "requests_per_minute": (requests / actual_duration) * 60,
                "success_rate": requests / (requests + errors) if (requests + errors) > 0 else 0,
                "actual_duration": actual_duration
            }
        
        except ImportError:
            return {"error": "LLM client not available for benchmarking"}


class AlertingTool(Tool):
    """Tool for generating alerts and notifications."""
    
    def __init__(self):
        super().__init__(
            name="alerting",
            description="Generates alerts and notifications for system events."
        )
        self._logger = logging.getLogger(__name__)
    
    def validate_input(self, **kwargs) -> Optional[str]:
        alert_type = kwargs.get("alert_type")
        if not alert_type:
            return "alert_type parameter is required"
        
        if alert_type not in ["info", "warning", "error", "critical"]:
            return "alert_type must be one of: info, warning, error, critical"
        
        message = kwargs.get("message")
        if not message:
            return "message parameter is required"
        
        return None
    
    @safe_execute(ErrorCode.TOOL_EXECUTION)
    def execute(self, **kwargs) -> Dict[str, Any]:
        validation_error = self.validate_input(**kwargs)
        if validation_error:
            return self._create_error_response(validation_error, ErrorCode.VALIDATION_ERROR.value)
        
        alert_type = kwargs["alert_type"]
        message = kwargs["message"]
        component = kwargs.get("component", "system")
        metadata = kwargs.get("metadata", {})
        
        try:
            # Create alert record
            alert = {
                "id": f"alert_{int(time.time() * 1000)}",
                "type": alert_type,
                "component": component,
                "message": message,
                "metadata": metadata,
                "timestamp": datetime.now().isoformat(),
                "resolved": False
            }
            
            # Log alert
            log_level = {
                "info": logging.INFO,
                "warning": logging.WARNING,
                "error": logging.ERROR,
                "critical": logging.CRITICAL
            }[alert_type]
            
            self._logger.log(log_level, f"ALERT [{alert_type.upper()}] {component}: {message}", 
                           extra={"alert_metadata": metadata})
            
            # In production, this would send to monitoring systems
            # For now, just return the alert details
            
            return self._create_success_response({
                "alert": alert,
                "logged": True,
                "notification_sent": False  # Would be True in production with actual notification system
            })
        
        except Exception as e:
            return self._create_error_response(f"Alert generation failed: {str(e)}", "ALERT_ERROR")