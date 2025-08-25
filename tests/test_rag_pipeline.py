from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag_pipeline import generate_response
from server import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_db_connections():
    with (
        patch(
            "db_connectors.get_sql_server_connection", new_callable=AsyncMock
        ) as mock_get_sql_conn,
        patch("db_connectors.get_milvus_client") as mock_get_milvus_client,
        patch("db_connectors.get_neo4j_driver") as mock_get_neo4j_driver,
    ):
        # Mock SQL Server Connection
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            ("SQL Text 1",),
            ("SQL Text 2",),
        ]
        mock_cursor.description = [
            ("DocumentContent",)
        ]  # Mock description for dict conversion
        mock_sql_conn_instance = MagicMock()
        mock_sql_conn_instance.cursor.return_value = mock_cursor
        mock_get_sql_conn.return_value = mock_sql_conn_instance

        # Mock Milvus Client
        mock_milvus_client_instance = MagicMock()
        mock_milvus_client_instance.search.return_value = [
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
        mock_get_milvus_client.return_value = mock_milvus_client_instance

        # Mock Neo4j Driver
        mock_neo4j_driver_instance = MagicMock()
        mock_neo4j_driver_instance.session.return_value.__enter__.return_value.run.return_value = [
            {"text": "Neo4j Text 1"},
            {"text": "Neo4j Text 2"},
        ]
        mock_get_neo4j_driver.return_value = mock_neo4j_driver_instance

        yield (
            mock_sql_conn_instance,
            mock_milvus_client_instance,
            mock_neo4j_driver_instance,
        )


@pytest.mark.asyncio
async def test_generate_response(mock_db_connections):
    mock_sql_conn_instance, mock_milvus_client_instance, mock_neo4j_driver_instance = (
        mock_db_connections
    )
    query = "test query"
    with patch("rag_pipeline.llm_pipeline") as mock_llm_pipeline:
        mock_llm_pipeline.return_value = [
            {"generated_text": "This is a generated response."}
        ]
        response = await generate_response(query)

    # Verify that search functions were called
    mock_milvus_client_instance.search.assert_called_once()
    mock_neo4j_driver_instance.session.return_value.__enter__.return_value.run.assert_called_once()
    mock_sql_conn_instance.cursor.return_value.execute.assert_called_once()

    assert "final_response" in response
    assert "responses" in response
    assert "audit_log" in response
    assert "plugin_results" in response
    assert response["final_response"] == "This is a generated response."


@pytest.mark.asyncio
async def test_generate_response_db_connection_failure(mock_db_connections):
    # Test scenario where one or more DB connections fail
    with patch("db_connectors.get_sql_server_connection", return_value=None):
        with patch("db_connectors.get_milvus_client", return_value=None):
            with patch("db_connectors.get_neo4j_driver", return_value=None):
                response = await generate_response("test query")
                assert "error" in response
                assert response["error"] == "Database connection error."


@pytest.mark.asyncio
async def test_generate_response_embedding_failure(mock_db_connections):
    with patch("rag_pipeline.get_embedding", return_value=None):
        response = await generate_response("test query")
        assert "error" in response
        assert response["error"] == "Failed to generate query embedding."
