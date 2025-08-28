import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from llm_connector import LLMClient
from plugins import call_plugin
from services.embedding_service import EmbeddingService
from services.rag_orchestrator import RAGOrchestrator
from services.unified_database_service import EnhancedUnifiedSearchService
from plugins_folder.tools import RAGTool, CheckForClarificationsTool, TreeOfThoughtTool


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


@pytest.fixture
def mock_unified_db_service():
    """Mock unified database service for testing."""
    mock_service = AsyncMock(spec=EnhancedUnifiedSearchService)
    mock_service.search_all.return_value = {
        "vector_results": [{"text": "milvus context", "score": 0.9, "source": "milvus"}],
        "graph_results": [{"text": "neo4j context", "score": 1.0, "source": "neo4j"}],
        "relational_results": [],
        "errors": [],
        "search_successful": True,
        "services_attempted": ["vector", "graph"]
    }
    mock_service.get_service_status.return_value = {
        "vector": {"healthy": True},
        "graph": {"healthy": True},
        "relational": {"healthy": True}
    }
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


# --- Tests for Database Services ---


@pytest.mark.asyncio
async def test_unified_db_service_search_success():
    """Test successful unified database service search."""
    mock_service = EnhancedUnifiedSearchService()
    
    with patch.object(mock_service.vector_service, 'search_by_vector') as mock_vector, \
         patch.object(mock_service.graph_service, 'search_nodes') as mock_graph, \
         patch.object(mock_service.vector_service, 'is_healthy') as mock_vector_health, \
         patch.object(mock_service.graph_service, 'is_healthy') as mock_graph_health:
        
        mock_vector_health.return_value = True
        mock_graph_health.return_value = True
        mock_vector.return_value = [{"text": "vector result", "score": 0.9, "source": "milvus"}]
        mock_graph.return_value = [{"text": "graph result", "source": "neo4j"}]
        
        results = await mock_service.search_all(
            query="test query",
            embedding=[0.1] * 1536
        )
        
        assert results["search_successful"] is True
        assert len(results["vector_results"]) == 1
        assert len(results["graph_results"]) == 1


# --- Tests for Enhanced Tools ---


@pytest.mark.asyncio
async def test_rag_tool_execution():
    """Test RAG tool execution with mocked orchestrator."""
    mock_orchestrator = AsyncMock()
    mock_orchestrator.generate_response.return_value = {
        "final_response": "Test RAG response",
        "success": True
    }
    
    rag_tool = RAGTool(mock_orchestrator)
    result = await rag_tool.execute(query="What is machine learning?")
    
    assert result["status"] == "success"
    assert "Test RAG response" in str(result["data"])
    mock_orchestrator.generate_response.assert_called_once()


@pytest.mark.asyncio
async def test_tree_of_thought_tool_execution():
    """Test Tree of Thought tool execution."""
    mock_llm = AsyncMock()
    mock_llm.invoke.side_effect = [
        '["Approach 1", "Approach 2", "Approach 3"]',  # Generation response
        '0.8',  # Evaluation for first approach
        '0.6',  # Evaluation for second approach
        '0.9',  # Evaluation for third approach
    ]
    
    tot_tool = TreeOfThoughtTool(mock_llm)
    result = await tot_tool.execute(prompt="How to solve climate change?")
    
    assert result["status"] == "success"
    assert "thoughts" in result["data"]
    assert "best_thought" in result["data"]
    assert len(result["data"]["thoughts"]) == 3


@pytest.mark.asyncio
async def test_clarification_tool_execution():
    """Test clarification checking tool."""
    clarification_tool = CheckForClarificationsTool()
    
    # Test query that needs clarification
    result = clarification_tool.execute(query="Help me")
    assert result["status"] == "success"
    assert result["data"]["needs_clarification"] is True
    
    # Test query that doesn't need clarification
    result = clarification_tool.execute(query="What is the capital of France and when was it founded?")
    assert result["status"] == "success"
    assert result["data"]["needs_clarification"] is False




# --- Tests for RAGOrchestrator ---


@pytest.mark.asyncio
async def test_rag_orchestrator_generate_response_success(
    mock_llm_client, mock_embedding_service, mock_unified_db_service
):
    """Test successful RAG response generation with unified service."""
    with patch('plugins.call_plugin', new_callable=AsyncMock) as mock_plugin:
        mock_plugin.return_value = {"plugin": "result"}
        
        orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client, mock_unified_db_service)
        response = await orchestrator.generate_response("What is the capital of France?")

        # Verify response structure
        assert "final_response" in response
        assert response["final_response"] == "Mocked LLM response"
        assert "search_results" in response
        assert "context_used" in response
        assert response["success"] is True

        # Verify that services were called
        mock_embedding_service.get_embedding.assert_called_once()
        mock_llm_client.invoke.assert_called_once()
        mock_unified_db_service.search_all.assert_called_once()


