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
    change_id: int
    source_table: str
    source_id: str
    change_type: str
    payload: str


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
        milvus_client.delete,
        collection_name=MILVUS_COLLECTION,
        ids=[str(chunk_id)],
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
    payload = json.loads(entry.payload)

    async def handle_chunks():
        chunk_id = payload.get("ChunkID")
        document_id = payload.get("DocumentID")
        embedding = payload.get("Embedding")
        if (
            entry.change_type in ("INSERT", "UPDATE")
            and chunk_id
            and document_id
            and embedding
        ):
            await _upsert_milvus_chunk(milvus_client, chunk_id, document_id, embedding)
        elif entry.change_type == "DELETE" and chunk_id:
            await _delete_milvus_chunk(milvus_client, chunk_id)
        else:
            logger.warning("Missing or invalid data for Milvus operation: %s", payload)

    async def handle_agent_logs():
        log_id = payload.get("LogID")
        agent_id = payload.get("AgentID")
        if entry.change_type == "INSERT" and log_id and agent_id:
            await _neo4j_session_run(
                neo4j_driver,
                "MERGE (a:Agent {id: $agent_id})",
                agent_id=agent_id,
            )
            await _neo4j_session_run(
                neo4j_driver,
                "MERGE (l:AgentLog {id: $log_id, agent_id: $agent_id})",
                log_id=log_id,
                agent_id=agent_id,
            )
            logger.info("Deleted AgentLog %s from Neo4j.", log_id)

    async def handle_agents():
        agent_id = payload.get("AgentID")
        name = payload.get("Name")
        role = payload.get("Role")
        status = payload.get("Status")
        if entry.change_type == "INSERT" and agent_id:
            await _neo4j_session_run(
                neo4j_driver,
                (
                    "MERGE (a:Agent {id: $agent_id, name: $name, "
                    "role: $role, status: $status})"
                ),
                agent_id=agent_id,
                name=name,
                role=role,
                status=status,
            )
            logger.info("Inserted Agent %s into Neo4j.", agent_id)
        elif entry.change_type == "DELETE" and agent_id:
            await _neo4j_session_run(
                neo4j_driver,
                "MATCH (a:Agent {id: $agent_id}) DETACH DELETE a",
                agent_id=agent_id,
            )
            logger.info("Deleted Agent %s from Neo4j.", agent_id)

    async def handle_documents():
        document_id = payload.get("DocumentID")
        title = payload.get("Title")
        source_url = payload.get("SourceURL")
        if entry.change_type == "INSERT" and document_id:
            await _neo4j_session_run(
                neo4j_driver,
                (
                    "MERGE (d:Document {id: $document_id, title: $title, "
                    "source_url: $source_url})"
                ),
                document_id=document_id,
                title=title,
                source_url=source_url,
            )
            logger.info("Inserted Document %s into Neo4j.", document_id)
        elif entry.change_type == "DELETE" and document_id:
            await _neo4j_session_run(
                neo4j_driver,
                "MATCH (d:Document {id: $document_id}) DETACH DELETE d",
                document_id=document_id,
            )
            logger.info("Deleted Document %s from Neo4j.", document_id)

    handlers = {
        SOURCE_TABLE_CHUNKS: handle_chunks,
        SOURCE_TABLE_AGENT_LOGS: handle_agent_logs,
        SOURCE_TABLE_AGENTS: handle_agents,
        SOURCE_TABLE_DOCUMENTS: handle_documents,
    }
    handler = handlers.get(entry.source_table)
    if handler:
        await handler()


def all_connections_ready(sql_conn, milvus_client, neo4j_driver):
    return (
        sql_conn is not None and milvus_client is not None and neo4j_driver is not None
    )


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
        try:
            async with get_sql_server_connection() as sql_conn:
                milvus_client = await get_milvus_client()
                neo4j_driver = await get_neo4j_driver()
                if all_connections_ready(sql_conn, milvus_client, neo4j_driver):
                    logger.info("Successfully re-established database connections.")
                    break
        except Exception as e:
            logger.error(f"Failed to connect to databases on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                logger.info("Retrying in 10 seconds.")
                await asyncio.sleep(10)
            else:
                logger.error("Max retries reached. Failed to establish database connections.")
                return


# --- Entry Point ---
if __name__ == "__main__":
    logger.info("Starting CDC Consumer...")
    asyncio.run(run_cdc_consumer())
