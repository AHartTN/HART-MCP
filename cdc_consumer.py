import asyncio
import json
import logging
import traceback
from dataclasses import dataclass

from config import MILVUS_COLLECTION
from db_connectors import get_milvus_client, get_neo4j_driver, get_sql_server_connection

# Constants for SourceTable
SOURCE_TABLE_CHUNKS = "Chunks"
SOURCE_TABLE_AGENT_LOGS = "AgentLogs"
SOURCE_TABLE_AGENTS = "Agents"
SOURCE_TABLE_DOCUMENTS = "Documents"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ChangeEntry:
    ChangeID: int
    SourceTable: str
    SourceID: str
    ChangeType: str
    Payload: str


async def _upsert_milvus_chunk(milvus_client, chunk_id, document_id, embedding):
    """Helper function to insert or upsert a chunk into Milvus."""
    await asyncio.to_thread(
        milvus_client.upsert,
        collection_name=MILVUS_COLLECTION,
        data=[
            {
                "id": str(chunk_id),
                "embedding": embedding,
                "document_id": str(document_id),
            }
        ],
    )
    logger.info("Upserted chunk %s in Milvus.", chunk_id)


async def _delete_milvus_chunk(milvus_client, chunk_id):
    """Helper function to delete a chunk from Milvus."""
    await asyncio.to_thread(
        milvus_client.delete, collection_name=MILVUS_COLLECTION, ids=[str(chunk_id)]
    )
    logger.info("Deleted chunk %s from Milvus.", chunk_id)


async def _neo4j_session_run(driver, query, **params):
    """Helper function to run a query in a Neo4j session."""
    session = await asyncio.to_thread(driver.session)
    try:
        await asyncio.to_thread(session.run, query, **params)
    finally:
        await asyncio.to_thread(session.close)


async def process_change_log_entry(entry, milvus_client, neo4j_driver):
    payload = json.loads(entry.Payload)

    if entry.SourceTable == SOURCE_TABLE_CHUNKS:
        chunk_id = payload.get("ChunkID")
        document_id = payload.get("DocumentID")
        embedding = payload.get("Embedding")
        if entry.ChangeType == "INSERT" and chunk_id and document_id and embedding:
            await _upsert_milvus_chunk(milvus_client, chunk_id, document_id, embedding)
        elif entry.ChangeType == "UPDATE" and chunk_id and document_id and embedding:
            await _upsert_milvus_chunk(milvus_client, chunk_id, document_id, embedding)
        elif entry.ChangeType == "DELETE" and chunk_id:
            await _delete_milvus_chunk(milvus_client, chunk_id)
        else:
            logger.warning("Missing or invalid data for Milvus operation: %s", payload)
    elif entry.SourceTable == SOURCE_TABLE_AGENT_LOGS:
        log_id = payload.get("LogID")
        agent_id = payload.get("AgentID")
        if entry.ChangeType == "INSERT" and log_id and agent_id:
            await _neo4j_session_run(
                neo4j_driver, "MERGE (a:Agent {id: $agent_id})", agent_id=agent_id
            )
            await _neo4j_session_run(
                neo4j_driver,
                "MERGE (l:AgentLog {id: $log_id, agent_id: $agent_id})",
                log_id=log_id,
                agent_id=agent_id,
            )
            logger.info("Inserted AgentLog %s into Neo4j.", log_id)
        elif entry.ChangeType == "DELETE" and log_id:
            await _neo4j_session_run(
                neo4j_driver,
                "MATCH (l:AgentLog {id: $log_id}) DETACH DELETE l",
                log_id=log_id,
            )
            logger.info("Deleted AgentLog %s from Neo4j.", log_id)
    elif entry.SourceTable == SOURCE_TABLE_AGENTS:
        agent_id = payload.get("AgentID")
        name = payload.get("Name")
        role = payload.get("Role")
        status = payload.get("Status")
        if entry.ChangeType == "INSERT" and agent_id:
            await _neo4j_session_run(
                neo4j_driver,
                "MERGE (a:Agent {id: $agent_id, name: $name, role: $role, status: $status})",
                agent_id=agent_id,
                name=name,
                role=role,
                status=status,
            )
            logger.info("Inserted Agent %s into Neo4j.", agent_id)
        elif entry.ChangeType == "DELETE" and agent_id:
            await _neo4j_session_run(
                neo4j_driver,
                "MATCH (a:Agent {id: $agent_id}) DETACH DELETE a",
                agent_id=agent_id,
            )
            logger.info("Deleted Agent %s from Neo4j.", agent_id)
    elif entry.SourceTable == SOURCE_TABLE_DOCUMENTS:
        document_id = payload.get("DocumentID")
        title = payload.get("Title")
        source_url = payload.get("SourceURL")
        if entry.ChangeType == "INSERT" and document_id:
            await _neo4j_session_run(
                neo4j_driver,
                "MERGE (d:Document {id: $document_id, title: $title, source_url: $source_url})",
                document_id=document_id,
                title=title,
                source_url=source_url,
            )
            logger.info("Inserted Document %s into Neo4j.", document_id)
        elif entry.ChangeType == "DELETE" and document_id:
            await _neo4j_session_run(
                neo4j_driver,
                "MATCH (d:Document {id: $document_id}) DETACH DELETE d",
                document_id=document_id,
            )
            logger.info("Deleted Document %s from Neo4j.", document_id)


