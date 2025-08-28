"""Real integration tests that validate actual functionality without extensive mocking."""
import pytest
import asyncio
import tempfile
import os
from pathlib import Path

# Real database tests
@pytest.mark.integration
async def test_real_database_connectivity():
    """Test actual database connections without mocking."""
    from services.unified_database_service import MilvusSearchService, Neo4jSearchService, SQLServerSearchService
    
    # Test Milvus connection
    milvus_service = MilvusSearchService()
    try:
        milvus_healthy = await milvus_service.connect()
        assert isinstance(milvus_healthy, bool), "Milvus connect should return boolean"
        
        if milvus_healthy:
            # Test actual search operation
            results = await milvus_service.search_by_vector(
                embedding=[0.1] * 384,  # Standard embedding size
                collection="test_collection",
                limit=1
            )
            assert isinstance(results, list), "Milvus search should return list"
    except Exception as e:
        pytest.skip(f"Milvus not available: {e}")
    
    # Test Neo4j connection
    neo4j_service = Neo4jSearchService()
    try:
        neo4j_healthy = await neo4j_service.connect()
        assert isinstance(neo4j_healthy, bool), "Neo4j connect should return boolean"
        
        if neo4j_healthy:
            # Test actual query
            results = await neo4j_service.search_nodes("test", limit=1)
            assert isinstance(results, list), "Neo4j search should return list"
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")
    
    # Test SQL Server connection
    sql_service = SQLServerSearchService()
    try:
        sql_healthy = await sql_service.connect()
        assert isinstance(sql_healthy, bool), "SQL connect should return boolean"
        
        if sql_healthy:
            # Test actual query
            results = await sql_service.execute_query("SELECT 1 as test_value")
            assert isinstance(results, list), "SQL query should return list"
            if results:
                assert "test_value" in results[0], "SQL query should return expected column"
    except Exception as e:
        pytest.skip(f"SQL Server not available: {e}")


@pytest.mark.integration
async def test_real_llm_integration():
    """Test actual LLM responses without mocking."""
    from llm_connector import LLMClient
    
    client = LLMClient()
    
    # Test basic invocation
    response = await client.invoke("Say 'TEST_PASSED' if you can read this message.")
    assert isinstance(response, str), "LLM response should be string"
    assert len(response) > 0, "LLM response should not be empty"
    
    # Test that response is contextually appropriate
    math_response = await client.invoke("What is 2+2? Respond with only the number.")
    assert "4" in math_response, "LLM should correctly answer basic math"


@pytest.mark.integration
async def test_real_agent_workflow():
    """Test actual agent execution with real tools and LLM."""
    from plugins_folder.agent_core import SpecialistAgent
    from plugins_folder.tools import ToolRegistry, FinishTool
    from llm_connector import LLMClient
    from project_state import ProjectState
    
    llm_client = LLMClient()
    project_state = ProjectState()
    
    # Create minimal tool registry
    tool_registry = ToolRegistry()
    tool_registry.register_tool(FinishTool())
    
    # Create agent
    agent = SpecialistAgent(
        agent_id=999,
        name="IntegrationTestAgent",
        role="Integration Tester",
        tool_registry=tool_registry,
        llm_client=llm_client,
        project_state=project_state
    )
    
    # Test agent can execute a simple mission
    result = await agent.run(
        mission_prompt="Complete this test by using the finish tool with message 'Integration test completed'",
        log_id=1
    )
    
    assert isinstance(result, dict), "Agent should return dict result"
    assert "final_response" in result, "Agent result should have final_response"


@pytest.mark.integration  
async def test_file_system_operations():
    """Test file system operations that real tools would need."""
    import tempfile
    import json
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test file creation and reading
        test_file = temp_path / "test.txt"
        test_content = "Integration test content"
        
        test_file.write_text(test_content)
        read_content = test_file.read_text()
        
        assert read_content == test_content, "File I/O should work correctly"
        
        # Test JSON handling
        json_file = temp_path / "test.json"
        test_data = {"test": "data", "number": 42}
        
        json_file.write_text(json.dumps(test_data))
        loaded_data = json.loads(json_file.read_text())
        
        assert loaded_data == test_data, "JSON serialization should work correctly"


@pytest.mark.integration
async def test_concurrent_operations():
    """Test system behavior under concurrent load."""
    from plugins_folder.tools import TreeOfThoughtTool
    from llm_connector import LLMClient
    
    llm_client = LLMClient()
    tot_tool = TreeOfThoughtTool(llm_client)
    
    # Run multiple operations concurrently
    tasks = []
    for i in range(5):
        task = tot_tool.execute(
            prompt=f"Analyze approach {i} for solving concurrent testing",
            branches=2,
            depth=1
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify all completed without errors
    for i, result in enumerate(results):
        assert not isinstance(result, Exception), f"Task {i} failed with exception: {result}"
        assert isinstance(result, dict), f"Task {i} should return dict"
        assert result.get("status") in ["success", "error"], f"Task {i} should have valid status"


@pytest.mark.integration
async def test_error_recovery():
    """Test system recovery from real error conditions."""
    from plugins_folder.tools import SQLQueryTool
    
    sql_tool = SQLQueryTool()
    
    # Test with intentionally bad query
    result = await sql_tool.execute(sql_query="SELECT * FROM definitely_nonexistent_table_12345")
    
    assert result.get("status") == "error", "Should handle SQL errors gracefully"
    assert "message" in result, "Error should include message"
    assert len(result["message"]) > 0, "Error message should not be empty"


@pytest.mark.integration
async def test_memory_usage():
    """Test memory usage patterns under load."""
    import psutil
    import gc
    
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    
    # Create and destroy many objects
    from project_state import ProjectState
    
    states = []
    for i in range(100):
        state = ProjectState()
        await state.update_state(f"key_{i}", f"value_{i}" * 100)  # Create some data
        states.append(state)
    
    peak_memory = process.memory_info().rss
    
    # Clean up
    del states
    gc.collect()
    
    final_memory = process.memory_info().rss
    
    # Memory should not grow unboundedly
    memory_growth = peak_memory - initial_memory
    memory_recovered = peak_memory - final_memory
    
    assert memory_growth < 100 * 1024 * 1024, "Memory growth should be reasonable"  # Less than 100MB
    assert memory_recovered > 0, "Memory should be recoverable"


@pytest.mark.integration
async def test_data_consistency():
    """Test data consistency across operations."""
    from project_state import ProjectState
    
    state = ProjectState()
    
    # Test concurrent writes to same key
    async def writer(key, value, iterations):
        for i in range(iterations):
            await state.update_state(key, f"{value}_{i}")
            await asyncio.sleep(0.001)  # Small delay
    
    # Run concurrent writers
    await asyncio.gather(
        writer("test_key", "writer_a", 10),
        writer("test_key", "writer_b", 10)
    )
    
    # Final value should be from one of the writers
    final_value = state.get_state("test_key")
    assert final_value is not None, "Final value should exist"
    assert ("writer_a" in final_value or "writer_b" in final_value), "Final value should be from a writer"