# In tests/test_rag_pipeline.py
from unittest.mock import MagicMock, AsyncMock

import pytest

from rag_pipeline import generate_response
from tests.conftest import MockLLMClient


@pytest.mark.asyncio
async def test_generate_response_success(
    mock_sql_connection: MagicMock,
    mock_milvus_client: MagicMock,
    mock_neo4j_driver: MagicMock,
    mock_llm_client: MockLLMClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Tests successful response generation from the RAG pipeline.
    """
    # Arrange
    mock_sql_cursor = mock_sql_connection.cursor.return_value
    mock_sql_cursor.fetchall.return_value = [("SQL Text 1",), ("SQL Text 2",)]
    mock_sql_cursor.description = [("text",)]

    mock_milvus_client.search.return_value = [
        [
            MagicMock(
                id="milvus_id_1",
                distance=0.1,
                entity={"document_id": "doc1", "text": "Milvus Text 1"},
            ),
            MagicMock(
                id="milvus_id_2",
                distance=0.2,
                entity={"document_id": "doc2", "text": "Milvus Text 2"},
            ),
        ]
    ]

    mock_neo4j_driver.session.return_value.run.return_value = [
        {"text": "Neo4j Text 1"}, {"text": "Neo4j Text 2"}
    ]

    mock_llm_client.response = "This is a generated response."

    monkeypatch.setattr("rag_pipeline.llm_client", mock_llm_client)

    # Act
    query = "test query"
    response = await generate_response(query)

    # Assert
    assert "final_response" in response
    assert response["final_response"] == "This is a generated response."


@pytest.mark.asyncio
async def test_generate_response_db_connection_failure(
    mock_sql_connection: MagicMock,
    mock_milvus_client: MagicMock,
    mock_neo4j_driver: MagicMock,
    mock_llm_client: MockLLMClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Tests response generation failure when a database connection cannot be established.
    """
    # Arrange
    mock_sql_connection.cursor.side_effect = Exception("DB error")
    monkeypatch.setattr("rag_pipeline.llm_client", mock_llm_client)

    # Act
    query = "test query"
    response = await generate_response(query)

    # Assert
    assert "final_response" in response
    assert response["final_response"] == "Failed to connect to all databases."


@pytest.mark.asyncio
async def test_generate_response_embedding_failure(
    mock_sql_connection: MagicMock,
    mock_milvus_client: MagicMock,
    mock_neo4j_driver: MagicMock,
    mock_llm_client: MockLLMClient,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Tests response generation failure when embedding generation fails.
    """
    # Arrange
    mock_llm_client.error = Exception("Embedding failed")
    monkeypatch.setattr("rag_pipeline.llm_client", mock_llm_client)

    # Act
    query = "test query"
    response = await generate_response(query)

    # Assert
    assert "error" in response
    assert response["error"] == "Failed to generate query embedding."