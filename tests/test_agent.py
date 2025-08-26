import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from llm_connector import LLMClient
from plugins_folder.agent_core import SpecialistAgent
from plugins_folder.tools import (FinishTool, RAGTool, ToolRegistry,
                                  TreeOfThoughtTool)
from utils import sql_connection_context


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

    registry.use_tool.side_effect = lambda name, query: {
        "RAG Tool": mock_rag_tool.execute(query),
        "Tree of Thought Tool": mock_tot_tool.execute(query),
        "FinishTool": mock_finish_tool.execute(query),
    }[name]
    return registry


@pytest.fixture
def mock_sql_connection_context():
    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()

    # Mock the context manager itself
    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = (mock_conn, mock_cursor)
    mock_context_manager.__aexit__.return_value = None

    with patch("utils.sql_connection_context", return_value=mock_context_manager):
        yield mock_cursor


@pytest.mark.asyncio
async def test_specialist_agent_run_finish_tool(
    mock_llm_client, mock_tool_registry, mock_sql_connection_context
):
    agent = SpecialistAgent(
        agent_id=1,
        name="TestAgent",
        role="Tester",
        tool_registry=mock_tool_registry,
        llm_client=mock_llm_client,
    )
    log_id = 101
    mission_prompt = "Complete this mission immediately."

    mock_llm_client.invoke.return_value = json.dumps(
        {
            "thought": "I should use the FinishTool.",
            "action": {"tool": "FinishTool", "query": "Mission accomplished!"},
        }
    )

    result = await agent.run(mission_prompt, log_id)

    assert result["final_response"] == "Mission accomplished!"
    mock_llm_client.invoke.assert_called_once()
    mock_sql_connection_context.execute.assert_called()


@pytest.mark.asyncio
async def test_specialist_agent_run_with_tool_usage(
    mock_llm_client, mock_tool_registry, mock_sql_connection_context
):
    agent = SpecialistAgent(
        agent_id=2,
        name="ToolUser",
        role="Executor",
        tool_registry=mock_tool_registry,
        llm_client=mock_llm_client,
    )
    log_id = 102
    mission_prompt = "Use the RAG tool to get information."

    # First LLM call: use RAG Tool
    mock_llm_client.invoke.side_effect = [
        json.dumps(
            {
                "thought": "I need to use the RAG Tool.",
                "action": {"tool": "RAG Tool", "query": "information about X"},
            }
        ),
        # Second LLM call: finish after RAG Tool result
        json.dumps(
            {
                "thought": "RAG Tool provided information, now I can finish.",
                "action": {"tool": "FinishTool", "query": "RAG info retrieved."},
            }
        ),
    ]

    result = await agent.run(mission_prompt, log_id)

    assert result["final_response"] == "RAG info retrieved."
    assert mock_llm_client.invoke.call_count == 2
    mock_tool_registry.use_tool.assert_called_once_with(
        "RAG Tool", "information about X"
    )
    mock_sql_connection_context.execute.assert_called()


@pytest.mark.asyncio
async def test_specialist_agent_run_malformed_llm_response(
    mock_llm_client, mock_tool_registry, mock_sql_connection_context
):
    agent = SpecialistAgent(
        agent_id=3,
        name="BadLLM",
        role="Troubleshooter",
        tool_registry=mock_tool_registry,
        llm_client=mock_llm_client,
    )
    log_id = 103
    mission_prompt = "Cause an LLM error."

    mock_llm_client.invoke.return_value = "This is not JSON."

    result = await agent.run(mission_prompt, log_id)

    assert "No final answer" in result["final_response"]
    assert "Error decoding JSON" in agent.scratchpad[-1]
    mock_llm_client.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_specialist_agent_run_update_callback(
    mock_llm_client, mock_tool_registry, mock_sql_connection_context
):
    mock_update_callback = AsyncMock()
    agent = SpecialistAgent(
        agent_id=4,
        name="Streamer",
        role="Reporter",
        tool_registry=mock_tool_registry,
        llm_client=mock_llm_client,
        update_callback=mock_update_callback,
    )
    log_id = 104
    mission_prompt = "Observe my updates."

    mock_llm_client.invoke.return_value = json.dumps(
        {
            "thought": "I will finish now.",
            "action": {"tool": "FinishTool", "query": "Updates observed."},
        }
    )

    await agent.run(mission_prompt, log_id)

    # Check if update_callback was called at various stages
    assert (
        mock_update_callback.call_count >= 3
    )  # mission_start, thought_process, thought, final_answer
    mock_update_callback.assert_any_call(
        {"type": "mission_start", "content": mission_prompt}
    )
    mock_update_callback.assert_any_call(
        {"type": "thought", "content": "I will finish now."}
    )
    mock_update_callback.assert_any_call(
        {"type": "final_answer", "content": "Updates observed."}
    )


@pytest.mark.asyncio
async def test_specialist_agent_load_from_db_existing_agent(
    mock_llm_client, mock_tool_registry, mock_sql_connection_context
):
    # Mock the fetchone result for an existing agent
    mock_sql_connection_context.fetchone.return_value = (
        1,
        "LoadedAgent",
        "LoadedRole",
        json.dumps({"beliefs": {"key": "value"}}),
    )

    agent = await SpecialistAgent.load_from_db(1, mock_tool_registry, mock_llm_client)

    assert agent is not None
    assert agent.agent_id == 1
    assert agent.name == "LoadedAgent"
    assert agent.role == "LoadedRole"
    assert agent.bdi_state["beliefs"] == {"key": "value"}
    mock_sql_connection_context.execute.assert_called_once_with(
        "SELECT AgentID, Name, Role, BDIState FROM Agents WHERE AgentID = ?", 1
    )


@pytest.mark.asyncio
async def test_specialist_agent_load_from_db_non_existent_agent(
    mock_llm_client, mock_tool_registry, mock_sql_connection_context
):
    # Mock the fetchone result for a non-existent agent
    mock_sql_connection_context.fetchone.return_value = None

    agent = await SpecialistAgent.load_from_db(999, mock_tool_registry, mock_llm_client)

    assert agent is None
    mock_sql_connection_context.execute.assert_called_once_with(
        "SELECT AgentID, Name, Role, BDIState FROM Agents WHERE AgentID = ?", 999
    )


@pytest.mark.asyncio
async def test_specialist_agent_update_bdi_state(mock_sql_connection_context):
    agent = SpecialistAgent(
        agent_id=5,
        name="BDIUpdater",
        role="Updater",
        tool_registry=MagicMock(),
        llm_client=MagicMock(),
    )
    log_id = 105
    new_beliefs = {"new_fact": "fact_value"}
    new_desires = ["new_desire"]
    new_intentions = ["new_intention"]

    await agent.update_bdi_state(log_id, new_beliefs, new_desires, new_intentions)

    assert agent.bdi_state["beliefs"]["new_fact"] == "fact_value"
    assert "new_desire" in agent.bdi_state["desires"]
    assert "new_intention" in agent.bdi_state["intentions"]

    mock_sql_connection_context.execute.assert_called_once()
    # Verify the update query and parameters
    call_args = mock_sql_connection_context.execute.call_args[0]
    assert "UPDATE AgentLogs SET BDIState = ? WHERE LogID = ?" in call_args[0]
    assert json.loads(call_args[1])["beliefs"]["new_fact"] == "fact_value"
    assert call_args[2] == log_id
