import asyncio
import logging
import json
import traceback
from pathlib import Path

from db_connectors import get_sql_server_connection
from query_utils import execute_sql_query, sql_server_connection_context
from rag_pipeline import get_embedding
from utils import milvus_connection_context, neo4j_connection_context

logger = logging.getLogger(__name__)


class CDCConsumer:
    def __init__(
        self,
        state_file="cdc_state.txt",
        poll_interval=5,
        max_retries=5,
        initial_backoff=1,
    ):
        self.state_file = Path(state_file)
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.last_processed_id = self._load_last_processed_id()
        logger.info(
            f"CDC Consumer initialized. Last processed ChangeLog ID: {self.last_processed_id}"
        )

    def _load_last_processed_id(self):
        """Loads the last successfully processed ChangeLog.ID from a file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    content = f.read().strip()
                    if content:
                        return int(content)
            except Exception as e:
                logger.error(f"Error loading CDC state from {self.state_file}: {e}")
            try:
                with open(self.state_file, "r") as f:
                    return int(f.read())
            except Exception:
                # Try backup file
                try:
                    with open(self.state_file + ".bak", "r") as f:
                        return int(f.read())
                except Exception:
                    return 0

    def _save_last_processed_id(self, change_id):
        """Saves the last successfully processed ChangeLog.ID to a file."""
        try:
            with open(self.state_file, "w") as f:
                f.write(str(change_id))
            self.last_processed_id = change_id
        except Exception as e:
            logger.error(f"Error saving CDC state to {self.state_file}: {e}")
            # Write backup
            with open(self.state_file + ".bak", "w") as f:
                f.write(str(change_id))

    async def _execute_with_retry(self, func, *args, **kwargs):
        """Executes an async function with exponential backoff retry strategy."""
        retries = 0
        while retries < self.max_retries:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                delay = self.initial_backoff * (2**retries)
                logger.warning(
                    f"Attempt {retries + 1}/{self.max_retries} failed for {func.__name__}: {e}. Retrying in {delay} seconds..."
                )
                retries += 1
                await asyncio.sleep(delay)
        logger.error(
            f"Function {func.__name__} failed after {self.max_retries} retries."
        )
        return None

    async def _sync_agent_to_milvus(self, agent_id, payload, operation_type):
        logger.info(
            f"Syncing agent {agent_id} to Milvus (Operation: {operation_type})..."
        )
        # Milvus typically stores document/chunk embeddings, not raw agent data.
        # This is a placeholder for potential future use if agent-related text needs embedding.
        pass

    async def _delete_agent_from_milvus(self, agent_id):
        logger.info(f"Deleting agent {agent_id} from Milvus...")
        pass

    async def _sync_agent_to_neo4j(self, agent_id, payload, operation_type):
        logger.info(
            f"Syncing agent {agent_id} to Neo4j (Operation: {operation_type})..."
        )
        async with neo4j_connection_context() as neo4j_driver:
            if neo4j_driver:
                try:
                    name = payload.get("Name")
                    role = payload.get("Role")
                    status = payload.get("Status")

                    if operation_type == "INSERT" or operation_type == "UPDATE":
                        query = (
                            "MERGE (a:Agent {agent_id: $agent_id}) "
                            "SET a.name = $name, a.role = $role, a.status = $status"
                        )
                        await asyncio.to_thread(
                            neo4j_driver.session().run,
                            query,
                            agent_id=agent_id,
                            name=name,
                            role=role,
                            status=status,
                        )
                        logger.info(f"Agent {agent_id} upserted to Neo4j.")
                    elif operation_type == "DELETE":
                        query = "MATCH (a:Agent {agent_id: $agent_id}) DETACH DELETE a"
                        await asyncio.to_thread(
                            neo4j_driver.session().run, query, agent_id=agent_id
                        )
                        logger.info(f"Agent {agent_id} deleted from Neo4j.")
                except Exception as e:
                    logger.error(
                        f"Error syncing agent {agent_id} to Neo4j: {e}\n{traceback.format_exc()}"
                    )

    async def _delete_agent_from_neo4j(self, agent_id):
        logger.info(f"Deleting agent {agent_id} from Neo4j...")
        async with neo4j_connection_context() as neo4j_driver:
            if neo4j_driver:
                try:
                    query = "MATCH (a:Agent {agent_id: $agent_id}) DETACH DELETE a"
                    await asyncio.to_thread(
                        neo4j_driver.session().run, query, agent_id=agent_id
                    )
                    logger.info(f"Agent {agent_id} deleted from Neo4j.")
                except Exception as e:
                    logger.error(
                        f"Error deleting agent {agent_id} from Neo4j: {e}\n{traceback.format_exc()}"
                    )

    async def _sync_document_to_milvus(self, document_id, payload, operation_type):
        logger.info(
            f"Syncing document {document_id} to Milvus (Operation: {operation_type})..."
        )
        async with milvus_connection_context() as milvus_client:
            if milvus_client:
                try:
                    if operation_type == "INSERT" or operation_type == "UPDATE":
                        # Milvus stores chunks, not full documents directly. This is a placeholder.
                        # Actual document content would be processed into chunks and then synced.
                        logger.warning(
                            f"Document {document_id} change detected. Milvus sync for full documents is a placeholder. Chunks should be synced separately."
                        )
                    elif operation_type == "DELETE":
                        # When a document is deleted, its associated chunks should also be deleted from Milvus.
                        # This requires querying for chunks related to this document_id and deleting them.
                        logger.info(
                            f"Document {document_id} deleted. Placeholder for deleting associated chunks from Milvus."
                        )
                except Exception as e:
                    logger.error(
                        f"Error syncing document {document_id} to Milvus: {e}\n{traceback.format_exc()}"
                    )

    async def _delete_document_from_milvus(self, document_id):
        logger.info(f"Deleting document {document_id} from Milvus...")
        async with milvus_connection_context() as milvus_client:
            if milvus_client:
                try:
                    # Placeholder for deleting all chunks associated with this document_id
                    logger.info(
                        f"Placeholder: Deleting all chunks for document {document_id} from Milvus."
                    )
                except Exception as e:
                    logger.error(
                        f"Error deleting document {document_id} from Milvus: {e}\n{traceback.format_exc()}"
                    )

    async def _sync_document_to_neo4j(self, document_id, payload, operation_type):
        logger.info(
            f"Syncing document {document_id} to Neo4j (Operation: {operation_type})..."
        )
        async with neo4j_connection_context() as neo4j_driver:
            if neo4j_driver:
                try:
                    title = payload.get("Title")
                    source_url = payload.get("SourceURL")

                    if operation_type == "INSERT" or operation_type == "UPDATE":
                        query = (
                            "MERGE (d:Document {document_id: $document_id}) "
                            "SET d.title = $title, d.source_url = $source_url"
                        )
                        await asyncio.to_thread(
                            neo4j_driver.session().run,
                            query,
                            document_id=document_id,
                            title=title,
                            source_url=source_url,
                        )
                        logger.info(f"Document {document_id} upserted to Neo4j.")
                    elif operation_type == "DELETE":
                        query = "MATCH (d:Document {document_id: $document_id}) DETACH DELETE d"
                        await asyncio.to_thread(
                            neo4j_driver.session().run, query, document_id=document_id
                        )
                        logger.info(f"Document {document_id} deleted from Neo4j.")
                except Exception as e:
                    logger.error(
                        f"Error syncing document {document_id} to Neo4j: {e}\n{traceback.format_exc()}"
                    )

    async def _delete_document_from_neo4j(self, document_id):
        logger.info(f"Deleting document {document_id} from Neo4j...")
        async with neo4j_connection_context() as neo4j_driver:
            if neo4j_driver:
                try:
                    query = (
                        "MATCH (d:Document {document_id: $document_id}) DETACH DELETE d"
                    )
                    await asyncio.to_thread(
                        neo4j_driver.session().run, query, document_id=document_id
                    )
                    logger.info(f"Document {document_id} deleted from Neo4j.")
                except Exception as e:
                    logger.error(
                        f"Error deleting document {document_id} from Neo4j: {e}\n{traceback.format_exc()}"
                    )

    async def _sync_chunk_to_milvus(self, chunk_id, payload, operation_type):
        logger.info(
            f"Syncing chunk {chunk_id} to Milvus (Operation: {operation_type})..."
        )
        async with milvus_connection_context() as milvus_client:
            if milvus_client:
                try:
                    if operation_type == "INSERT" or operation_type == "UPDATE":
                        text_content = payload.get("Text")
                        document_id = payload.get("DocumentID")
                        model_name = payload.get("ModelName")
                        model_version = payload.get("ModelVersion")

                        if text_content:
                            embedding = await get_embedding(
                                text_content
                            )  # Assuming get_embedding is an async function
                            if embedding:
                                data = {
                                    "id": str(chunk_id),
                                    "embedding": embedding,
                                    "document_id": str(document_id),
                                    "text": text_content,
                                    "model_name": model_name,
                                    "model_version": model_version,
                                }
                                milvus_client.upsert(
                                    collection_name="rag_collection",  # Assuming a default collection name
                                    data=[data],
                                )
                                logger.info(f"Chunk {chunk_id} upserted to Milvus.")
                            else:
                                logger.error(
                                    f"Failed to generate embedding for chunk {chunk_id}."
                                )
                        else:
                            logger.warning(
                                f"No text content found in payload for chunk {chunk_id} to sync to Milvus."
                            )
                    elif operation_type == "DELETE":
                        milvus_client.delete(
                            collection_name="rag_collection", ids=[str(chunk_id)]
                        )
                        logger.info(f"Chunk {chunk_id} deleted from Milvus.")
                except Exception as e:
                    logger.error(
                        f"Error syncing chunk {chunk_id} to Milvus: {e}\n{traceback.format_exc()}"
                    )

    async def _delete_chunk_from_milvus(self, chunk_id):
        logger.info(f"Deleting chunk {chunk_id} from Milvus...")
        async with milvus_connection_context() as milvus_client:
            if milvus_client:
                try:
                    milvus_client.delete(
                        collection_name="rag_collection", ids=[str(chunk_id)]
                    )
                    logger.info(f"Chunk {chunk_id} deleted from Milvus.")
                except Exception as e:
                    logger.error(
                        f"Error deleting chunk {chunk_id} from Milvus: {e}\n{traceback.format_exc()}"
                    )

    async def _sync_chunk_to_neo4j(self, chunk_id, payload, operation_type):
        logger.info(
            f"Syncing chunk {chunk_id} to Neo4j (Operation: {operation_type})..."
        )
        async with neo4j_connection_context() as neo4j_driver:
            if neo4j_driver:
                try:
                    text = payload.get("Text")
                    document_id = payload.get("DocumentID")

                    if operation_type == "INSERT" or operation_type == "UPDATE":
                        query = (
                            "MERGE (c:Chunk {chunk_id: $chunk_id}) "
                            "SET c.text = $text, c.model_name = $model_name, c.model_version = $model_version "
                            "MERGE (d:Document {document_id: $document_id}) "
                            "MERGE (d)-[:HAS_CHUNK]->(c)"
                        )
                        await asyncio.to_thread(
                            neo4j_driver.session().run,
                            query,
                            chunk_id=chunk_id,
                            text=text,
                            document_id=document_id,
                            model_name=payload.get("ModelName"),
                            model_version=payload.get("ModelVersion"),
                        )
                        logger.info(f"Chunk {chunk_id} upserted to Neo4j.")
                    elif operation_type == "DELETE":
                        query = "MATCH (c:Chunk {chunk_id: $chunk_id}) DETACH DELETE c"
                        await asyncio.to_thread(
                            neo4j_driver.session().run, query, chunk_id=chunk_id
                        )
                        logger.info(f"Chunk {chunk_id} deleted from Neo4j.")
                except Exception as e:
                    logger.error(
                        f"Error syncing chunk {chunk_id} to Neo4j: {e}\n{traceback.format_exc()}"
                    )

    async def _delete_chunk_from_neo4j(self, chunk_id):
        logger.info(f"Deleting chunk {chunk_id} from Neo4j...")
        async with neo4j_connection_context() as neo4j_driver:
            if neo4j_driver:
                try:
                    query = "MATCH (c:Chunk {chunk_id: $chunk_id}) DETACH DELETE c"
                    await asyncio.to_thread(
                        neo4j_driver.session().run, query, chunk_id=chunk_id
                    )
                    logger.info(f"Chunk {chunk_id} deleted from Neo4j.")
                except Exception as e:
                    logger.error(
                        f"Error deleting chunk {chunk_id} from Neo4j: {e}\n{traceback.format_exc()}"
                    )

    async def _process_change(self, change):
        change_id, source_table, source_id, change_type, payload_json = change
        logger.info(
            f"Processing change: ID={change_id}, Table={source_table}, "
            f"SourceID={source_id}, Type={change_type}"
        )
        try:
            payload = json.loads(payload_json)
        except json.JSONDecodeError:
            logger.error(
                f"Failed to decode JSON payload for ChangeLog ID {change_id}. Skipping."
            )
            return

        sync_tasks = []
        if source_table == "Agents":
            if change_type == "INSERT" or change_type == "UPDATE":
                sync_tasks.append(
                    self._execute_with_retry(
                        self._sync_agent_to_neo4j, source_id, payload, change_type
                    )
                )
            elif change_type == "DELETE":
                sync_tasks.append(
                    self._execute_with_retry(self._delete_agent_from_neo4j, source_id)
                )
        elif source_table == "Documents":
            if change_type == "INSERT" or change_type == "UPDATE":
                sync_tasks.append(
                    self._execute_with_retry(
                        self._sync_document_to_milvus, source_id, payload, change_type
                    )
                )
                sync_tasks.append(
                    self._execute_with_retry(
                        self._sync_document_to_neo4j, source_id, payload, change_type
                    )
                )
            elif change_type == "DELETE":
                sync_tasks.append(
                    self._execute_with_retry(
                        self._delete_document_from_milvus, source_id
                    )
                )
                sync_tasks.append(
                    self._execute_with_retry(
                        self._delete_document_from_neo4j, source_id
                    )
                )
        elif source_table == "Chunks":
            if change_type == "INSERT" or change_type == "UPDATE":
                sync_tasks.append(
                    self._execute_with_retry(
                        self._sync_chunk_to_milvus, source_id, payload, change_type
                    )
                )
                sync_tasks.append(
                    self._execute_with_retry(
                        self._sync_chunk_to_neo4j, source_id, payload, change_type
                    )
                )
            elif change_type == "DELETE":
                sync_tasks.append(
                    self._execute_with_retry(self._delete_chunk_from_milvus, source_id)
                )
                sync_tasks.append(
                    self._execute_with_retry(self._delete_chunk_from_neo4j, source_id)
                )
        # Add other source tables as needed

        if sync_tasks:
            await asyncio.gather(*sync_tasks)

    async def run(self):
        """Main method to run the CDC consumer in an infinite loop."""
        while True:
            try:
                sql_server_conn = get_sql_server_connection()
                async with sql_server_connection_context(sql_server_conn) as (
                    conn,
                    cursor,
                ):
                    if not conn:
                        logger.error(
                            "SQL Server connection is not available. Retrying..."
                        )
                        await asyncio.sleep(self.poll_interval)
                        continue

                    # Query ChangeLog for new entries
                    query = "SELECT ChangeID, SourceTable, SourceID, ChangeType, Payload FROM ChangeLog WHERE ChangeID > ? ORDER BY ChangeID ASC"
                    await asyncio.to_thread(
                        execute_sql_query, cursor, query, (self.last_processed_id,)
                    )
                    changes = await asyncio.to_thread(cursor.fetchall)

                    if changes:
                        logger.info(f"Found {len(changes)} new changes to process.")
                        for change in changes:
                            change_id = change[0]  # ChangeID is the first element
                            await self._process_change(change)
                            self._save_last_processed_id(change_id)
                        await asyncio.to_thread(conn.commit)
                    else:
                        logger.info("No new changes found. Waiting...")

            except Exception as e:
                logger.error(
                    f"Error in CDC consumer main loop: {e}\n{traceback.format_exc()}"
                )

            await asyncio.sleep(self.poll_interval)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    consumer = CDCConsumer()
    try:
        asyncio.run(consumer.run())
    except KeyboardInterrupt:
        logger.info("CDC Consumer stopped by user.")
