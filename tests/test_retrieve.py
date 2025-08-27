# In tests/test_retrieve.py
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from tests.conftest import MockLLMClient


def test_retrieve_success(
    client: TestClient,
    mock_milvus_client: MagicMock,
    mock_llm_client: MockLLMClient,
):
    """
    Tests the /retrieve endpoint's happy path.
    """
    # Arrange
    # 1. Configure the LLM mock to return a simulated embedding.
    mock_llm_client.response = "[0.1, 0.2, 0.3]"  # Simulate embedding

    # 2. Configure the Milvus mock to return search results.
    mock_search_results = [
        {
            "id": "fake_chunk_id_1",
            "score": 0.9,
            "entity": {"text": "This is the first retrieved chunk."},
        }
    ]
    mock_milvus_client.search.return_value = mock_search_results

    # Act
    response = client.post("/retrieve", json={"query": "test query"})

    # Assert
    response.raise_for_status()
    assert response.json() == {"results": mock_search_results}


def test_retrieve_llm_failure(client: TestClient, mock_llm_client: MockLLMClient):
    """
    Tests how /retrieve handles a failure during embedding generation.
    """
    # Arrange: Configure the LLM mock to raise an error.
    mock_llm_client.error = Exception("Embedding model failed")

    # Act
    response = client.post("/retrieve", json={"query": "test query"})

    # Assert
    assert response.status_code == 500
    assert "Embedding model failed" in response.text


def test_retrieve_milvus_failure(
    client: TestClient,
    mock_milvus_client: MagicMock,
    mock_llm_client: MockLLMClient,
):
    """
    Tests how /retrieve handles a failure during Milvus search.
    """
    # Arrange
    # 1. Configure the LLM mock to return a simulated embedding.
    mock_llm_client.response = "[0.1, 0.2, 0.3]"  # Simulate embedding

    # 2. Configure the Milvus mock to raise an error.
    mock_milvus_client.search.side_effect = Exception("Milvus is down")

    # Act
    response = client.post("/retrieve", json={"query": "test query"})

    # Assert
    assert response.status_code == 500
    assert "Milvus is down" in response.text