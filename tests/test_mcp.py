# In tests/test_mcp.py
import pytest
from fastapi.testclient import TestClient

from tests.conftest import MockLLMClient


def test_mcp_golden_path(client: TestClient, mock_llm_client: MockLLMClient):
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

    # Act: Call the MCP endpoint with a mission.
    mission_payload = {"prompt": "Test mission"}
    response = client.post("/mcp", json=mission_payload)

    # Assert: Verify that the streaming response contains the final answer.
    # This proves the entire agentic loop worked as expected.
    response.raise_for_status()  # Ensure the request was successful (200 OK)
    assert final_answer in response.text


def test_mcp_llm_error(client: TestClient, mock_llm_client: MockLLMClient):
    """
    Tests how the /mcp endpoint handles an unexpected error from the LLM.

    This test ensures the system is resilient and returns a proper HTTP error
    instead of crashing if the agent's 'brain' fails.
    """
    # Arrange: Configure the mock LLM to raise an exception.
    mock_llm_client.error = Exception("LLM service is down")

    # Act: Call the MCP endpoint.
    mission_payload = {"prompt": "Test mission that will fail"}
    response = client.post("/mcp", json=mission_payload)

    # Assert: Verify that the server returned an internal server error status code.
    assert response.status_code == 500
    assert "LLM service is down" in response.text
