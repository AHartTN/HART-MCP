import pytest
from unittest.mock import AsyncMock, MagicMock

from llm_connector import LLMClient
from plugins import call_plugin
from rag_pipeline import (
    _search_milvus,
    _search_neo4j,
    _search_sql_server,
    generate_response,
    get_embedding,
)

# Mock the LLMClient at a module level for these tests
# This ensures that generate_response uses our mock
pytest.fixture(autouse=True)


def import pytest
from unittest.mock import AsyncMock, MagicMock

from llm_connector import LLMClient
from plugins import call_plugin # Keep if call_plugin is still used in RAGOrchestrator
from services.embedding_service import EmbeddingService
from services.rag_orchestrator import RAGOrchestrator
from services.database_search import search_milvus, search_neo4j, search_sql_server_async
from utils import milvus_connection_context, neo4j_connection_context, sql_connection_context
from db_connectors import get_milvus_client, get_neo4j_driver, get_sql_server_connection
from query_utils import DOCUMENT_SELECT_VECTOR, SEARCH_NODES_CONTAINS_TEXT, execute_sql_query

# Mock the LLMClient for RAGOrchestrator
@pytest.fixture(autouse=True)
def mock_llm_client_for_rag_tests(monkeypatch):
    mock_client = AsyncMock(spec=LLMClient)
    mock_client.invoke.return_value = "Mocked LLM response"
    # We will pass this mock directly to RAGOrchestrator
    return mock_client

# Mock EmbeddingService
@pytest.fixture
def mock_embedding_service(monkeypatch):
    mock_service = AsyncMock(spec=EmbeddingService)
    mock_service.get_embedding.return_value = [0.1, 0.2, 0.3]
    return mock_service

# Mock Database Search Functions
@pytest.fixture
def mock_database_search_functions(monkeypatch):
    monkeypatch.setattr("services.database_search.search_milvus_async", AsyncMock(return_value=[]))
    monkeypatch.setattr("services.database_search.search_neo4j_async", AsyncMock(return_value=[]))
    monkeypatch.setattr("services.database_search.search_sql_server_async", AsyncMock(return_value=[]))

# --- Tests for EmbeddingService ---
@pytest.mark.asyncio
async def test_embedding_service_get_embedding_success(mock_embedding_service):
    service = EmbeddingService()
    service.embedding_model = MagicMock()
    service.embedding_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
    
    embedding = await service.get_embedding("test text")
    assert embedding == [0.1, 0.2, 0.3]
    service.embedding_model.encode.assert_called_once_with("test text")

@pytest.mark.asyncio
async def test_embedding_service_get_embedding_no_model(monkeypatch):
    service = EmbeddingService()
    service.embedding_model = None # Simulate no model loaded
    
    embedding = await service.get_embedding("test text")
    assert embedding is None

# --- Tests for Database Search Functions (from services/database_search.py) ---

class MockMilvusClient:
    def search(self, *args, **kwargs):
        return [[MagicMock(id="1", distance=0.1, entity={"document_id": "doc1", "text": "milvus text"})]]
    def close(self):
        pass

class MockNeo4jDriver:
    def session(self):
        mock_session = MagicMock()
        mock_session.run.return_value = [{"text": "neo4j text"}]
        mock_session.close = MagicMock()
        return mock_session
    def close(self):
        pass

class MockSQLServerConnection:
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
    mock_milvus_client_instance = MockMilvusClient()
    monkeypatch.setattr("utils.milvus_connection_context", AsyncMock(return_value=mock_milvus_client_instance))
    
    results = await search_milvus_async([0.1, 0.2, 0.3])
    assert len(results) == 1
    assert results[0]["text"] == "milvus text"

@pytest.mark.asyncio
async def test_search_neo4j_async_success(monkeypatch):
    mock_neo4j_driver_instance = MockNeo4jDriver()
    monkeypatch.setattr("utils.neo4j_connection_context", AsyncMock(return_value=mock_neo4j_driver_instance))
    
    results = await search_neo4j_async("test query")
    assert len(results) == 1
    assert results[0] == "neo4j text"

