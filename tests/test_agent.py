from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_agent_tree_of_thought_success():
    payload = {"agent_id": 1, "log_id": 101, "query": "analyze complex problem"}
    # Mock initiate_tree_of_thought to return a mock Thought object
    with patch(
        "tree_of_thought.initiate_tree_of_thought", new_callable=AsyncMock
    ) as mock_initiate_tot:
        mock_thought = MagicMock()
        mock_thought.to_dict.return_value = {"text": "mock root", "children": []}
        mock_initiate_tot.return_value = mock_thought
        response = client.post(
            "/agent/tree_of_thought", json=payload
        )  # Await client.post
        assert response.status_code == 200
        json_data = response.json()
        assert "message" in json_data
        assert "tree_of_thought_root" in json_data
        mock_initiate_tot.assert_awaited_once_with(
            payload["query"], payload["agent_id"]
        )


@pytest.mark.asyncio
async def test_agent_tree_of_thought_failure():
    payload = {"agent_id": 1, "log_id": 101, "query": "dummy query"}
    with patch(
        "tree_of_thought.initiate_tree_of_thought", new_callable=AsyncMock
    ) as mock_initiate_tot:
        mock_initiate_tot.return_value = None  # Simulate failure
        response = client.post("/agent/tree_of_thought", json=payload)
        assert response.status_code == 500  # Expect 500 for internal failure
        json_data = response.json()
        assert "error" in json_data
        mock_initiate_tot.assert_awaited_once_with(
            payload["query"], payload["agent_id"]
        )


@pytest.mark.asyncio
async def test_agent_reflexion_success():  # Renamed for clarity
    payload = {
        "agent_id": 1,
        "log_id": 101,
        "query": "test query",
    }
    with patch(
        "plugins_folder.agent_core.Agent.perform_rag_query", new_callable=AsyncMock
    ) as mock_perform_rag_query:
        mock_perform_rag_query.return_value = {"final_response": "mocked reflexion"}
        response = client.post("/agent/reflexion", json=payload)
        assert response.status_code == 200
        json_data = response.json()
        assert "reflexion" in json_data
        assert json_data["reflexion"] == "mocked reflexion"
        mock_perform_rag_query.assert_awaited_once_with(
            payload["query"], payload["log_id"]
        )


@pytest.mark.asyncio
async def test_agent_bdi_success():
    payload = {
        "agent_id": 1,
        "log_id": 101,
        "beliefs": {"goal": "solve"},
        "desires": ["complete"],
        "intentions": ["plan"],
    }
    with patch(
        "plugins_folder.agent_core.Agent.update_bdi_state", new_callable=AsyncMock
    ) as mock_update_bdi_state:
        mock_update_bdi_state.return_value = (
            None  # update_bdi_state doesn't return anything
        )
        response = client.post("/agent/bdi", json=payload)
        assert response.status_code == 200
        json_data = response.json()
        assert "message" in json_data
        mock_update_bdi_state.assert_awaited_once_with(
            payload["new_beliefs"],
            payload["new_desires"],
            payload["new_intentions"],
        )


@pytest.mark.asyncio
async def test_agent_bdi_agent_creation_failure():
    payload = {
        "agent_id": 999,  # Assuming this agent_id causes creation failure
        "log_id": 101,
        "new_beliefs": {"goal": "fail"},
        "new_desires": ["fail"],
        "new_intentions": ["fail"],
    }
    # Mock the Agent constructor to raise an exception or return None
    with patch(
        "plugins.call_plugin",
        side_effect=Exception("Agent creation failed"),
    ):
        response = client.post("/agent/bdi", json=payload)
        assert response.status_code == 422
        assert "error" in response.json()


@pytest.mark.asyncio
async def test_agent_endpoint_no_json_payload():
    response = client.post("/agent/tree_of_thought")
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["body"],
                "msg": "Field required",
                "input": None,
            }
        ]
    }


@pytest.mark.asyncio
async def test_agent_endpoint_validation_error():
    payload = {"agent_id": 1}  # Missing log_id and query
    response = client.post("/agent/tree_of_thought", json=payload)
    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "missing",
                "loc": ["body", "log_id"],
                "msg": "Field required",
                "input": {"agent_id": 1},
            },
            {
                "type": "missing",
                "loc": ["body", "query"],
                "msg": "Field required",
                "input": {"agent_id": 1},
            },
        ]
    }


@pytest.mark.asyncio
async def test_agent_endpoint_general_exception():
    payload = {"agent_id": 1, "log_id": 101, "query": "trigger exception"}
    with patch(
        "tree_of_thought.initiate_tree_of_thought",
        side_effect=Exception("Simulated error"),
    ):
        response = client.post("/agent/tree_of_thought", json=payload)
        assert response.status_code == 500
        assert "error" in response.json()


@pytest.mark.asyncio
async def test_agent_reflexion_db_connection_failure():
    payload = {
        "agent_id": 1,
        "log_id": 101,
        "query": "test query",
    }
    with patch(
        "plugins_folder.agent_core.Agent.perform_rag_query",
        side_effect=Exception("DB connection failed"),
    ):
        response = client.post("/agent/reflexion", json=payload)
        assert response.status_code == 500
        assert "error" in response.json()
