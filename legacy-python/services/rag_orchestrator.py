import logging
import os
import traceback
from typing import Any, Dict, List, Optional

from llm_connector import LLMClient
from plugins import call_plugin
from services.embedding_service import EmbeddingService
from services.unified_database_service import EnhancedUnifiedSearchService
from utils.error_handlers import ErrorCode, safe_execute, StandardizedError

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """Enhanced RAG orchestrator with unified database service and better error handling."""
    
    def __init__(self, 
                 embedding_service: EmbeddingService, 
                 llm_client: LLMClient,
                 unified_db_service: Optional[EnhancedUnifiedSearchService] = None):
        self.embedding_service = embedding_service
        self.llm_client = llm_client
        self.unified_db_service = unified_db_service or EnhancedUnifiedSearchService()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @safe_execute(ErrorCode.GENERIC_ERROR)
    async def generate_response(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        include_vector: bool = True,
        include_graph: bool = True,
        include_relational: bool = False,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Enhanced RAG response generation with unified database service."""
        if not query or not isinstance(query, str):
            return self._create_error_response("Query parameter is required and must be a string")
        
        self._logger.info(f"Generating RAG response for query: {query[:100]}...")
        
        try:
            # Generate embedding for the query
            embedding = await self._generate_query_embedding(query)
            if embedding is None and include_vector:
                self._logger.warning("Failed to generate embedding, skipping vector search")
                include_vector = False

            # Perform unified database search
            search_results = await self.unified_db_service.search_all(
                query=query,
                embedding=embedding,
                limit=limit,
                include_vector=include_vector,
                include_graph=include_graph,
                include_relational=include_relational
            )

            # Check if any searches were successful
            if not search_results.get("search_successful", False):
                error_msg = "No database searches succeeded"
                if search_results.get("errors"):
                    error_msg += f": {'; '.join([str(e) for e in search_results['errors']])}"
                
                return {
                    "final_response": error_msg,
                    "search_results": search_results,
                    "context_used": [],
                    "plugin_results": None,
                    "success": False
                }

            # Combine retrieved context for LLM
            combined_context = self._combine_enhanced_context(search_results)

            # Generate LLM response
            final_response_text = await self._generate_llm_response(query, combined_context)

            # Call plugins/hooks
            plugin_results = await self._call_plugins(
                query, context, search_results, final_response_text
            )

            return {
                "final_response": final_response_text,
                "search_results": search_results,
                "context_used": combined_context,
                "plugin_results": plugin_results,
                "success": True,
                "query": query,
                "services_used": search_results.get("services_attempted", [])
            }
            
        except Exception as e:
            self._logger.error(f"Error in RAG generation: {e}", exc_info=True)
            return self._create_error_response(f"RAG generation failed: {str(e)}")
    
    def _create_error_response(self, message: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            "final_response": message,
            "search_results": {"vector_results": [], "graph_results": [], "errors": [message]},
            "context_used": [],
            "plugin_results": None,
            "success": False,
            "error": message
        }

    async def _generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """Generate embedding for the query using the embedding service."""
        try:
            return await self.embedding_service.get_embedding(query)
        except Exception as e:
            logger.error(
                f"Failed to generate query embedding: {e}\n{traceback.format_exc()}"
            )
            return None

    def _combine_enhanced_context(
        self,
        search_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Combine search results into enhanced context with source attribution."""
        combined_context = []
        
        # Process vector results
        for result in search_results.get("vector_results", []):
            if result.get("text"):
                combined_context.append({
                    "text": result["text"],
                    "source": "vector_search",
                    "score": result.get("score", 0),
                    "document_id": result.get("document_id"),
                    "metadata": {
                        "distance": result.get("distance"),
                        "vector_id": result.get("id")
                    }
                })
        
        # Process graph results
        for result in search_results.get("graph_results", []):
            if result.get("text"):
                context_entry = {
                    "text": result["text"],
                    "source": "graph_search",
                    "score": 1.0,  # Graph results don't have similarity scores
                    "metadata": {
                        "relationships": result.get("relationships", []),
                        "node_id": result.get("id")
                    }
                }
                
                # Add relationship information to text if available
                if result.get("relationships"):
                    rel_info = "; ".join([
                        f"{rel.get('type', 'RELATED')}: {rel.get('related_text', '')}"
                        for rel in result["relationships"][:3]  # Limit to first 3 relationships
                    ])
                    if rel_info:
                        context_entry["text"] += f" [Related: {rel_info}]"
                
                combined_context.append(context_entry)
        
        # Process relational results
        for result in search_results.get("relational_results", []):
            if isinstance(result, dict):
                # Convert SQL result to text representation
                text_parts = []
                for key, value in result.items():
                    if key != "source" and value is not None:
                        text_parts.append(f"{key}: {value}")
                
                if text_parts:
                    combined_context.append({
                        "text": "; ".join(text_parts),
                        "source": "relational_search",
                        "score": 1.0,
                        "metadata": {"raw_result": result}
                    })
        
        # Sort by score (highest first) and limit results
        combined_context.sort(key=lambda x: x.get("score", 0), reverse=True)
        return combined_context[:10]  # Limit to top 10 results

    # Legacy method kept for backward compatibility
    def _combine_context(
        self,
        milvus_results: List[Dict[str, Any]],
        neo4j_results: List[str],
    ) -> List[str]:
        """Legacy context combination method."""
        combined_context = []
        if milvus_results:
            combined_context.extend(
                [r["text"] for r in milvus_results if r.get("text")]
            )
        if neo4j_results:
            combined_context.extend(neo4j_results)
        return combined_context

    @safe_execute(ErrorCode.LLM_RESPONSE)
    async def _generate_llm_response(
        self, query: str, combined_context: List[Dict[str, Any]]
    ) -> str:
        """Generate LLM response with enhanced context handling."""
        if not self.llm_client:
            context_text = self._format_context_for_display(combined_context)
            return (
                f"LLM not available. Based on retrieved context:\n\n{context_text}\n\n"
                f"This information relates to your query: {query}"
            )
        
        try:
            # Format context with source attribution
            formatted_context = self._format_context_for_llm(combined_context)
            
            prompt = (
                f"You are an AI assistant answering questions based on retrieved context. "
                f"Use the following context to answer the question accurately and comprehensively.\n\n"
                f"Context:\n{formatted_context}\n\n"
                f"Question: {query}\n\n"
                f"Please provide a detailed answer based on the context above. "
                f"If the context doesn't fully address the question, say so and provide what information is available."
            )
            
            self._logger.debug(f"LLM prompt length: {len(prompt)} characters")
            
            generated_text = await self.llm_client.invoke(prompt)
            
            if isinstance(generated_text, str):
                # Clean up response if it starts with the prompt
                if generated_text.startswith(prompt):
                    response = generated_text[len(prompt):].strip()
                else:
                    response = generated_text.strip()
                
                if not response:
                    response = "I was unable to generate a response based on the provided context."
                    
                return response
            else:
                return str(generated_text)
                
        except Exception as e:
            self._logger.error(f"LLM text generation failed: {e}", exc_info=True)
            context_text = self._format_context_for_display(combined_context)
            return (
                f"Error generating LLM response: {str(e)}\n\n"
                f"Retrieved context:\n{context_text}\n\n"
                f"Regarding your query: {query}"
            )
    
    def _format_context_for_llm(self, context: List[Dict[str, Any]]) -> str:
        """Format context for LLM consumption with source attribution."""
        formatted_parts = []
        for i, ctx in enumerate(context, 1):
            source = ctx.get("source", "unknown")
            text = ctx.get("text", "")
            score = ctx.get("score", 0)
            
            formatted_parts.append(
                f"[Source {i} - {source.replace('_', ' ').title()} (relevance: {score:.2f})]\n{text}"
            )
        
        return "\n\n".join(formatted_parts)
    
    def _format_context_for_display(self, context: List[Dict[str, Any]]) -> str:
        """Format context for user display."""
        if not context:
            return "No relevant context found."
        
        formatted_parts = []
        for ctx in context:
            source = ctx.get("source", "unknown")
            text = ctx.get("text", "")
            formatted_parts.append(f"[{source.replace('_', ' ').title()}] {text}")
        
        return "\n\n".join(formatted_parts)

    @safe_execute(ErrorCode.GENERIC_ERROR, default_return=None)
    async def _call_plugins(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        search_results: Dict[str, Any],
        final_response_text: str,
    ) -> Any:
        """Call plugins with enhanced data structure."""
        try:
            plugin_data = {
                "query": query,
                "context": context,
                "search_results": search_results,
                "final_response": final_response_text,
                "timestamp": __import__('datetime').datetime.now().isoformat(),
                "services_used": search_results.get("services_attempted", []),
                "total_results": search_results.get("total_results", 0)
            }
            
            plugin_results = await call_plugin("echo", plugin_data)
            self._logger.debug(f"Plugin execution completed: {type(plugin_results)}")
            return plugin_results
        except Exception as e:
            self._logger.error(f"Plugin execution failed: {e}", exc_info=True)
            return None
    
    async def get_orchestrator_health(self) -> Dict[str, Any]:
        """Get health status of the RAG orchestrator and its dependencies."""
        health_status = {
            "orchestrator_healthy": True,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        
        # Check embedding service
        try:
            if self.embedding_service:
                # Try generating a test embedding
                test_embedding = await self.embedding_service.get_embedding("test")
                health_status["embedding_service"] = test_embedding is not None
            else:
                health_status["embedding_service"] = False
        except Exception as e:
            health_status["embedding_service"] = False
            health_status["embedding_error"] = str(e)
        
        # Check LLM client
        try:
            if self.llm_client:
                health_status["llm_client"] = True
                # Could add a test invocation here if needed
            else:
                health_status["llm_client"] = False
        except Exception as e:
            health_status["llm_client"] = False
            health_status["llm_error"] = str(e)
        
        # Check unified database service
        try:
            db_health = await self.unified_db_service.get_service_status()
            health_status["database_services"] = db_health
        except Exception as e:
            health_status["database_services"] = {"error": str(e)}
        
        return health_status
