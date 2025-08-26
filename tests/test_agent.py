import json
import pytest
from unittest.mock import MagicMock
from plugins_folder.agent_core import SpecialistAgent


@pytest.fixture
def db_context_and_patch(monkeypatch):
    global_cursor = MagicMock()
    global_conn = MagicMock()

    class DummyContextManager:
        async def __aenter__(self):
            return (global_conn, global_cursor)

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr("utils.sql_connection_context", lambda: DummyContextManager())
    monkeypatch.setattr(
        "plugins_folder.agent_core.sql_connection_context",
        lambda: DummyContextManager(),
    )
    return global_cursor, global_conn


@pytest.fixture
def mock_llm_client():
    return MagicMock()


@pytest.fixture
def mock_tool_registry():
    return MagicMock()


@pytest.mark.asyncio
async def test_specialist_agent_run_finish_tool(
    mock_llm_client, mock_tool_registry, db_context_and_patch
):
    global_cursor, _ = db_context_and_patch
    agent = SpecialistAgent(
        agent_id=1,
        name="TestAgent",
        role="Tester",
        tool_registry=mock_tool_registry,
        llm_client=mock_llm_client,
    )
    log_id = 101
    mission_prompt = "Complete this mission immediately."
    async def async_invoke_side_effect(*args, **kwargs):
        responses = [
            json.dumps(
                {
                    "thought": "I should use the FinishTool.",
                    "action": {"tool": "FinishTool", "query": "Mission accomplished!"},
                }
            ),
            json.dumps({"summary": "Mocked scratchpad summary."}),
        ]
        if not hasattr(async_invoke_side_effect, "call_count"):
            async_invoke_side_effect.call_count = 0
        response = responses[async_invoke_side_effect.call_count]
        async_invoke_side_effect.call_count += 1
        return response

    mock_llm_client.invoke.side_effect = async_invoke_side_effect
    result = await agent.run(mission_prompt, log_id)
    assert result["final_response"] == "Mission accomplished!"
    assert mock_llm_client.invoke.call_count == 2
    assert global_cursor.execute.call_count > 0

    from unittest.mock import AsyncMock
    mock_update_callback = AsyncMock()
    agent.update_callback = mock_update_callback

    mission_prompt = "Get updates from the field."
    # Use an async side effect for all calls
    async def async_invoke_side_effect_2(*args, **kwargs):
        responses = [
            json.dumps(
                {
                    "thought": "I need to use the RAG Tool.",
                    "action": {"tool": "RAG Tool", "query": "information about X"},
                }
            ),
            json.dumps(
                {
                    "thought": "RAG Tool provided information, now I can finish.",
                    "action": {"tool": "FinishTool", "query": "RAG info retrieved."},
                }
            ),
            "Mocked mission summary.",
        ]
        if not hasattr(async_invoke_side_effect_2, "call_count"):
            async_invoke_side_effect_2.call_count = 0
        response = responses[async_invoke_side_effect_2.call_count]
        async_invoke_side_effect_2.call_count += 1
        return response

    mock_llm_client.invoke.side_effect = async_invoke_side_effect_2
    result = await agent.run(mission_prompt, log_id)
    assert result["final_response"] == "RAG info retrieved."
    assert mock_llm_client.invoke.call_count == 3
    mock_tool_registry.use_tool.assert_called_once_with(
        "RAG Tool", "information about X"
    )
    assert global_cursor.execute.call_count > 0

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
    mock_llm_client, mock_tool_registry, db_context_and_patch
):
    global_cursor, _ = db_context_and_patch
    # Mock the fetchone result for an existing agent
    global_cursor.fetchone.return_value = (
        1,
        "LoadedAgent",
        "LoadedRole",
    )

    agent = await SpecialistAgent.load_from_db(1, mock_tool_registry, mock_llm_client)

    assert agent is not None
    assert agent.agent_id == 1
    assert agent.name == "LoadedAgent"
    assert agent.role == "LoadedRole"
    global_cursor.execute.assert_called_once_with(
        "SELECT AgentID, Name, Role, BDIState FROM Agents WHERE AgentID = ?", 1
    )


@pytest.mark.asyncio
async def test_specialist_agent_load_from_db_non_existent_agent(
    mock_llm_client, mock_tool_registry, db_context_and_patch
):
    global_cursor, _ = db_context_and_patch
    # Mock the fetchone result for a non-existent agent
    global_cursor.fetchone.return_value = None

    agent = await SpecialistAgent.load_from_db(999, mock_tool_registry, mock_llm_client)

    assert agent is None
    global_cursor.execute.assert_called_once_with(
        "SELECT AgentID, Name, Role, BDIState FROM Agents WHERE AgentID = ?", 999
    )


@pytest.mark.asyncio
async def test_specialist_agent_update_bdi_state(db_context_and_patch):
    global_cursor, _ = db_context_and_patch
    agent = SpecialistAgent(
        agent_id=5,
        name="BDIUpdater",
        role="Updater",
        tool_registry=MagicMock(),
        llm_client=MagicMock(),
    )
    log_id = 555
    new_beliefs = {"new_fact": "fact_value"}
    new_desires = ["desire1"]
    new_intentions = ["intention1"]
    await agent.update_bdi_state(log_id, new_beliefs, new_desires, new_intentions)
    global_cursor.execute.assert_called()

    assert agent.bdi_state["beliefs"]["new_fact"] == "fact_value"
    assert "desire1" in agent.bdi_state["desires"]
    assert "intention1" in agent.bdi_state["intentions"]
