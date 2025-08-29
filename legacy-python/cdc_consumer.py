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
        """Sync agent data to Milvus by creating embeddings of agent text data."""
        logger.info(
            f"Syncing agent {agent_id} to Milvus (Operation: {operation_type})..."
        )
        try:
            if operation_type in ["INSERT", "UPDATE"] and payload:
                # Extract text content from agent data for embedding
                text_content = self._extract_agent_text_content(payload)
                if not text_content:
                    logger.debug(f"No text content found for agent {agent_id}, skipping Milvus sync")
                    return
                
                # Generate embedding
                embedding = await get_embedding(text_content)
                if not embedding:
                    logger.warning(f"Failed to generate embedding for agent {agent_id}")
                    return
                
                async with milvus_connection_context() as milvus_client:
                    if milvus_client:
                        # Prepare data for insertion
                        data = [{
                            "id": f"agent_{agent_id}",
                            "document_id": f"agent_{agent_id}",
                            "text": text_content[:1000],  # Limit text length
                            "embedding": embedding,
                            "metadata": json.dumps({
                                "type": "agent_data",
                                "agent_id": agent_id,
                                "operation": operation_type,
                                "timestamp": payload.get("timestamp") if payload else None
                            })
                        }]
                        
                        # Insert/update in Milvus
                        milvus_client.upsert(collection_name="default_collection", data=data)
                        logger.info(f"Agent {agent_id} synced to Milvus successfully")
                    else:
                        logger.error("Milvus client not available")
        except Exception as e:
            logger.error(f"Error syncing agent {agent_id} to Milvus: {e}\n{traceback.format_exc()}")

    async def _delete_agent_from_milvus(self, agent_id):
        """Delete agent data from Milvus."""
        logger.info(f"Deleting agent {agent_id} from Milvus...")
        try:
            async with milvus_connection_context() as milvus_client:
                if milvus_client:
                    # Delete by ID
                    milvus_client.delete(
                        collection_name="default_collection",
                        filter=f"id == 'agent_{agent_id}'"
                    )
                    logger.info(f"Agent {agent_id} deleted from Milvus successfully")
                else:
                    logger.error("Milvus client not available for deletion")
        except Exception as e:
            logger.error(f"Error deleting agent {agent_id} from Milvus: {e}\n{traceback.format_exc()}")

    def _extract_agent_text_content(self, payload):
        """Extract meaningful text content from agent payload for embedding."""
        if not payload or not isinstance(payload, dict):
            return None
            
        text_parts = []
        
        # Extract common agent fields
        if "name" in payload:
            text_parts.append(f"Name: {payload['name']}")
        if "role" in payload:
            text_parts.append(f"Role: {payload['role']}")
        if "description" in payload:
            text_parts.append(f"Description: {payload['description']}")
        if "capabilities" in payload:
            text_parts.append(f"Capabilities: {payload['capabilities']}")
        if "status" in payload:
            text_parts.append(f"Status: {payload['status']}")
            
        # Extract BDI state if present
        if "BDIState" in payload:
            try:
                bdi_data = json.loads(payload["BDIState"]) if isinstance(payload["BDIState"], str) else payload["BDIState"]
                if "beliefs" in bdi_data:
                    beliefs_summary = str(bdi_data["beliefs"])[:200]
                    text_parts.append(f"Beliefs: {beliefs_summary}")
            except Exception:
                pass
        
        return " | ".join(text_parts) if text_parts else None

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
                        # Process document into chunks and sync to Milvus
                        await self._sync_document_chunks_to_milvus(document_id, payload, operation_type)
                    elif operation_type == "DELETE":
                        # Delete all chunks associated with this document from Milvus
                        await self._delete_document_chunks_from_milvus(document_id)
                except Exception as e:
                    logger.error(
                        f"Error syncing document {document_id} to Milvus: {e}\n{traceback.format_exc()}"
                    )

    async def _sync_document_chunks_to_milvus(self, document_id, payload, operation_type):
        """Process document into chunks and sync to Milvus."""
        logger.info(f"Syncing document {document_id} chunks to Milvus (Operation: {operation_type})...")
        
        try:
            # Extract document content
            content = payload.get("Content", "")
            title = payload.get("Title", f"Document {document_id}")
            source_url = payload.get("SourceURL", "")
            
            if not content:
                logger.warning(f"Document {document_id} has no content to process")
                return
            
            # Import chunking and embedding functionality
            from services.text_processing import chunk_text
            from services.embedding_service import EmbeddingService
            
            # Split document into chunks
            chunks = chunk_text(content, chunk_size=512, overlap=50)
            logger.info(f"Document {document_id} split into {len(chunks)} chunks")
            
            # Get embeddings for chunks
            embedding_service = EmbeddingService()
            
            # Prepare chunk data for Milvus
            chunk_data = []
            for i, chunk in enumerate(chunks):
                try:
                    # Generate embedding for chunk
                    embedding = await embedding_service.get_embedding(chunk)
                    
                    chunk_data.append({
                        "id": f"{document_id}_{i}",
                        "document_id": int(document_id),
                        "chunk_index": i,
                        "text": chunk,
                        "title": title,
                        "source_url": source_url,
                        "embedding": embedding
                    })
                except Exception as e:
                    logger.error(f"Failed to generate embedding for chunk {i} of document {document_id}: {e}")
                    continue
            
            if not chunk_data:
                logger.warning(f"No valid chunks generated for document {document_id}")
                return
            
            # Insert chunks into Milvus
            async with milvus_connection_context() as milvus_client:
                if milvus_client:
                    try:
                        # For UPDATE operations, delete existing chunks first
                        if operation_type == "UPDATE":
                            await self._delete_document_chunks_from_milvus(document_id)
                        
                        # Insert new chunks
                        from config import MILVUS_COLLECTION
                        
                        # Prepare data for Milvus insert
                        ids = [chunk["id"] for chunk in chunk_data]
                        document_ids = [chunk["document_id"] for chunk in chunk_data]
                        chunk_indices = [chunk["chunk_index"] for chunk in chunk_data]
                        texts = [chunk["text"] for chunk in chunk_data]
                        titles = [chunk["title"] for chunk in chunk_data]
                        source_urls = [chunk["source_url"] for chunk in chunk_data]
                        embeddings = [chunk["embedding"] for chunk in chunk_data]
                        
                        insert_data = [
                            ids,
                            document_ids,
                            chunk_indices,
                            texts,
                            titles,
                            source_urls,
                            embeddings
                        ]
                        
                        result = await asyncio.to_thread(
                            milvus_client.insert,
                            collection_name=MILVUS_COLLECTION,
                            data=insert_data
                        )
                        
                        logger.info(f"Successfully inserted {len(chunk_data)} chunks for document {document_id} into Milvus")
                        
                    except Exception as e:
                        logger.error(f"Failed to insert chunks into Milvus for document {document_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing document {document_id} for Milvus sync: {e}\n{traceback.format_exc()}")

    async def _delete_document_chunks_from_milvus(self, document_id):
        """Delete all chunks associated with a document from Milvus."""
        logger.info(f"Deleting chunks for document {document_id} from Milvus...")
        
        async with milvus_connection_context() as milvus_client:
            if milvus_client:
                try:
                    from config import MILVUS_COLLECTION
                    
                    # Delete all chunks with matching document_id
                    expr = f"document_id == {document_id}"
                    
                    result = await asyncio.to_thread(
                        milvus_client.delete,
                        collection_name=MILVUS_COLLECTION,
                        expr=expr
                    )
                    
                    logger.info(f"Successfully deleted chunks for document {document_id} from Milvus")
                    
                except Exception as e:
                    logger.error(f"Failed to delete chunks for document {document_id} from Milvus: {e}")

    async def _delete_document_from_milvus(self, document_id):
        """Legacy method - redirects to chunk deletion."""
        await self._delete_document_chunks_from_milvus(document_id)

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
