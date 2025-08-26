import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from llm_connector import LLMClient
from plugins_folder.agent_core import SpecialistAgent
from plugins_folder.orchestrator_core import (
    OrchestratorAgent,
)
from server import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_llm_client():
    return AsyncMock(spec=LLMClient)


@pytest.fixture
def mock_sql_connection_context():
    mock_cursor = AsyncMock()
    mock_conn = AsyncMock()
    mock_conn.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_conn.commit = AsyncMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchone.return_value = None  # Default to no agent found
    mock_cursor.lastrowid = 1  # Default log_id

    mock_context_manager = AsyncMock()
    mock_context_manager.__aenter__.return_value = (mock_conn, mock_cursor)
    mock_context_manager.__aexit__.return_value = None

    with patch("utils.sql_connection_context", return_value=mock_context_manager):
        yield mock_cursor


@pytest.fixture
def mock_specialist_agent_instance(mock_llm_client):
    # This mock will be passed to DelegateToSpecialistTool
    mock_agent = AsyncMock(spec=SpecialistAgent)
    mock_agent.run.return_value = {"final_response": "Specialist completed sub-task."}
    mock_agent.update_callback = (
        AsyncMock()
    )  # Mock the update_callback for the specialist
    return mock_agent


@pytest.mark.asyncio
async def test_mcp_streaming_orchestrator_delegation_success(
    client, mock_llm_client, mock_sql_connection_context, mock_specialist_agent_instance
):
    mission_query = "Orchestrate a simple task."
    agent_id = 1

    # Mock LLM responses for Orchestrator and Specialist
    # Orchestrator's first thought: delegate to specialist
    orchestrator_llm_response_1 = json.dumps(
        {
            "thought": "I need to delegate this task to a specialist.",
            "action": {
                "tool": "DelegateToSpecialistTool",
                "query": "Perform sub-task X",
            },
        }
    )
    # Orchestrator's second thought: finish after delegation
    orchestrator_llm_response_2 = json.dumps(
        {
            "thought": "Specialist has completed the sub-task, I can now finish.",
            "action": {"tool": "FinishTool", "query": "Orchestration complete."},
        }
    )

    # Specialist's LLM response (if it were to make its own LLM calls, mocked via mock_specialist_agent_instance.run)
    # Here, we directly control mock_specialist_agent_instance.run's return value

    mock_llm_client.invoke.side_effect = [
        orchestrator_llm_response_1,  # Orchestrator's first turn
        orchestrator_llm_response_2,  # Orchestrator's second turn
    ]

    # Mock agent creation/loading
    with (
        patch(
            "plugins_folder.agent_core.create_agent",
            AsyncMock(return_value=mock_specialist_agent_instance),
        ),
        patch(
            "plugins_folder.orchestrator_core.OrchestratorAgent.load_from_db",
            AsyncMock(return_value=None),
        ),
        patch(
            "plugins.call_plugin",
            AsyncMock(
                side_effect=[
                    AsyncMock(spec=OrchestratorAgent),  # For create_orchestrator_agent
                ]
            ),
        ) as _,
    ):
        response = client.post(
            "/mcp", json={"query": mission_query, "agent_id": agent_id}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        received_events = []
        async for chunk in response.aiter_bytes():
            decoded_chunk = chunk.decode("utf-8")
            for line in decoded_chunk.split("\n\n"):
                if line.startswith("data:"):  # Ensure it's an SSE data line
                    try:
                        event_data = json.loads(line[len("data:") :])
                        received_events.append(event_data)
                    except json.JSONDecodeError:
                        pass  # Ignore malformed lines

        # Assertions on streamed events
        assert any(e["type"] == "orchestrator_mission_start" for e in received_events)
        assert any(
            e["type"] == "orchestrator_thought" and "delegate" in e["content"].lower()
            for e in received_events
        )
        assert any(
            e["type"] == "orchestrator_action"
            and e["content"]["tool"] == "DelegateToSpecialistTool"
            for e in received_events
        )
        assert any(
            e["type"] == "orchestrator_observation"
            and "Specialist completed sub-task." in e["content"]
            for e in received_events
        )
        assert any(e["type"] == "orchestrator_final_answer" for e in received_events)
        assert any(e["status"] == "completed" for e in received_events)

        # Verify specialist agent's run method was called by the delegate tool
        mock_specialist_agent_instance.run.assert_awaited_once_with(
            "Perform sub-task X",
            log_id=1,  # Default log_id from mock_sql_connection_context
            update_callback=mock_specialist_agent_instance.update_callback,  # Callback passed down
        )

        # Verify LLM calls
        assert mock_llm_client.invoke.call_count == 2

        # Verify database logging
        mock_sql_connection_context.execute.assert_called()


@pytest.mark.asyncio
async def test_mcp_streaming_error_handling(
    client, mock_llm_client, mock_sql_connection_context, mock_specialist_agent_instance
):
    mission_query = "Trigger an error."
    agent_id = 2

    # Simulate Orchestrator LLM returning malformed JSON
    mock_llm_client.invoke.return_value = "This is not valid JSON."

    with (
        patch(
            "plugins_folder.agent_core.create_agent",
            AsyncMock(return_value=mock_specialist_agent_instance),
        ),
        patch(
            "plugins_folder.orchestrator_core.OrchestratorAgent.load_from_db",
            AsyncMock(return_value=None),
        ),
        patch(
            "plugins.call_plugin",
            AsyncMock(
                side_effect=[
                    AsyncMock(spec=OrchestratorAgent),  # For create_orchestrator_agent
                ]
            ),
        ),
    ):
        response = client.post(
            "/mcp", json={"query": mission_query, "agent_id": agent_id}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        received_events = []
        async for chunk in response.aiter_bytes():
            decoded_chunk = chunk.decode("utf-8")
            for line in decoded_chunk.split("\n\n"):
                if line.startswith("data:"):  # Ensure it's an SSE data line
                    try:
                        event_data = json.loads(line[len("data:") :])
                        received_events.append(event_data)
                    except json.JSONDecodeError:
                        pass  # Ignore malformed lines

        # Assert that an error event was received
        assert any(
            e["type"] == "orchestrator_error" and "Error decoding JSON" in e["content"]
            for e in received_events
        )
        assert any(
            e["error"] for e in received_events
        )  # Check for top-level error from MCP

        mock_llm_client.invoke.assert_called_once()
        mock_sql_connection_context.execute.assert_called()


@pytest.mark.asyncio
async def test_mcp_streaming_orchestrator_load_from_db(
    client, mock_llm_client, mock_sql_connection_context, mock_specialist_agent_instance
):
    mission_query = "Continue an existing mission."
    agent_id = 1

    # Mock an existing OrchestratorAgent instance
    mock_existing_orchestrator = AsyncMock(spec=OrchestratorAgent)
    mock_existing_orchestrator.agent_id = agent_id
    mock_existing_orchestrator.name = "ExistingOrchestrator"
    mock_existing_orchestrator.role = "Orchestrator"
    mock_existing_orchestrator.run.return_value = {
        "final_response": "Existing orchestration completed."
    }
    mock_existing_orchestrator.update_callback = AsyncMock()

    # Mock LLM responses for Orchestrator
    orchestrator_llm_response = json.dumps(
        {
            "thought": "I am an existing orchestrator and will finish.",
            "action": {
                "tool": "FinishTool",
                "query": "Existing orchestration completed.",
            },
        }
    )
    mock_llm_client.invoke.return_value = orchestrator_llm_response

    # Mock agent creation/loading to return the existing orchestrator
    with (
        patch(
            "plugins_folder.agent_core.create_agent",
            AsyncMock(return_value=mock_specialist_agent_instance),
        ),
        patch(
            "plugins_folder.orchestrator_core.OrchestratorAgent.load_from_db",
            AsyncMock(return_value=mock_existing_orchestrator),
        ),
        patch(
            "plugins.call_plugin",
            AsyncMock(
                side_effect=[
                    mock_existing_orchestrator,  # For create_orchestrator_agent (if called)
                ]
            ),
        ) as _,
    ):
        response = client.post(
            "/mcp", json={"query": mission_query, "agent_id": agent_id}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream"

        received_events = []
        async for chunk in response.aiter_bytes():
            decoded_chunk = chunk.decode("utf-8")
            for line in decoded_chunk.split("\n\n"):
                if line.startswith("data:"):
                    try:
                        event_data = json.loads(line[len("data:") :])
                        received_events.append(event_data)
                    except json.JSONDecodeError:
                        pass

        assert any(e["type"] == "orchestrator_mission_start" for e in received_events)
        assert any(
            e["type"] == "orchestrator_final_answer"
            and "Existing orchestration completed." in e["content"]
            for e in received_events
        )
        assert any(e["status"] == "completed" for e in received_events)

        mock_existing_orchestrator.run.assert_awaited_once_with(
            mission_query,
            log_id=1,  # Default log_id from mock_sql_connection_context
            update_callback=mock_existing_orchestrator.update_callback,
        )
        mock_llm_client.invoke.assert_called_once()
        mock_sql_connection_context.execute.assert_called()


# New test for serving index.html
def test_mcp_serve_index_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Hartonomous MCP</title>" in response.text
    assert '<textarea id="mission-prompt"' in response.text
    assert '<button id="launch-agent-button"' in response.text
    assert '<pre id="scratchpad-output"' in response.text
