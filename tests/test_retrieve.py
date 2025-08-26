import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# The client fixture is automatically provided by conftest.py
import utils # Import utils (still needed for other potential utils functions)
import rag_pipeline # Import rag_pipeline


@pytest.mark.asyncio
async def test_retrieve_success(client):
    """
    Tests successful retrieval from the /retrieve endpoint.
    Mocks embedding generation and Milvus search.
    """
    mock_embedding = [0.1, 0.2, 0.3]
    mock_milvus_results = [{"id": "1", "text": "test result 1"}, {"id": "2", "text": "test result 2"}]

    with patch("rag_pipeline.get_embedding", new_callable=AsyncMock, return_value=mock_embedding), \
         patch("rag_pipeline.search_milvus", new_callable=AsyncMock, return_value=mock_milvus_results), \
         patch("db_connectors.get_milvus_client", new_callable=AsyncMock, return_value=MagicMock()): # Ensure Milvus client is mocked as available

        response = client.post("/retrieve", json={"query": "test query"})

        assert response.status_code == 200
        assert response.json() == {"results": mock_milvus_results}
        rag_pipeline.get_embedding.assert_called_once_with("test query")
        rag_pipeline.search_milvus.assert_called_once_with(MagicMock(), mock_embedding)


@pytest.mark.asyncio
async def test_retrieve_embedding_failure(client):
    """
    Tests retrieval failure when embedding generation fails.
    """
    with patch("rag_pipeline.get_embedding", new_callable=AsyncMock, return_value=None): # Simulate embedding failure
        response = client.post("/retrieve", json={"query": "test query"})

        assert response.status_code == 500
        assert response.json() == {"error": "Failed to generate query embedding."}


@pytest.mark.asyncio
async def test_retrieve_milvus_connection_failure(client):
    """
    Tests retrieval failure when Milvus connection cannot be established.
    """
    mock_embedding = [0.1, 0.2, 0.3]

    with patch("rag_pipeline.get_embedding", new_callable=AsyncMock, return_value=mock_embedding), \
         patch("db_connectors.get_milvus_client", new_callable=AsyncMock, return_value=None): # Simulate Milvus connection failure

        response = client.post("/retrieve", json={"query": "test query"})

        assert response.status_code == 500
        assert response.json() == {"error": "Failed to connect to Milvus."}