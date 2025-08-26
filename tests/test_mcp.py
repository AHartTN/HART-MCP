import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# No need to import TestClient or app directly, as they are handled by the client fixture from conftest.py
from plugins_folder.agent_core import SpecialistAgent
from plugins_folder.orchestrator_core import OrchestratorAgent


@pytest.mark.asyncio
async def test_mcp_mission_completion(client, mock_llm_client):
    """
    Tests the end-to-end mission completion flow through the /mcp endpoint.
    Focuses on inputs and outputs, not internal mock calls.
    """
    mission_query = "Please tell me a short story about a brave knight."
    expected_final_answer = "The brave knight, Sir Reginald, vanquished the dragon and saved the kingdom."

    # Configure mock_llm_client to return a sequence of responses
    # First, simulate the LLM deciding to use a tool (e.g., a story-telling tool, or just a placeholder for internal processing)
    # Then, simulate the LLM providing the final answer using the FinishTool
    mock_llm_client.invoke.side_effect = [
        json.dumps({
            "thought": "I will now generate a story about a brave knight.",
            "action": {"tool": "GenerateStoryTool", "query": "brave knight story"} # Placeholder tool
        }),
        json.dumps({
            "thought": "I have generated the story and will now finish.",
            "action": {"tool": "FinishTool", "query": expected_final_answer}
        })
    ]

    # Mock SpecialistAgent and OrchestratorAgent load_from_db
    with patch.object(SpecialistAgent, 'load_from_db', new_callable=AsyncMock) as mock_specialist_load_from_db, \
         patch.object(OrchestratorAgent, 'load_from_db', new_callable=AsyncMock) as mock_orchestrator_load_from_db:

        # Configure mock SpecialistAgent and OrchestratorAgent instances
        mock_specialist_agent_instance = MagicMock(spec=SpecialistAgent)
        mock_specialist_agent_instance.run = AsyncMock(return_value={"final_response": "Specialist completed sub-task."})) # Corrected: Added closing parenthesis
        mock_specialist_agent_instance.update_callback = AsyncMock() # Add update_callback

        mock_orchestrator_agent_instance = MagicMock(spec=OrchestratorAgent)
        mock_orchestrator_agent_instance.run = AsyncMock(return_value={"final_response": expected_final_answer})
        mock_orchestrator_agent_instance.update_callback = AsyncMock() # Add update_callback

        mock_specialist_load_from_db.return_value = mock_specialist_agent_instance
        mock_orchestrator_load_from_db.return_value = mock_orchestrator_agent_instance

        # 1. Make POST request to /mcp to start the mission and get mission_id
        post_response = client.post("/mcp", json={"query": mission_query, "agent_id": 1})
        assert post_response.status_code == 200
        post_data = post_response.json()
        mission_id = post_data.get("mission_id")
        assert mission_id is not None

        # 2. Make GET request to /stream/{mission_id} to receive streaming events
        stream_response = client.get(f"/stream/{mission_id}")
        assert stream_response.status_code == 200
        assert stream_response.headers["content-type"] == "text/event-stream; charset=utf-8" # Corrected assertion

        received_events = []
        async for chunk in stream_response.aiter_bytes():
            decoded_chunk = chunk.decode("utf-8")
            for line in decoded_chunk.split("data:"):
                line = line.strip()
                if line:
                    try:
                        event_data = json.loads(line)
                        received_events.append(event_data)
                    except json.JSONDecodeError:
                        pass # Ignore malformed lines or non-JSON data

        # Assert that the final response contains the expected answer
        final_event = next((e for e in received_events if e.get("type") == "orchestrator_final_answer"), None)
        assert final_event is not None
        assert final_event["content"] == expected_final_answer
        assert final_event["status"] == "completed"

        # Verify that the LLM was invoked the expected number of times
        assert mock_llm_client.invoke.call_count == 2