@pytest.mark.asyncio
async def test_rag_orchestrator_generate_response_embedding_failure(
    mock_llm_client, mock_embedding_service, mock_unified_db_service
):
    """Test RAG response when embedding generation fails but graph search succeeds."""
    mock_embedding_service.get_embedding.return_value = None
    # Mock successful graph search even without embedding
    mock_unified_db_service.search_all.return_value = {
        "vector_results": [],
        "graph_results": [{"text": "graph only result", "source": "neo4j"}],
        "relational_results": [],
        "errors": [],
        "search_successful": True,
        "services_attempted": ["graph"]
    }

    orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client, mock_unified_db_service)
    response = await orchestrator.generate_response("test query")

    # Should still succeed with graph results
    assert "final_response" in response
    assert response["success"] is True


@pytest.mark.asyncio
async def test_rag_orchestrator_generate_response_all_db_unavailable(
    mock_llm_client, mock_embedding_service
):
    """Test RAG response when all databases are unavailable."""
    # Mock failed unified database service
    mock_failed_db_service = AsyncMock()
    mock_failed_db_service.search_all.return_value = {
        "vector_results": [],
        "graph_results": [],
        "relational_results": [],
        "errors": ["All services failed"],
        "search_successful": False,
        "services_attempted": ["vector", "graph"]
    }

    orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client, mock_failed_db_service)
    response = await orchestrator.generate_response("test query")

    assert "final_response" in response
    assert response["success"] is False
    assert "No database searches succeeded" in response["final_response"]


# --- Integration Tests ---


@pytest.mark.asyncio
async def test_rag_pipeline_integration():
    """Test the RAG pipeline integration with enhanced architecture.""" 
    mock_embedding_service = AsyncMock()
    mock_embedding_service.get_embedding.return_value = [0.1, 0.2, 0.3]
    
    mock_llm_client = AsyncMock()
    mock_llm_client.invoke.return_value = "Integration test response"
    
    mock_unified_db = AsyncMock()
    mock_unified_db.search_all.return_value = {
        "vector_results": [{"text": "integration vector context", "score": 0.9, "source": "milvus"}],
        "graph_results": [{"text": "integration graph context", "source": "neo4j"}],
        "relational_results": [],
        "errors": [],
        "search_successful": True,
        "services_attempted": ["vector", "graph"],
        "total_results": 2
    }

    with patch('plugins.call_plugin', new_callable=AsyncMock) as mock_plugin:
        mock_plugin.return_value = {"status": "success"}
        
        orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client, mock_unified_db)
        response = await orchestrator.generate_response("integration test query")

        # Verify the enhanced response structure
        assert "final_response" in response
        assert response["final_response"] == "Integration test response"
        assert "search_results" in response
        assert "context_used" in response
        assert "services_used" in response
        assert response["success"] is True

        # Verify that services were called correctly
        mock_embedding_service.get_embedding.assert_called_once_with("integration test query")
        mock_llm_client.invoke.assert_called_once()
        mock_unified_db.search_all.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_health_check():
    """Test RAG orchestrator health check functionality."""
    mock_embedding_service = AsyncMock()
    mock_embedding_service.get_embedding.return_value = [0.1, 0.2, 0.3]
    
    mock_llm_client = AsyncMock()
    
    mock_unified_db = AsyncMock()
    mock_unified_db.get_service_status.return_value = {
        "vector": {"healthy": True, "name": "Milvus"},
        "graph": {"healthy": True, "name": "Neo4j"},
        "relational": {"healthy": False, "error": "Connection failed"}
    }
    
    orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client, mock_unified_db)
    health = await orchestrator.get_orchestrator_health()
    
    assert "orchestrator_healthy" in health
    assert "embedding_service" in health
    assert "llm_client" in health
    assert "database_services" in health
    assert health["embedding_service"] is True
    assert health["llm_client"] is True


# --- Error Handling Tests ---


@pytest.mark.asyncio
async def test_tool_error_handling():
    """Test enhanced tool error handling."""
    # Test RAG tool with invalid input
    rag_tool = RAGTool()
    result = await rag_tool.execute()  # No query provided (async tool)
    
    assert result["status"] == "error"
    assert "error_code" in result
    
    # Test Tree of Thought tool with missing LLM client (use valid prompt length)
    tot_tool = TreeOfThoughtTool(None)  # No LLM client
    result = await tot_tool.execute(prompt="How to solve complex problems?")
    
    assert result["status"] == "error"
    assert "LLM client not available" in result["message"]


@pytest.mark.asyncio  
async def test_orchestrator_error_recovery():
    """Test orchestrator error recovery mechanisms."""
    mock_embedding_service = AsyncMock()
    mock_embedding_service.get_embedding.side_effect = Exception("Embedding service down")
    
    mock_llm_client = AsyncMock()
    mock_llm_client.invoke.return_value = "Fallback response"
    
    # Mock DB service to still work for graph search
    mock_unified_db = AsyncMock()
    mock_unified_db.search_all.return_value = {
        "vector_results": [],
        "graph_results": [{"text": "graph fallback", "source": "neo4j"}],
        "relational_results": [],
        "errors": ["Embedding generation failed"],
        "search_successful": True,
        "services_attempted": ["graph"]
    }
    
    orchestrator = RAGOrchestrator(mock_embedding_service, mock_llm_client, mock_unified_db)
    
    # Should still generate response using graph results
    response = await orchestrator.generate_response("test query")
    assert response["success"] is True
    assert "final_response" in response