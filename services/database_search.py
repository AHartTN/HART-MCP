import asyncio
import json
import logging
import traceback
from typing import Any, Dict, List


# Import database connection functions from db_connectors
from db_connectors import get_sql_server_connection
from query_utils import (
    DOCUMENT_SELECT_VECTOR,
    SEARCH_NODES_CONTAINS_TEXT,
    execute_sql_query,
)
from utils import (
    milvus_connection_context,
    neo4j_connection_context,
    sql_connection_context,
)  # Corrected import
from config import MILVUS_COLLECTION

logger = logging.getLogger(__name__)


def search_milvus(
    milvus_client, query_embedding: List[float], collection_name: str
) -> List[Dict[str, Any]]:
    """Search for similar vectors in Milvus using MilvusClient."""
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    milvus_results = milvus_client.search(
        collection_name=collection_name,
        data=[query_embedding],
        anns_field="embedding",
        search_params=search_params,
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


async def search_milvus_async(embedding: List[float]) -> List[Dict[str, Any]]:
    """Asynchronously search Milvus."""
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
            results = await asyncio.to_thread(
                search_milvus, milvus_client, embedding, MILVUS_COLLECTION
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


async def search_neo4j(neo4j_driver, query: str) -> List[str]:
    """Search for relevant nodes in Neo4j."""
    if not neo4j_driver:
        logger.error("Neo4j driver is not available.")
        return []  # Return empty list if driver is not available

    try:
        async with neo4j_driver.session() as session:
            result = await session.run(SEARCH_NODES_CONTAINS_TEXT, {"query": query})
            records = await result.data()
            return [record["text"] for record in records]
    except (RuntimeError, ValueError, TypeError) as e:
        logger.error(
            (
                "Neo4j search failed: %s\n%s",
                e,
                traceback.format_exc(),
            )
        )
        return []


async def search_neo4j_async(query: str) -> List[str]:
    """Asynchronously search Neo4j."""
    try:
        async with neo4j_connection_context() as neo4j_driver:
            if not neo4j_driver:
                logging.error(
                    ("Neo4j driver is not available. Cannot proceed with Neo4j search.")
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


async def search_sql_server_async(
    query_embedding: List[float], sql_server_conn=None
) -> List[Dict[str, Any]]:
    """Asynchronously search SQL Server."""
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
        async with sql_connection_context() as (
            conn,
            cursor,
        ):
            if not conn:
                logging.error(
                    "SQL Server connection is not available. "
                    "Cannot proceed with SQL Server search."
                )
                return []

            await asyncio.to_thread(
                execute_sql_query,
                cursor,
                DOCUMENT_SELECT_VECTOR,
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
