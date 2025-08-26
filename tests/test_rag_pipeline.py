import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from rag_pipeline import generate_response


@pytest.mark.asyncio
async def test_generate_response_success():
    """
    Tests successful response generation from the RAG pipeline.
    Mocks database connections, search results, and LLM pipeline.
    """
    mock_sql_cursor = MagicMock()
    mock_sql_cursor.fetchall.return_value = [("SQL Text 1",), ("SQL Text 2",)]
    mock_sql_cursor.description = [("DocumentContent",)] # For dict conversion
    mock_sql_conn = MagicMock()
    mock_sql_conn.cursor.return_value = mock_sql_cursor

    mock_milvus_client = MagicMock()
    mock_milvus_client.search.return_value = [
        [
            MagicMock(id="milvus_id_1", distance=0.1, entity={"document_id": "doc1", "text": "Milvus Text 1"}),
            MagicMock(id="milvus_id_2", distance=0.2, entity={"document_id": "doc2", "text": "Milvus Text 2"}),
        ]
    ]

    mock_neo4j_session = MagicMock()
    mock_neo4j_session.run.return_value = [{"text": "Neo4j Text 1"}, {"text": "Neo4j Text 2"}]
    mock_neo4j_driver = MagicMock()
    mock_neo4j_driver.session.return_value.__enter__.return_value = mock_neo4j_session


    with patch("db_connectors.get_sql_server_connection", new_callable=AsyncMock, return_value=mock_sql_conn), \
         patch("db_connectors.get_milvus_client", new_callable=AsyncMock, return_value=mock_milvus_client), \
         patch("db_connectors.get_neo4j_driver", new_callable=AsyncMock, return_value=mock_neo4j_driver), \
         patch("rag_pipeline.llm_pipeline", new_callable=AsyncMock) as mock_llm_pipeline, \
         patch("rag_pipeline.get_embedding", new_callable=AsyncMock, return_value=[0.1, 0.2, 0.3]): # Mock embedding

        mock_llm_pipeline.return_value = [{"generated_text": "This is a generated response."}]

        query = "test query"
        response = await generate_response(query)

        assert "final_response" in response
        assert response["final_response"] == "This is a generated response."
        assert mock_sql_conn.cursor.return_value.execute.called
        assert mock_milvus_client.search.called
        assert mock_neo4j_session.run.called
        assert mock_llm_pipeline.called


@pytest.mark.asyncio
async def test_generate_response_db_connection_failure():
    """
    Tests response generation failure when a database connection cannot be established.
    """
    with patch("db_connectors.get_sql_server_connection", new_callable=AsyncMock, return_value=None), \
         patch("db_connectors.get_milvus_client", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("db_connectors.get_neo4j_driver", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("rag_pipeline.get_embedding", new_callable=AsyncMock, return_value=[0.1, 0.2, 0.3]):

        query = "test query"
        response = await generate_response(query)
        assert "error" in response
        assert response["error"] == "Database connection error."


@pytest.mark.asyncio
async def test_generate_response_embedding_failure():
    """
    Tests response generation failure when embedding generation fails.
    """
    with patch("db_connectors.get_sql_server_connection", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("db_connectors.get_milvus_client", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("db_connectors.get_neo4j_driver", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("rag_pipeline.get_embedding", new_callable=AsyncMock, return_value=None): # Simulate embedding failure

        query = "test query"
        response = await generate_response(query)
        assert "error" in response
        assert response["error"] == "Failed to generate query embedding."