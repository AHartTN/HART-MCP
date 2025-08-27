import logging
import threading
from typing import Any, Dict, Optional

# Import database connection functions from db_connectors
from llm_connector import LLMClient
from services.embedding_service import EmbeddingService
from services.rag_orchestrator import RAGOrchestrator
from utils.async_runner import run_async_in_thread  # New import

logger = logging.getLogger(__name__)

# Initialize Embedding Service
embedding_service = EmbeddingService()

# Initialize LLM client
llm_client = LLMClient()

# Initialize RAG Orchestrator
rag_orchestrator = RAGOrchestrator(embedding_service, llm_client)


def run_rag_async(
    query: str,
    context: Optional[Dict[str, Any]] = None,
    callback: Optional[Any] = None,
) -> threading.Thread:
    """
    Run RAG pipeline in a background thread.
    """
    return run_async_in_thread(
        rag_orchestrator.generate_response, query, context=context, callback=callback
    )
