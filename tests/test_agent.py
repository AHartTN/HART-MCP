import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from plugins_folder.agent_core import SpecialistAgent
from llm_connector import LLMClient # Import for type hinting mock_llm_client


@pytest.mark.asyncio
async def test_specialist_agent_run_simple_mission(mock_llm_client: MagicMock):
    """
    Tests the SpecialistAgent's run method with a simple mission,
    simulating a direct path to a final answer.
    """
    agent = SpecialistAgent(
        agent_id=1,
        name="TestAgent",
        role="Tester",
        tool_registry=MagicMock(), # Tool registry is mocked as it's not the focus here
        llm_client=mock_llm_client,
    )
    mission_prompt = "Tell me a joke."
    expected_final_answer = "Why don't scientists trust atoms? Because they make up everything!"

    mock_llm_client.invoke.side_effect = [
        json.dumps({
            "thought": "I will tell a joke.",
            "action": {"tool": "FinishTool", "query": expected_final_answer}
        }),
        # Second response for the summary call at the end of agent.run
        "Mocked mission summary."
    ]

    result = await agent.run(mission_prompt, log_id=1) # log_id is arbitrary for this test

    assert result["final_response"] == expected_final_answer
    assert mock_llm_client.invoke.call_count == 2 # Now expects two calls


@pytest.mark.asyncio
async def test_specialist_agent_load_from_db(mock_db_connection: MagicMock, mock_llm_client: MagicMock):
    """
    Tests the SpecialistAgent's load_from_db method for both existing and non-existent agents.
    """
    # Simulate an existing agent in the database
    mock_db_connection.cursor.return_value.__aenter__.return_value.fetchone.side_effect = [
        (1, "LoadedAgent", "LoadedRole"), # For existing agent
        None # For non-existent agent
    ]

    # Test loading an existing agent
    agent = await SpecialistAgent.load_from_db(1, MagicMock(), mock_llm_client)
    assert agent is not None
    assert agent.agent_id == 1
    assert agent.name == "LoadedAgent"
    assert agent.role == "LoadedRole"

    # Test loading a non-existent agent
    agent = await SpecialistAgent.load_from_db(999, MagicMock(), mock_llm_client)
    assert agent is None

    # Verify that execute was called twice (once for each load attempt)
    assert mock_db_connection.cursor.return_value.__aenter__.return_value.execute.call_count == 2
