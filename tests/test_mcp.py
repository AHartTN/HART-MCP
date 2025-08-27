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


@pytest.mark.asyncio
async def test_mcp_llm_error(client: TestClient, mock_llm_client: MockLLMClient, monkeypatch: pytest.MonkeyPatch):
    """
    Tests how the /mcp endpoint handles an unexpected error from the LLM.

    This test ensures the system is resilient and returns a proper HTTP error
    instead of crashing if the agent's 'brain' fails.
    """
    # Arrange: Configure the mock LLM to raise an. exception.
    mock_llm_client.error = Exception("LLM service is down")

    # Mock LLMClient instantiation within run_agent_mission
    monkeypatch.setattr(LLMClient, '__new__', lambda cls, *args, **kwargs: mock_llm_client)

    # Act: Call the MCP endpoint.
    mission_payload = {"query": "Test mission that will fail"}
    response = client.post("/mcp", json=mission_payload)
    response.raise_for_status()
    mission_id = response.json()["mission_id"]

    # Stream the response from the /stream/{mission_id} endpoint
    stream_response = client.get(f"/stream/{mission_id}")
    stream_response.raise_for_status()

    # Assert: Verify that the streaming response contains the error message.
    full_response_text = ""
    for chunk in stream_response.iter_bytes():
        full_response_text += chunk.decode("utf-8")

    assert "LLM service is down" in full_response_text


@pytest.mark.asyncio
async def test_stream_endpoint_isolation(client: TestClient):
    """
    Tests the /stream/{mission_id} endpoint in isolation to check for 405 errors.
    """
    # Arrange: Use a dummy mission_id
    dummy_mission_id = "test-mission-id"

    # Act
    response = client.get(f"/stream/{dummy_mission_id}")

    # Assert
    # We expect a 200 OK even if the mission is not found, as the endpoint itself should be accessible
    assert response.status_code == 200
    full_response_text = ""
    for chunk in response.iter_bytes():
        full_response_text += chunk.decode("utf-8")
    assert "Mission not found" in full_response_text