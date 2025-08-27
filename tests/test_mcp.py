# In tests/test_mcp.py
import pytest
from fastapi.testclient import TestClient

from tests.conftest import MockLLMClient
from llm_connector import LLMClient


@pytest.mark.asyncio
async def test_mcp_golden_path(client: TestClient, mock_llm_client: MockLLMClient, monkeypatch: pytest.MonkeyPatch):
    """
    Tests the end-to-end 'golden path' of the /mcp endpoint.

    This test verifies that when the agent decides to finish its mission,
    the final answer is correctly streamed back to the client.
    """
    # Arrange: Configure the mock LLM to return a predictable final answer.
    # This simulates the agent thinking and deciding to finish the mission.
    final_answer = "The mission was a success."
    mock_llm_client.response = (
        '''{"thought": "I have the final answer.", "action": {"tool": "FinishTool", "query": "'''
        + final_answer
        + """"}}"""
    )

    # Mock LLMClient instantiation within run_agent_mission
    monkeypatch.setattr(LLMClient, '__new__', lambda cls, *args, **kwargs: mock_llm_client)

    # Act: Call the MCP endpoint with a mission.
    mission_payload = {"query": "Test mission", "agent_id": 1}
    response = client.post("/mcp", json=mission_payload)
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

