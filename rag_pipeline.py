import asyncio
import logging
import os
import threading
import traceback
import json
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer

# Import database connection functions from db_connectors
from db_connectors import get_sql_server_connection
from plugins import call_plugin
from query_utils import (
    SEARCH_NODES_CONTAINS_TEXT,
    execute_sql_query,
    sql_server_connection_context,
    DOCUMENT_SELECT_VECTOR,
)
from utils import milvus_connection_context, neo4j_connection_context
from llm_connector import LLMClient

logger = logging.getLogger(__name__)
try:
    embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
except ImportError as e:
    logger.error(
        (
            "Failed to import SentenceTransformer: %s\n%s",
            e,
            traceback.format_exc(),
        )
    )
    embedding_model = None
except Exception as e:
    logger.error("Failed to load embedding model: %s\n%s", e, traceback.format_exc())
    embedding_model = None

# Initialize LLM client
llm_client = LLMClient()


async def _search_milvus(embedding):
    from config import MILVUS_COLLECTION

    milvus_collection_name = MILVUS_COLLECTION
    try:
        async with milvus_connection_context() as milvus_client:
            if not milvus_client:
                logging.error(
                    (
                        "Milvus client is not available. Cannot proceed with Milvus "
                        "search."
                    )
                )
                return []
            # Corrected line: Call search_milvus using asyncio.to_thread
            results = await asyncio.to_thread(
                search_milvus, milvus_client, embedding, milvus_collection_name
            )
            return results
    except (RuntimeError, ValueError, TypeError) as e:
        logger.error(
            (
                "An error occurred during Milvus search: %s\n%s",
                e,
                traceback.format_exc(),
            )
        )
        return []


async def _search_neo4j(query):
    try:
        async with neo4j_connection_context() as neo4j_driver:
            if not neo4j_driver:
                logging.error(
                    (
                        "Neo4j driver is not available. Cannot proceed with Neo4j "
                        "search."
                    )
                )
                return []
            results = await search_neo4j(neo4j_driver, query)
            return results
    except (RuntimeError, ValueError, TypeError) as e:
        logger.error(
            (
                "An error occurred during Neo4j search: %s\n%s",
                e,
                traceback.format_exc(),
            )
        )
        return []


async def _search_sql_server(query_embedding, sql_server_conn=None):
    if sql_server_conn is None:
        try:
            sql_server_conn = get_sql_server_connection()
        except (RuntimeError, ValueError, TypeError) as exc:
            logger.error(
                (
                    "Failed to get SQL Server connection: %s\n%s",
                    exc,
                    traceback.format_exc(),
                )
            )
            return []
    try:
        # Use async with for the context manager
        async with sql_server_connection_context(sql_server_conn) as (
            conn,
            cursor,
        ):
            if not conn:
                logging.error(
                    "SQL Server connection is not available. "
                    "Cannot proceed with SQL Server search."
                )
                return []

            # Use asyncio.to_thread for blocking cursor operations
            await asyncio.to_thread(
                execute_sql_query,
                cursor,
                DOCUMENT_SELECT_VECTOR,
                (json.dumps(query_embedding),),
            )
            results = await asyncio.to_thread(cursor.fetchall)
            return [
                dict(
                    zip(
                        [column[0] for column in cursor.description],
                        row,
                        strict=True,
                    )
                )
                for row in results
            ]
    except (RuntimeError, ValueError, TypeError) as e:
        logger.error(
            (
                "SQL Server semantic search failed: %s\n%s",
                e,
                traceback.format_exc(),
            )
        )
        return []


