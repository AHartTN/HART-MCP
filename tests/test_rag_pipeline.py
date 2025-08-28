import pytest
from unittest.mock import AsyncMock, MagicMock

from llm_connector import LLMClient
from plugins import call_plugin
from services.embedding_service import EmbeddingService
from services.rag_orchestrator import RAGOrchestrator
from services.database_search import (
    search_milvus_async,
    search_neo4j_async,
    search_sql_server_async,
)


# --- Fixtures ---


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    mock_client = AsyncMock(spec=LLMClient)
    mock_client.invoke.return_value = "Mocked LLM response"
    return mock_client


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for testing."""
    mock_service = AsyncMock(spec=EmbeddingService)
    mock_service.get_embedding.return_value = [0.1, 0.2, 0.3]
    return mock_service


# --- Tests for EmbeddingService ---


@pytest.mark.asyncio
async def test_embedding_service_get_embedding_success():
    """Test successful embedding generation."""
    service = EmbeddingService()
    service.embedding_model = MagicMock()
    service.embedding_model.encode.return_value = MagicMock(
        tolist=lambda: [0.1, 0.2, 0.3]
    )

    embedding = await service.get_embedding("test text")
    assert embedding == [0.1, 0.2, 0.3]
    service.embedding_model.encode.assert_called_once_with("test text")


@pytest.mark.asyncio
async def test_embedding_service_get_embedding_no_model():
    """Test embedding generation when no model is loaded."""
    service = EmbeddingService()
    service.embedding_model = None

    embedding = await service.get_embedding("test text")
    assert embedding is None


# --- Tests for Database Search Functions ---


class MockMilvusClient:
    def search(self, *args, **kwargs):
        return [
            [
                MagicMock(
                    id="1",
                    distance=0.1,
                    entity={"document_id": "doc1", "text": "milvus text"},
                )
            ]
        ]

    def close(self):
        pass


class MockNeo4jDriver:
    def session(self):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_session_context():
            mock_session = AsyncMock()
            # Mock the run method to return a result object
            mock_result = AsyncMock()
            mock_result.data.return_value = [{"text": "neo4j text"}]
            mock_session.run.return_value = mock_result
            mock_session.close = AsyncMock()
            yield mock_session

        return mock_session_context()

    async def close(self):
        pass


class MockSQLConnection:
    def cursor(self):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("sql server text",)]
        mock_cursor.description = [("DocumentContent",)]
        mock_cursor.close = MagicMock()
        return mock_cursor

    def commit(self):
        pass

    def close(self):
        pass


@pytest.mark.asyncio
async def test_search_milvus_async_success(monkeypatch):
    """Test successful Milvus search."""
    mock_client = MockMilvusClient()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_milvus_context():
        yield mock_client

    monkeypatch.setattr(
        "services.database_search.milvus_connection_context", mock_milvus_context
    )

    # Create a 1536-dimensional vector to match Milvus collection expectations
    test_embedding = [0.1] * 1536  # All values set to 0.1 for simplicity
    results = await search_milvus_async(test_embedding)
    assert len(results) == 1
    assert results[0]["text"] == "milvus text"


@pytest.mark.asyncio
async def test_search_neo4j_async_success(monkeypatch):
    """Test successful Neo4j search."""
    mock_driver = MockNeo4jDriver()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_neo4j_context():
        yield mock_driver

    monkeypatch.setattr(
        "services.database_search.neo4j_connection_context", mock_neo4j_context
    )

    results = await search_neo4j_async("test query")
    assert len(results) == 1
    assert results[0] == "neo4j text"


@pytest.mark.asyncio
async def test_search_sql_server_async_success(monkeypatch):
    """Test successful SQL Server search."""
    mock_conn = MockSQLConnection()
    mock_cursor = mock_conn.cursor()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_sql_context():
        yield mock_conn, mock_cursor

    monkeypatch.setattr(
        "services.database_search.sql_connection_context", mock_sql_context
    )

    results = await search_sql_server_async([0.1, 0.2, 0.3])
    assert len(results) == 1
    assert results[0]["DocumentContent"] == "sql server text"


# --- Tests for RAGOrchestrator ---


@pytest.mark.asyncio
async def test_rag_orchestrator_generate_response_success(
    mock_llm_client, mock_embedding_service, monkeypatch
):
    """Test successful RAG response generation."""
    # Mock database search functions in the RAGOrchestrator module
    monkeypatch.setattr(
        "services.rag_orchestrator.search_milvus_async",
        AsyncMock(return_value=[{"text": "milvus context"}]),
    )
    monkeypatch.setattr(
        "services.rag_orchestrator.search_neo4j_async",
        AsyncMock(return_value=["neo4j context"]),
    )
    monkeypatch.setattr(
        "services.rag_orchestrator.search_sql_server_async",
        AsyncMock(return_value=[{"text": "sql context"}]),
    )
    monkeypatch.setattr(
        "plugins.call_plugin", AsyncMock(return_value={"plugin": "result"})
    )

    orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client)
    response = await orchestrator.generate_response("What is the capital of France?")

    # Verify response structure
    assert "final_response" in response
    assert response["final_response"] == "Mocked LLM response"
    assert "responses" in response
    assert "audit_log" in response

    # Verify that services were called
    mock_embedding_service.get_embedding.assert_called_once()
    mock_llm_client.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_rag_orchestrator_generate_response_embedding_failure(
    mock_llm_client, mock_embedding_service
):
    """Test RAG response when embedding generation fails."""
    mock_embedding_service.get_embedding.return_value = None

    orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client)
    response = await orchestrator.generate_response("test query")

    assert "error" in response
    assert response["error"] == "Failed to generate query embedding."


@pytest.mark.asyncio
async def test_rag_orchestrator_generate_response_all_db_unavailable(
    mock_llm_client, mock_embedding_service, monkeypatch
):
    """Test RAG response when all databases are unavailable."""
    # Mock all databases to return empty results
    monkeypatch.setattr(
        "services.database_search.search_milvus_async", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        "services.database_search.search_neo4j_async", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        "services.database_search.search_sql_server_async", AsyncMock(return_value=[])
    )

    orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client)
    response = await orchestrator.generate_response("test query")

    assert "final_response" in response
    assert response["final_response"] == "Failed to connect to all databases."


# --- Integration Tests ---


@pytest.mark.asyncio
async def test_rag_pipeline_integration(monkeypatch):
    """Test the RAG pipeline integration with actual service instances."""
    from rag_pipeline import rag_orchestrator

    # Mock the underlying database connections to avoid network calls
    monkeypatch.setattr(
        "services.rag_orchestrator.search_milvus_async",
        AsyncMock(return_value=[{"text": "integration test context"}]),
    )
    monkeypatch.setattr(
        "services.rag_orchestrator.search_neo4j_async",
        AsyncMock(return_value=["integration test neo4j context"]),
    )
    monkeypatch.setattr(
        "services.rag_orchestrator.search_sql_server_async",
        AsyncMock(return_value=[{"text": "integration test sql context"}]),
    )
    monkeypatch.setattr(
        "plugins.call_plugin", AsyncMock(return_value={"status": "success"})
    )

    # Mock the embedding service in the global instance
    rag_orchestrator.embedding_service.get_embedding = AsyncMock(
        return_value=[0.1, 0.2, 0.3]
    )

    # Mock the LLM client in the global instance
    rag_orchestrator.llm_client.invoke = AsyncMock(
        return_value="Integration test response"
    )

    response = await rag_orchestrator.generate_response("integration test query")

    # Verify the response structure
    assert "final_response" in response
    assert response["final_response"] == "Integration test response"
    assert "responses" in response

    # Verify that the embedding service was called
    rag_orchestrator.embedding_service.get_embedding.assert_called_once_with(
        "integration test query"
    )
