from unittest.mock import MagicMock, patch

import pytest

from server import app


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        yield client


# --- Tests ---
def test_retrieve_success(client):
    with (
        patch("routes.retrieve.get_embedding") as mock_get_embedding,
        patch("routes.retrieve.search_milvus") as mock_search_milvus,
        patch("routes.retrieve.get_milvus_client") as mock_get_milvus_client,
    ):
        mock_get_embedding.return_value = [0.1, 0.2, 0.3]
        mock_search_milvus.return_value = [{"id": "1", "text": "test"}]
        mock_get_milvus_client.return_value = (
            MagicMock()
        )  # Simulate successful connection

    response = client.post("/retrieve", json={"query": "test"})
    assert response.status_code == 200
    assert response.json() == {"results": [{"id": "1", "text": "test"}]}
    mock_get_embedding.assert_called_once_with("test")
    mock_search_milvus.assert_called_once()
    mock_get_milvus_client.assert_called_once()


def test_retrieve_validation_error(client):
    response = client.post("/retrieve", json={"invalid_field": "test"})
    assert response.status_code == 400
    assert "Validation error" in response.json()["error"]


def test_retrieve_get_embedding_failure(client):
    with patch("routes.retrieve.get_embedding") as mock_get_embedding:
        mock_get_embedding.return_value = None
        response = client.post("/retrieve", json={"query": "test"})
        assert response.status_code == 500
    assert response.json() == {"error": "Failed to generate query embedding."}


def test_retrieve_milvus_connection_failure(client):
    with patch("routes.retrieve.get_milvus_client") as mock_get_milvus_client:
        mock_get_milvus_client.return_value = None
        response = client.post("/retrieve", json={"query": "test"})
        assert response.status_code == 500
    assert response.json() == {"error": "Failed to connect to Milvus."}


def test_retrieve_general_exception(client):
    with patch("routes.retrieve.get_embedding") as mock_get_embedding:
        mock_get_embedding.side_effect = Exception("Simulated error")
        response = client.post("/retrieve", json={"query": "test"})
        assert response.status_code == 500
    assert "Internal server error" in response.json()["error"]