@pytest.mark.asyncio
async def test_search_sql_server_async_success(monkeypatch):
    mock_sql_conn_instance = MockSQLServerConnection()
    monkeypatch.setattr("utils.sql_connection_context", AsyncMock(return_value=(mock_sql_conn_instance, mock_sql_conn_instance.cursor())))
    monkeypatch.setattr("db_connectors.get_sql_server_connection", MagicMock(return_value=mock_sql_conn_instance))
    
    results = await search_sql_server_async([0.1, 0.2, 0.3])
    assert len(results) == 1
    assert results[0]["DocumentContent"] == "sql server text"

# --- Tests for RAGOrchestrator ---

@pytest.mark.asyncio
async def test_rag_orchestrator_generate_response_success(mock_llm_client_for_rag_tests, mock_embedding_service, monkeypatch):
    # Mock internal methods of RAGOrchestrator or underlying service calls
    monkeypatch.setattr("services.database_search.search_milvus_async", AsyncMock(return_value=[{"text": "milvus context"}]))
    monkeypatch.setattr("services.database_search.search_neo4j_async", AsyncMock(return_value=["neo4j context"]))
    monkeypatch.setattr("services.database_search.search_sql_server_async", AsyncMock(return_value=[{"text": "sql context"}]))
    monkeypatch.setattr("plugins.call_plugin", AsyncMock(return_value={"plugin": "result"}))

    orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client_for_rag_tests)
    query = "What is the capital of France?"
    response = await orchestrator.generate_response(query)

    assert "final_response" in response
    assert response["final_response"] == "Mocked LLM response"
    assert "responses" in response
    assert "milvus" in response["responses"]
    assert "neo4j" in response["responses"]
    assert "sql_server" in response["responses"]
    assert "audit_log" in response
    assert "plugin_results" in response

    # Verify that key methods were called
    mock_embedding_service.get_embedding.assert_called_once_with(query)
    mock_llm_client_for_rag_tests.invoke.assert_called_once()
    call_plugin.assert_called_once()

@pytest.mark.asyncio
async def test_rag_orchestrator_generate_response_embedding_failure(mock_llm_client_for_rag_tests, mock_embedding_service):
    mock_embedding_service.get_embedding.return_value = None
    orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client_for_rag_tests)
    response = await orchestrator.generate_response("test query")
    assert response["error"] == "Failed to generate query embedding."

@pytest.mark.asyncio
async def test_rag_orchestrator_generate_response_all_db_unavailable(mock_llm_client_for_rag_tests, mock_embedding_service, monkeypatch):
    monkeypatch.setattr("services.database_search.search_milvus_async", AsyncMock(return_value=[]))
    monkeypatch.setattr("services.database_search.search_neo4j_async", AsyncMock(return_value=[]))
    monkeypatch.setattr("services.database_search.search_sql_server_async", AsyncMock(return_value=[]))

    orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client_for_rag_tests)
    response = await orchestrator.generate_response("test query")
    assert response["final_response"] == "Failed to connect to all databases."
:
    mock_client = AsyncMock(spec=LLMClient)
    mock_client.invoke.return_value = "Mocked LLM response"
    monkeypatch.setattr("rag_pipeline.llm_client", mock_client)
    return mock_client


@pytest.fixture
def mock_embedding_model(monkeypatch):
    mock_model = MagicMock()
    mock_model.encode.return_value = MagicMock(tolist=lambda: [0.1, 0.2, 0.3])
    monkeypatch.setattr("rag_pipeline.embedding_model", mock_model)
    return mock_model


@pytest.mark.asyncio
async def test_get_embedding_success(mock_embedding_model):
    text = "test text"
    embedding = await get_embedding(text)
    assert embedding == [0.1, 0.2, 0.3]
    mock_embedding_model.encode.assert_called_once_with(text)


@pytest.mark.asyncio
async def test_get_embedding_no_model(monkeypatch):
    monkeypatch.setattr("rag_pipeline.embedding_model", None)
    embedding = await get_embedding("test text")
    assert embedding is None


