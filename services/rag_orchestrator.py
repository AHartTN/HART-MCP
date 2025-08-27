import logging
import os
import traceback
from typing import Any, Dict, List, Optional

from llm_connector import LLMClient
from plugins import call_plugin
from services.database_search import (
    search_milvus_async,
    search_neo4j_async,
    search_sql_server_async,
)
from services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    def __init__(self, embedding_service: EmbeddingService, llm_client: LLMClient):
        self.embedding_service = embedding_service
        self.llm_client = llm_client

    async def generate_response(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a RAG response from Milvus, Neo4j, and SQL Server."""
        responses = {}
        audit_log = []
        overall_error = None

        # Generate embedding for the query
        embedding = await self._generate_query_embedding(query)
        if embedding is None:
            overall_error = "Failed to generate query embedding."

        # If embedding failed, return error immediately
        if overall_error == "Failed to generate query embedding.":
            return {"error": overall_error}

        # Perform database searches
        (
            milvus_results,
            neo4j_results,
            sql_server_results,
            overall_error,
            milvus_available,
            neo4j_available,
            sql_server_available,
        ) = await self._perform_database_searches(embedding, query, overall_error)

        responses["milvus"] = milvus_results
        audit_log.append(
            {"source": "milvus", "query": query, "results": milvus_results}
        )
        responses["neo4j"] = neo4j_results
        audit_log.append({"source": "neo4j", "query": query, "results": neo4j_results})
        responses["sql_server"] = sql_server_results
        audit_log.append(
            {"source": "sql_server", "query": query, "results": sql_server_results}
        )

        # Handle overall database connection errors
        if (
            (not milvus_available or milvus_results == [])
            and (not neo4j_available or neo4j_results == [])
            and (not sql_server_available or sql_server_results == [])
        ):
            return {
                "final_response": "Failed to connect to all databases.",
                "responses": responses,
                "audit_log": audit_log,
                "plugin_results": None,
            }

        # If there's an overall error, return it immediately in final_response
        if overall_error:
            return {
                "final_response": overall_error,
                "responses": responses,
                "audit_log": audit_log,
                "plugin_results": None,
            }

        # Combine retrieved context for LLM
        combined_context = self._combine_context(
            milvus_results, neo4j_results, sql_server_results
        )

        # LLM integration
        final_response_text = await self._generate_llm_response(query, combined_context)

        # Plugin/tool hook
        plugin_results = await self._call_plugins(
            query, context, responses, final_response_text
        )

        return {
            "final_response": final_response_text,
            "responses": responses,
            "audit_log": audit_log,
            "plugin_results": plugin_results,
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

    async def _perform_database_searches(
        self,
        embedding: List[float],
        query: str,
        overall_error: Optional[str],
    ):
        milvus_results = []
        milvus_available = True
        try:
            if overall_error is None:
                milvus_results = await search_milvus_async(embedding)
                milvus_available = milvus_results is not None
        except Exception as e:
            milvus_available = False
            overall_error = f"Milvus search failed: {e}"
            logger.error(f"Milvus search failed: {e}\n{traceback.format_exc()}")

        neo4j_results = []
        neo4j_available = True
        try:
            if overall_error is None:
                neo4j_results = await search_neo4j_async(query)
                neo4j_available = neo4j_results is not None
        except Exception as e:
            neo4j_available = False
            overall_error = f"Neo4j search failed: {e}"
            logger.error(f"Neo4j search failed: {e}\n{traceback.format_exc()}")

        sql_server_results = []
        sql_server_available = True
        try:
            if overall_error is None:
                sql_server_results = await search_sql_server_async(embedding)
                sql_server_available = sql_server_results is not None
        except Exception as e:
            sql_server_available = False
            overall_error = f"SQL Server search failed: {e}"
            logger.error("SQL Server search failed: %s\n%s", e, traceback.format_exc())

        return (
            milvus_results,
            neo4j_results,
            sql_server_results,
            overall_error,
            milvus_available,
            neo4j_available,
            sql_server_available,
        )

    def _combine_context(
        self,
        milvus_results: List[Dict[str, Any]],
        neo4j_results: List[str],
        sql_server_results: List[Dict[str, Any]],
    ) -> List[str]:
        combined_context = []
        if milvus_results:
            combined_context.extend(
                [r["text"] for r in milvus_results if r.get("text")]
            )
        if neo4j_results:
            combined_context.extend(neo4j_results)
        if sql_server_results:
            combined_context.extend(
                [r["text"] for r in sql_server_results if r.get("text")]
            )
        return combined_context

    async def _generate_llm_response(
        self, query: str, combined_context: List[str]
    ) -> str:
        final_response_text = ""
        if self.llm_client:
            prompt = (
                f"Given the following context: {os.linesep}"
                + "\n".join(combined_context)
                + f"{os.linesep}{os.linesep}Answer the following question: "
                + f"{query}{os.linesep}Answer:"
            )
            try:
                generated_text = await self.llm_client.invoke(prompt)
                if isinstance(generated_text, str) and generated_text.startswith(
                    prompt
                ):
                    final_response_text = generated_text[len(prompt) :].strip()
                elif isinstance(generated_text, str):
                    final_response_text = generated_text.strip()
                else:
                    final_response_text = str(generated_text)
            except Exception as e:
                logger.error(
                    f"LLM text generation failed: {e}\n{traceback.format_exc()}"
                )
                final_response_text = (
                    (f"Error generating response with LLM. Context found: {os.linesep}")
                    + "\n".join(combined_context)
                    + f"{os.linesep}{os.linesep}Regarding your query: {query}"
                )
        else:
            final_response_text = (
                f"LLM not loaded. Context found: {os.linesep}"
                + "\n".join(combined_context)
                + f"{os.linesep}{os.linesep}Regarding your query: {query}"
            )
        return final_response_text

    async def _call_plugins(
        self,
        query: str,
        context: Optional[Dict[str, Any]],
        responses: Dict[str, Any],
        final_response_text: str,
    ) -> Any:
        plugin_results = await call_plugin(
            "echo",
            {
                "query": query,
                "context": context,
                "responses": responses,
                "final_response": final_response_text,
            },
        )
        return plugin_results
