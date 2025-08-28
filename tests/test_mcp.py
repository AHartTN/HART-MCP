# In tests/test_mcp.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock # Added this line

from llm_connector import LLMClient
from tests.conftest import MockLLMClient


@pytest.mark.asyncio
async def test_mcp_golden_path(
    client: TestClient, mock_llm_client: MockLLMClient, monkeypatch: pytest.MonkeyPatch
):
    """
    Tests the end-to-end 'golden path' of the /mcp endpoint.

    This test verifies that when the agent decides to finish its mission,
    the final answer is correctly streamed back to the client.
    """
    # Arrange: Configure the mock LLM to return a predictable final answer.
    # This simulates the agent thinking and deciding to finish the mission.
    final_answer = "The mission was a success."
    mock_llm_client.response = f'{{"thought": "I have the final answer.", "action": {{"tool_name": "finish", "parameters": {{"response": "{final_answer}"}}}}}}'
    

    # Act: Call the MCP endpoint with a mission.
    mission_payload = {"query": "Test mission", "agent_id": 1}
    response = client.post("/mcp", json=mission_payload)

    # Debug: Print response details if there's an error
    if response.status_code != 200:
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Response content: {response.text}")

    response.raise_for_status()
    mission_id = response.json()["mission_id"]

    # Stream the response from the /stream/{mission_id} endpoint
    stream_response = client.get(f"/stream/{mission_id}")
    stream_response.raise_for_status()

    # Assert: Verify that the streaming response contains the final answer.
    # This proves the entire agentic loop worked as expected.
    full_response_text = ""
    for chunk in stream_response.iter_bytes():
        full_response_text += chunk.decode("utf-8")

    assert final_answer in full_response_text
