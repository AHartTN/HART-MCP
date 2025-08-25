import asyncio
import logging
import os
import threading
import traceback
from typing import Any, Dict, List, Optional

from sentence_transformers import SentenceTransformer
from transformers import pipeline

# Import database connection functions from db_connectors
from db_connectors import get_sql_server_connection
from plugins import call_plugin
from query_utils import (
    DOCUMENT_SELECT_LIKE,
    SEARCH_NODES_CONTAINS_TEXT,
    execute_sql_query,
    sql_server_connection_context,
)
from utils import milvus_connection_context, neo4j_connection_context

logger = logging.getLogger(__name__)
try:
    embedding_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
except Exception as e:
    logger.error(f"Failed to load embedding model: {e}\n{traceback.format_exc()}")
    embedding_model = None

# Initialize LLM pipeline
try:
    llm_pipeline = pipeline("text-generation", model="distilgpt2")
except Exception as e:
    logger.error(f"Failed to load LLM model: {e}\n{traceback.format_exc()}")
    llm_pipeline = None


async def _search_milvus(embedding):
    from config import MILVUS_COLLECTION

    milvus_collection_name = MILVUS_COLLECTION
    try:
        async with milvus_connection_context() as milvus_client:
            if not milvus_client:
                logging.error(
                    "Milvus client is not available. Cannot proceed with Milvus search."
                )
                return []
            results = await search_milvus(
                milvus_client, embedding, milvus_collection_name
            )
            return results
    except Exception as e:
        logging.error(
            f"An error occurred during Milvus search: {e}\n{traceback.format_exc()}"
        )
        return []


async def _search_neo4j(query):
    try:
        async with neo4j_connection_context() as neo4j_driver:
            if not neo4j_driver:
                logging.error(
                    "Neo4j driver is not available. Cannot proceed with Neo4j search."
                )
                return []
            results = await search_neo4j(neo4j_driver, query)
            return results
    except Exception as e:
        logging.error(
            f"An error occurred during Neo4j search: {e}\n{traceback.format_exc()}"
        )
        return []


async def _search_sql_server(query, sql_server_conn=None):
    if sql_server_conn is None:
        try:
            sql_server_conn = await get_sql_server_connection()
        except Exception as exc:
            logging.error(
                f"Failed to get SQL Server connection: {exc}\n{traceback.format_exc()}"
            )
            return []
    try:
        # Use async with for the context manager
        async with sql_server_connection_context(sql_server_conn) as (conn, cursor):
            if not conn:
                logging.error(
                    "SQL Server connection is not available. "
                    "Cannot proceed with SQL Server search."
                )
                return []

            # Use asyncio.to_thread for blocking cursor operations
            await asyncio.to_thread(
                execute_sql_query, cursor, DOCUMENT_SELECT_LIKE, (f"%{query}%",)
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
    except Exception as e:
        logging.error(
            f"SQL Server semantic search failed: {e}\n{traceback.format_exc()}"
        )
        return []


async def get_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding for a given text."""
    if embedding_model:
        try:
            return await asyncio.to_thread(embedding_model.encode, text).tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}\n{traceback.format_exc()}")
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
    except Exception as e:
        logger.error(f"Milvus search failed: {e}\n{traceback.format_exc()}")
        return []


async def search_neo4j(neo4j_driver, query: str) -> List[str]:
    """Search for relevant nodes in Neo4j."""
    if not neo4j_driver:
        logger.error("Neo4j driver is not available.")
        return []
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
    except Exception as e:
        logger.error(f"Neo4j search failed: {e}\n{traceback.format_exc()}")
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
            sql_server_results = await _search_sql_server(query)
            sql_server_available = sql_server_results is not None
    except Exception as e:
        sql_server_available = False
        overall_error = f"SQL Server search failed: {e}"
        logger.error(f"SQL Server search failed: {e}\n{traceback.format_exc()}")
    responses["sql_server"] = sql_server_results
    audit_log.append(
        {"source": "sql_server", "query": query, "results": sql_server_results}
    )

    # If all DB connections are unavailable, return error
    if (
        (not milvus_available or milvus_results == [])
        and (not neo4j_available or neo4j_results == [])
        and (not sql_server_available or sql_server_results == [])
    ):
        return {"error": "Database connection error."}

    # If there's an overall error, return it immediately
    if overall_error:
        return {"error": overall_error}

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
    if llm_pipeline:
        prompt = (
            f"Given the following context: {os.linesep}"
            + "\n".join(combined_context)
            + f"{os.linesep}{os.linesep}Answer the following question: "
            + f"{query}{os.linesep}Answer:"
        )
        try:
            # Generate text using the LLM pipeline
            generated_text = (
                await asyncio.to_thread(
                    llm_pipeline, prompt, max_new_tokens=100, num_return_sequences=1
                )
            )[0]["generated_text"]
            # Extract only the answer part
            # if the prompt is included in the output
            if generated_text.startswith(prompt):
                final_response_text = generated_text[len(prompt) :].strip()
            else:
                final_response_text = generated_text.strip()
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
    callback: Optional[callable] = None,
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
