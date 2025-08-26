import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add plugins_folder to sys.path for importlib to find it
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from llm_connector import LLMClient
from plugins import call_plugin, list_plugins, load_plugins, register_plugin
from plugins_folder.agent_core import SpecialistAgent, create_specialist_agent
from plugins_folder.orchestrator_core import (
    OrchestratorAgent,
    create_orchestrator_agent,
)
from plugins_folder.tools import (
    DelegateToSpecialistTool,
    FinishTool,
    RAGTool,
    ToolRegistry,
    TreeOfThoughtTool,
)


@pytest.fixture
def mock_llm_client():
    return AsyncMock(spec=LLMClient)


@pytest.fixture
def mock_tool_registry():
    registry = MagicMock(spec=ToolRegistry)
    registry.get_tool_names.return_value = [
        "RAG Tool",
        "Tree of Thought Tool",
        "FinishTool",
        "DelegateToSpecialistTool",
    ]

    mock_rag_tool = AsyncMock(spec=RAGTool)
    mock_rag_tool.name = "RAG Tool"
    mock_rag_tool.execute.return_value = {"response": "mocked RAG result"}
    registry.register_tool(mock_rag_tool)

    mock_tot_tool = AsyncMock(spec=TreeOfThoughtTool)
    mock_tot_tool.name = "Tree of Thought Tool"
    mock_tot_tool.execute.return_value = {"response": "mocked ToT result"}
    registry.register_tool(mock_tot_tool)

    mock_finish_tool = AsyncMock(spec=FinishTool)
    mock_finish_tool.name = "FinishTool"
    mock_finish_tool.execute.return_value = "mocked final answer"
    registry.register_tool(mock_finish_tool)

    # Mock use_tool to return specific results for known tools
    registry.use_tool.side_effect = lambda name, query: {
        "RAG Tool": mock_rag_tool.execute(query),
        "Tree of Thought Tool": mock_tot_tool.execute(query),
        "FinishTool": mock_finish_tool.execute(query),
        "DelegateToSpecialistTool": AsyncMock(
            return_value={"delegated_result": "mocked delegation"}
        ).execute(
            query
        ),  # Mock for delegate tool
    }[name]
    return registry


@pytest.fixture
def mock_specialist_agent_instance():
    mock_agent = AsyncMock(spec=SpecialistAgent)
    mock_agent.run.return_value = {"final_response": "Specialist completed sub-task."}
    mock_agent.update_callback = AsyncMock()
    return mock_agent


@pytest.fixture
def mock_orchestrator_agent_instance():
    mock_agent = AsyncMock(spec=OrchestratorAgent)
    mock_agent.run.return_value = {"final_response": "Orchestrator completed mission."}
    mock_agent.update_callback = AsyncMock()
    return mock_agent


# --- Tests for ToolRegistry ---
@pytest.mark.asyncio
async def test_tool_registry_register_and_use(mock_tool_registry):
    # The fixture already registers tools and mocks use_tool
    result = await mock_tool_registry.use_tool("RAG Tool", "test query")
    assert result == {"response": "mocked RAG result"}
    mock_tool_registry.get_tool_names.assert_called_once()


@pytest.mark.asyncio
async def test_tool_registry_tool_not_found(mock_tool_registry):
    with pytest.raises(ValueError, match="Tool 'NonExistentTool' not found."):
        await mock_tool_registry.use_tool("NonExistentTool", "query")


# --- Tests for DelegateToSpecialistTool ---
@pytest.mark.asyncio
async def test_delegate_to_specialist_tool_execute(mock_specialist_agent_instance):
    delegate_tool = DelegateToSpecialistTool(
        specialist_agent=mock_specialist_agent_instance
    )
    mission_prompt = "Perform a specific sub-task."

    result = await delegate_tool.execute(mission_prompt)

    mock_specialist_agent_instance.run.assert_awaited_once_with(
        mission_prompt,
        log_id=1,  # Default log_id from the tool's implementation
        update_callback=mock_specialist_agent_instance.update_callback,
    )
    assert result == {"final_response": "Specialist completed sub-task."}


# --- Tests for plugin system with new agents ---
@pytest.mark.asyncio
async def test_create_specialist_agent_plugin(mock_llm_client):
    # Mock sql_connection_context for load_from_db inside create_specialist_agent
    with patch("utils.sql_connection_context", AsyncMock()):
        agent = await create_specialist_agent(
            1, "TestSpecialist", "Specialist", ToolRegistry(), mock_llm_client
        )
        assert isinstance(agent, SpecialistAgent)
        assert agent.name == "TestSpecialist"


@pytest.mark.asyncio
async def test_create_orchestrator_agent_plugin(mock_llm_client):
    # Mock sql_connection_context for load_from_db inside create_orchestrator_agent
    with patch("utils.sql_connection_context", AsyncMock()):
        agent = await create_orchestrator_agent(
            2, "TestOrchestrator", "Orchestrator", ToolRegistry(), mock_llm_client
        )
        assert isinstance(agent, OrchestratorAgent)
        assert agent.name == "TestOrchestrator"


@pytest.mark.asyncio
async def test_orchestrator_tool_registry_composition(
    mock_llm_client, mock_specialist_agent_instance
):
    # Create a ToolRegistry for the Orchestrator
    orchestrator_tool_registry = ToolRegistry()
    orchestrator_tool_registry.register_tool(
        DelegateToSpecialistTool(specialist_agent=mock_specialist_agent_instance)
    )
    orchestrator_tool_registry.register_tool(FinishTool())

    # Create an OrchestratorAgent with this specific tool registry
    orchestrator_agent = OrchestratorAgent(
        agent_id=1,
        name="TestOrchestrator",
        role="Orchestrator",
        tool_registry=orchestrator_tool_registry,
        llm_client=mock_llm_client,
    )

    # Assert that the orchestrator's tool registry contains only the expected tools
    expected_tools = {"DelegateToSpecialistTool", "FinishTool"}
    actual_tools = set(orchestrator_agent.tool_registry.get_tool_names())
    assert actual_tools == expected_tools


# Test the overall plugin loading (if needed, but fixtures handle this)
# def test_load_plugins_new_structure():
#     load_plugins()
#     registered_plugins = list_plugins()
#     assert "create_specialist_agent" in registered_plugins
#     assert "create_orchestrator_agent" in registered_plugins
