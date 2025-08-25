from unittest.mock import patch, AsyncMock, MagicMock
import pytest
import asyncio
# import pyodbc # No longer need to import pyodbc here
from fastapi.testclient import TestClient
from server import app

@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client

def test_mcp_endpoint(client):
    mcp_payload = {
        "query": "test query",
        "context": {"key": "value"},
        "agent_id": 123
    }

    # Create mocks for SQL Server connection and cursor
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    # mock_conn.cursor.return_value = mock_cursor # Removed
    mock_conn.commit.return_value = None # Explicitly mock commit
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.lastrowid = 456  # Simulate a log_id

    with patch("routes.mcp.get_sql_server_connection") as mock_get_sql_server_connection, \
         patch("db_connectors.pyodbc.connect", return_value=mock_conn), \
         patch("routes.mcp.asyncio.to_thread") as mock_to_thread: # Patch asyncio.to_thread

        mock_to_thread.side_effect = [
            AsyncMock(return_value=mock_cursor), # For conn.cursor
            AsyncMock(return_value=None), # For cursor.execute
            AsyncMock(return_value=None), # For conn.commit
            AsyncMock(return_value=456) # For getattr(cursor, "lastrowid", None)
        ]

        # get_sql_server_connection is async, so its return value should be awaitable
        # It internally calls pyodbc.connect, so we mock that directly
        # The return_value of get_sql_server_connection should be an awaitable that returns mock_conn
        mock_get_sql_server_connection.return_value = AsyncMock(return_value=mock_conn)

        # Mock the agent object directly and set its bdi_state
        mock_agent_bdi_state = {"some_key": "some_value"} # Static string for bdi_state
        mock_agent_return_value = MagicMock(bdi_state=mock_agent_bdi_state)

        # Patch the call to call_plugin to return an AsyncMock whose return_value has bdi_state set
        with patch("routes.mcp.call_plugin", return_value=mock_agent_return_value):
            response = client.post("/mcp", json=mcp_payload)

        assert response.status_code == 200
        response_json = response.json()
        assert "log_id" in response_json
        assert "agent_id" in response_json
        assert response_json["log_id"] == 456
        assert response_json["agent_id"] == 123