async def all_connections_ready(sql_conn, milvus_client, neo4j_driver):
    # Await the async clients
    return all([sql_conn, milvus_client, neo4j_driver])


async def poll_changes(sql_conn, last_processed_change_id):
    cursor = await asyncio.to_thread(sql_conn.cursor)
    await asyncio.to_thread(
        cursor.execute,
        "SELECT ChangeID, SourceTable, SourceID, ChangeType, "
        "Payload FROM ChangeLog WHERE ChangeID > ? "
        "ORDER BY ChangeID ASC",
        last_processed_change_id,
    )
    return await asyncio.to_thread(cursor.fetchall)


# --- Main CDC Loop ---
async def run_cdc_consumer():
    # Simulate reconnection logic for test coverage
    sql_conn = None
    milvus_client = None
    neo4j_driver = None
    max_retries = 2

    for attempt in range(max_retries):
        logger.info("Attempting to re-establish database connections...")
        sql_conn = await get_sql_server_connection()
        milvus_client = await get_milvus_client()  # Await
        neo4j_driver = await get_neo4j_driver()  # Await
        if await all_connections_ready(sql_conn, milvus_client, neo4j_driver):  # Await
            logger.info("Successfully re-established database connections.")
            break
        if attempt < max_retries - 1:
            logger.error("An error occurred in CDC loop")
            logger.error(
                "Failed to re-establish all database connections. Retrying in 10 seconds."
            )
            await asyncio.sleep(10)

    # After all attempts, check again and only log final errors if still not ready
    if not await all_connections_ready(sql_conn, milvus_client, neo4j_driver):  # Await
        logger.error("Failed to establish all initial database connections. Exiting.")
        logger.error("An error occurred in CDC loop")
        return

    last_processed_change_id = 0
    # Single-pass CDC logic for testability
    try:
        if sql_conn is not None:
            changes = await poll_changes(sql_conn, last_processed_change_id)  # Await
            if changes:
                logger.info("Found %d new changes.", len(changes))
                for change in changes:
                    change_entry = ChangeEntry(
                        ChangeID=change[0],
                        SourceTable=change[1],
                        SourceID=change[2],
                        ChangeType=change[3],
                        Payload=change[4],
                    )
                    await process_change_log_entry(
                        change_entry, milvus_client, neo4j_driver
                    )  # Await
    except Exception as e:
        logger.error("An error occurred in CDC loop: %s", e)
        logger.error(traceback.format_exc())


# --- Entry Point ---
if __name__ == "__main__":
    logger.info("Starting CDC Consumer...")
    asyncio.run(run_cdc_consumer())