class MockMilvusContext:
    def __init__(self, client):
        self.client = client

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_search_milvus_success(monkeypatch):
    mock_milvus_client = MagicMock()
    mock_milvus_client.search.return_value = [
        [
            MagicMock(
                id="1",
                distance=0.1,
                entity={"document_id": "doc1", "text": "milvus text"},
            )
        ]
    ]
    monkeypatch.setattr(
        "rag_pipeline.milvus_connection_context",
        lambda: MockMilvusContext(mock_milvus_client),
    )

    results = await _search_milvus([0.1, 0.2, 0.3])
    assert len(results) == 1
    assert results[0]["text"] == "milvus text"


class MockNeo4jContext:
    def __init__(self, driver):
        self.driver = driver

    async def __aenter__(self):
        return self.driver

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_search_neo4j_success(monkeypatch):
    mock_neo4j_driver = MagicMock()
    mock_session = MagicMock()
    mock_session.run.return_value = [{"text": "neo4j text"}]
    mock_neo4j_driver.session.return_value = mock_session
    monkeypatch.setattr(
        "rag_pipeline.neo4j_connection_context",
        lambda: MockNeo4jContext(mock_neo4j_driver),
    )

    results = await _search_neo4j("test query")
    assert len(results) == 1
    assert results[0] == "neo4j text"


class MockSQLServerContext:
    def __init__(self, conn, cursor):
        self.conn = conn
        self.cursor = cursor

    async def __aenter__(self):
        return self.conn, self.cursor

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.mark.asyncio
async def test_search_sql_server_success(monkeypatch):
    mock_sql_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("sql server text",)]
    mock_cursor.description = [("DocumentContent",)]
    monkeypatch.setattr(
        "rag_pipeline.sql_server_connection_context",
        AsyncMock(return_value=MockSQLServerContext(mock_sql_conn, mock_cursor)),
    )
    monkeypatch.setattr(
        "rag_pipeline.get_sql_server_connection", MagicMock(return_value=mock_sql_conn)
    )

    results = await _search_sql_server([0.1, 0.2, 0.3])
    assert len(results) == 1
    assert results[0]["DocumentContent"] == "sql server text"


@pytest.mark.asyncio
async def test_generate_response_success(mock_embedding_model, monkeypatch):
    # Mock all search functions to return some data
    monkeypatch.setattr(
        "rag_pipeline._search_milvus",
        AsyncMock(return_value=[{"text": "milvus context"}]),
    )
    monkeypatch.setattr(
        "rag_pipeline._search_neo4j", AsyncMock(return_value=["neo4j context"])
    )
    monkeypatch.setattr(
        "rag_pipeline._search_sql_server",
        AsyncMock(return_value=[{"DocumentContent": "sql context"}]),
    )
    monkeypatch.setattr(
        "rag_pipeline.call_plugin", AsyncMock(return_value={"plugin": "result"})
    )

    query = "What is the capital of France?"
    response = await generate_response(query)

    assert "final_response" in response
    assert response["final_response"] == "Mocked LLM response"
    assert "responses" in response
    assert "milvus" in response["responses"]
    assert "neo4j" in response["responses"]
    assert "sql_server" in response["responses"]
    assert "audit_log" in response
    assert "plugin_results" in response

    # Verify that search functions were called
    _search_milvus.assert_called_once()
    _search_neo4j.assert_called_once_with(query)
    _search_sql_server.assert_called_once_with([0.1, 0.2, 0.3])
    mock_llm_client_for_rag_tests.invoke.assert_called_once()
    call_plugin.assert_called_once()


@pytest.mark.asyncio
async def test_generate_response_embedding_failure(monkeypatch):
    monkeypatch.setattr("rag_pipeline.get_embedding", AsyncMock(return_value=None))
    response = await generate_response("test query")
    assert response["error"] == "Failed to generate query embedding."


@pytest.mark.asyncio
async def test_generate_response_all_db_unavailable(mock_embedding_model, monkeypatch):
    monkeypatch.setattr("rag_pipeline._search_milvus", AsyncMock(return_value=[]))
    monkeypatch.setattr("rag_pipeline._search_neo4j", AsyncMock(return_value=[]))
    monkeypatch.setattr("rag_pipeline._search_sql_server", AsyncMock(return_value=[]))

    response = await generate_response("test query")
    assert response["final_response"] == "Failed to connect to all databases."