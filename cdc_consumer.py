import asyncio
import logging
import traceback
from datetime import datetime

from db_connectors import get_sql_server_connection
from query_utils import execute_sql_query, sql_server_connection_context
from utils import milvus_connection_context, neo4j_connection_context

logger = logging.getLogger(__name__)


async def poll_changelog_and_sync():
    """Polls the ChangeLog table in SQL Server and synchronizes changes to Milvus and Neo4j."""
    try:
        sql_server_conn = get_sql_server_connection()
        async with sql_server_connection_context(sql_server_conn) as (conn, cursor):
            if not conn:
                logger.error("SQL Server connection is not available.")
                return

            # Get the last synchronized timestamp
            last_sync_timestamp = await get_last_sync_timestamp(cursor)

            # Query ChangeLog for new entries
            query = "SELECT * FROM ChangeLog WHERE ChangeTimestamp > ? ORDER BY ChangeTimestamp ASC"
            await asyncio.to_thread(execute_sql_query, cursor, query, (last_sync_timestamp,))
            changes = await asyncio.to_thread(cursor.fetchall)

            for change in changes:
                change_id, entity_type, entity_id, operation_type, change_timestamp, payload = change
                logger.info(
                    f"Processing change: ID={change_id}, Type={entity_type}, "
                    f"Operation={operation_type}, Timestamp={change_timestamp}"
                )

                # Synchronize to Milvus and Neo4j based on entity_type and operation_type
                if entity_type == "Document":
                    if operation_type == "INSERT" or operation_type == "UPDATE":
                        await sync_document_to_milvus(entity_id, payload)
                        await sync_document_to_neo4j(entity_id, payload)
                    elif operation_type == "DELETE":
                        await delete_document_from_milvus(entity_id)
                        await delete_document_from_neo4j(entity_id)
                # Add other entity types as needed

                # Update last synchronized timestamp
                await update_last_sync_timestamp(cursor, change_timestamp)

            await asyncio.to_thread(conn.commit)

    except Exception as e:
        logger.error(f"Error in CDC consumer: {e}\n{traceback.format_exc()}")


async def get_last_sync_timestamp(cursor):
    """Retrieves the last synchronized timestamp from a configuration or state table."""
    # This is a placeholder. In a real application, you'd store this in a persistent way.
    # For now, we'll use a very old timestamp to ensure all changes are processed on first run.
    return datetime.min


async def update_last_sync_timestamp(cursor, timestamp):
    """Updates the last synchronized timestamp."""
    # Placeholder for updating the timestamp in a persistent store.
    logger.info(f"Updated last sync timestamp to: {timestamp}")


async def sync_document_to_milvus(document_id, payload):
    """Synchronizes document changes to Milvus."""
    logger.info(f"Syncing document {document_id} to Milvus with payload: {payload}")
    # Implement Milvus upsert logic here
    async with milvus_connection_context() as milvus_client:
        if milvus_client:
            # Example: insert or update document in Milvus
            # This would involve generating an embedding for the payload and inserting it
            # For now, just a log
            logger.info(f"Document {document_id} synced to Milvus.")


async def delete_document_from_milvus(document_id):
    """Deletes document from Milvus."""
    logger.info(f"Deleting document {document_id} from Milvus.")
    # Implement Milvus delete logic here
    async with milvus_connection_context() as milvus_client:
        if milvus_client:
            # Example: delete document from Milvus
            # For now, just a log
            logger.info(f"Document {document_id} deleted from Milvus.")


async def sync_document_to_neo4j(document_id, payload):
    """Synchronizes document changes to Neo4j."""
    logger.info(f"Syncing document {document_id} to Neo4j with payload: {payload}")
    # Implement Neo4j upsert logic here
    async with neo4j_connection_context() as neo4j_driver:
        if neo4j_driver:
            # Example: create or update node in Neo4j
            # For now, just a log
            logger.info(f"Document {document_id} synced to Neo4j.")


async def delete_document_from_neo4j(document_id):
    """Deletes document from Neo4j."""
    logger.info(f"Deleting document {document_id} from Neo4j.")
    # Implement Neo4j delete logic here
    async with neo4j_connection_context() as neo4j_driver:
        if neo4j_driver:
            # Example: delete node from Neo4j
            # For now, just a log
            logger.info(f"Document {document_id} deleted from Neo4j.")


async def main():
    while True:
        await poll_changelog_and_sync()
        await asyncio.sleep(5)  # Poll every 5 seconds


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