async def get_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding for a given text."""
    if embedding_model:
        try:
            # Corrected line: await the result of to_thread before calling .tolist()
            return (await asyncio.to_thread(embedding_model.encode, text)).tolist()
        except (RuntimeError, ValueError, TypeError) as e:
            logger.error(
                (
                    "Failed to generate embedding: %s\n%s",
                    e,
                    traceback.format_exc(),
                )
            )
            return None
    return None


def search_milvus(
    milvus_client, query_embedding: List[float], collection_name: str
) -> List[Dict[str, Any]]:
    """Search for similar vectors in Milvus using MilvusClient."""
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    milvus_results = milvus_client.search(
        collection_name=collection_name,
        data=[query_embedding],
        anns_field="embedding",
        param=search_params,
        limit=5,
        output_fields=["document_id", "text"],
    )
    try:
        # We want to flatten this and extract relevant info
        extracted_results = []
        for hits_list in milvus_results:
            for hit in hits_list:
                extracted_results.append(
                    {
                        "id": hit.id,
                        "distance": hit.distance,
                        "document_id": hit.entity.get("document_id"),
                        "text": hit.entity.get("text"),
                    }
                )
        return extracted_results
    except (RuntimeError, ValueError, TypeError) as e:
        logger.error("Milvus search failed: %s\n%s", e, traceback.format_exc())
        return []


async def search_neo4j(neo4j_driver, query: str) -> List[str]:
    """Search for relevant nodes in Neo4j."""
    if not neo4j_driver:
        logger.error("Neo4j driver is not available.")
        return [] # Return empty list if driver is not available

    try:
        # Neo4j session and run are blocking, so run in a thread
        session = await asyncio.to_thread(neo4j_driver.session)
        try:
            result = await asyncio.to_thread(
                session.run,
                SEARCH_NODES_CONTAINS_TEXT,
                query=query,
            )
            return [record["text"] for record in result]
        finally:
            await asyncio.to_thread(session.close)  # Close session in a thread
    except (RuntimeError, ValueError, TypeError) as e:
        logger.error(
            (
                "Neo4j search failed: %s\n%s",
                e,
                traceback.format_exc(),
            )
        )
        return []


async def generate_response(
    query: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Generate a RAG response from Milvus, Neo4j, and SQL Server."""
    responses = {}
    audit_log = []
    overall_error = None  # New variable to track overall error

    # Generate embedding for the query
    embedding = await get_embedding(query)  # Await the async function
    if embedding is None:
        overall_error = "Failed to generate query embedding."

    # If embedding failed, return error immediately
    if overall_error == "Failed to generate query embedding.":
        return {"error": overall_error}

    # Milvus search
    milvus_results = []
    milvus_available = True
    try:
        if overall_error is None:
            milvus_results = await _search_milvus(embedding)  # Await the async function
            milvus_available = milvus_results is not None
    except Exception as e:
        milvus_available = False
        overall_error = f"Milvus search failed: {e}"
        logger.error(f"Milvus search failed: {e}\n{traceback.format_exc()}")
    responses["milvus"] = milvus_results
    audit_log.append({"source": "milvus", "query": query, "results": milvus_results})

    # Neo4j search
    neo4j_results = []
    neo4j_available = True
    try:
        if overall_error is None:
            neo4j_results = await _search_neo4j(query)  # Await the async function
            neo4j_available = neo4j_results is not None
    except Exception as e:
        neo4j_available = False
        overall_error = f"Neo4j search failed: {e}"
        logger.error(f"Neo4j search failed: {e}\n{traceback.format_exc()}")
    responses["neo4j"] = neo4j_results
    audit_log.append({"source": "neo4j", "query": query, "results": neo4j_results})

    # SQL Server search (already async)
    sql_server_results = []
    sql_server_available = True
    try:
        if overall_error is None:
            sql_server_results = await _search_sql_server(embedding)
            sql_server_available = sql_server_results is not None
    except Exception as e:
        sql_server_available = False
        overall_error = f"SQL Server search failed: {e}"
        logger.error("SQL Server search failed: %s\n%s", e, traceback.format_exc())
    responses["sql_server"] = sql_server_results
    audit_log.append(
        {"source": "sql_server", "query": query, "results": sql_server_results}
    )

    # If all DB connections are unavailable, return error in final_response
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
    combined_context = []
    if milvus_results:
        combined_context.extend([r["text"] for r in milvus_results if r.get("text")])
    if neo4j_results:
        combined_context.extend(neo4j_results)
    if sql_server_results:
        combined_context.extend(
            [r["text"] for r in sql_server_results if r.get("text")]
        )

    # LLM integration
    final_response_text = ""
    if llm_client:
        prompt = (
            f"Given the following context: {os.linesep}"
            + "\n".join(combined_context)
            + f"{os.linesep}{os.linesep}Answer the following question: "
            + f"{query}{os.linesep}Answer:"
        )
        try:
            # Generate text using the LLM client
            generated_text = await llm_client.invoke(prompt)
            # Extract only the answer part
            # if the prompt is included in the output
            if isinstance(generated_text, str) and generated_text.startswith(prompt):
                final_response_text = generated_text[len(prompt) :].strip()
            elif isinstance(generated_text, str):
                final_response_text = generated_text.strip()
            else:
                final_response_text = str(generated_text)
        except Exception as e:
            logger.error(f"LLM text generation failed: {e}\n{traceback.format_exc()}")
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

    # Plugin/tool hook
    plugin_results = await call_plugin(  # Await call_plugin
        "echo",
        {
            "query": query,
            "context": context,
            "responses": responses,
            "final_response": final_response_text,
        },
    )

    return {
        "final_response": final_response_text,
        "responses": responses,
        "audit_log": audit_log,
        "plugin_results": plugin_results,
    }


def run_rag_async(
    query: str,
    context: Optional[Dict[str, Any]] = None,
    callback: Optional[Any] = None,
):
    """
    Run RAG pipeline in a background thread.
    """

    def task():
        result = asyncio.run(generate_response(query, context))
        if callback:
            callback(result)

    thread = threading.Thread(target=task)
    thread.start()
    return thread
