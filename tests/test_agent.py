# In tests/test_agent.py
import json
from unittest.mock import MagicMock, AsyncMock

import pytest

from plugins_folder.agent_core import SpecialistAgent
from tests.conftest import MockLLMClient


@pytest.mark.asyncio
async def test_specialist_agent_run_simple_mission(mock_llm_client: MockLLMClient):
    """
    Tests the SpecialistAgent's run method with a simple mission,
    simulating a direct path to a final answer.
    """
    agent = SpecialistAgent(
        agent_id=1,
        name="TestAgent",
        role="Tester",
        tool_registry=MagicMock(),
        llm_client=mock_llm_client,
    )
    mission_prompt = "Tell me a joke."
    expected_final_answer = (
        "Why don't scientists trust atoms? Because they make up everything!"
    )

    # Arrange
    mock_llm_client.response = json.dumps(
        {
            "thought": "I will tell a joke.",
            "action": {"tool": "FinishTool", "query": expected_final_answer},
        }
    )

    # Act
    result = await agent.run(mission_prompt, log_id=1)

    # Assert
    assert result["final_response"] == expected_final_answer


@pytest.mark.asyncio
async def test_specialist_agent_load_from_db(monkeypatch, mock_llm_client: MockLLMClient):
    """
    Tests the SpecialistAgent's load_from_db method for both existing and non-existent agents.
    """
    # Arrange
    mock_cursor = MagicMock()
    mock_cursor.fetchone.side_effect = [
        (1, "LoadedAgent", "LoadedRole"),
        None,
    ]
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__aenter__.return_value = mock_conn
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    monkeypatch.setattr(
        "db_connectors.get_sql_server_connection", lambda: mock_conn
    )

    # Act & Assert for existing agent
    agent = await SpecialistAgent.load_from_db(1, MagicMock(), mock_llm_client)
    assert agent is not None
    assert agent.agent_id == 1
    assert agent.name == "Analyst_Alpha"
    assert agent.role == "Analyst"

    # Act & Assert for non-existent agent
    agent = await SpecialistAgent.load_from_db(999, MagicMock(), mock_llm_client)
    assert agent is None