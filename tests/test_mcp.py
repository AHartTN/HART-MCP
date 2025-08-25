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

    # Create a mock for the Agent object that call_plugin will return
    mock_agent_instance = MagicMock()
    mock_agent_instance.bdi_state = {}

    # Create mocks for SQL Server connection and cursor
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.execute.return_value = None
    mock_cursor.fetchall.return_value = []
    mock_cursor.lastrowid = 456  # Simulate a log_id

    with patch("routes.mcp.get_sql_server_connection") as mock_get_sql_server_connection, \
         patch("plugins.call_plugin") as mock_call_plugin, \
         patch("db_connectors.pyodbc.connect", side_effect=lambda *args, **kwargs: mock_conn): # Patch db_connectors.pyodbc.connect with a side_effect

        # get_sql_server_connection is async, so its return value should be awaitable
        # It internally calls pyodbc.connect, so we mock that directly
        # The return_value of get_sql_server_connection should be an awaitable that returns mock_conn
        mock_get_sql_server_connection.return_value = AsyncMock(return_value=mock_conn)

        mock_call_plugin.return_value = mock_agent_instance

        response = client.post("/mcp", json=mcp_payload)

        assert response.status_code == 200
        response_json = response.json()
        assert "log_id" in response_json
        assert "agent_id" in response_json
        assert response_json["log_id"] == 456
        assert response_json["agent_id"] == 123