import asyncio
import json
import logging
import traceback
from typing import Optional

import pyodbc
from neo4j import Driver, GraphDatabase
from pymilvus import MilvusClient, MilvusException

from config import (
    MILVUS_HOST,
    MILVUS_PASSWORD,
    MILVUS_PORT,
    MILVUS_USER,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USER,
    SQL_SERVER_CONNECTION_STRING,
)
from query_utils import (
    AGENTLOGS_SELECT_EVALUATION,
    AGENTLOGS_UPDATE_EVALUATION,
    execute_sql_query,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def get_sql_server_connection():
    """
    Async connect to SQL Server database using credentials from env vars ONLY.
    """
    loop = asyncio.get_event_loop()
    conn = None
    try:
        conn = await loop.run_in_executor(
            None, pyodbc.connect, SQL_SERVER_CONNECTION_STRING
        )
        return conn
    except pyodbc.Error as exc:
        logger.error("SQL Server connection error: %s", exc)
        return None


async def get_milvus_client() -> Optional[MilvusClient]:
    """
    Connect to Milvus database using credentials from env vars.
    """
    try:
        uri = f"http://{MILVUS_USER}:{MILVUS_PASSWORD}@{MILVUS_HOST}:{MILVUS_PORT}"
        logger.info("Connecting to Milvus at %s...", uri)
        client = await asyncio.to_thread(
            MilvusClient, uri=uri
        )  # Run blocking call in a thread
        logger.info("Successfully connected to Milvus.")
        return client
    except MilvusException as exc:
        logger.error("Milvus connection error: %s\n%s", exc, traceback.format_exc())
        return None


async def get_neo4j_driver() -> Optional[Driver]:
    """
    Connect to Neo4j database using credentials from env vars ONLY.
    """
    driver = None
    try:
        logger.info("Connecting to Neo4j at %s...", NEO4J_URI)
        driver = await asyncio.to_thread(
            GraphDatabase.driver, NEO4J_URI, auth=(str(NEO4J_USER), str(NEO4J_PASSWORD))
        )
        return driver
    except Exception as exc:
        logger.error("Neo4j connection error: %s", exc)
        return None


async def update_agent_log_evaluation(cursor, log_id: int, new_entry: dict) -> bool:
    """
    Retrieves existing Evaluation JSON from AgentLogs, appends a new entry,
    and updates the column. Assumes an active cursor is provided.
    """
    try:
        # Execute fetchone in a thread
        result = await asyncio.to_thread(
            cursor.execute,
            AGENTLOGS_SELECT_EVALUATION,
            (log_id,),
        )
        result = await asyncio.to_thread(cursor.fetchone)

        if not result:
            logger.warning("LogID %s not found for evaluation update.", log_id)
            return False

        existing_evaluation = []
        if result[0]:
            try:
                existing_evaluation = json.loads(result[0])
            except json.JSONDecodeError:
                logger.warning(
                    "Existing evaluation for LogID %s is not valid JSON. Initializing as empty list.",
                    log_id,
                )
            if not isinstance(existing_evaluation, list):
                existing_evaluation = []

        existing_evaluation.append(new_entry)

        # Execute update in a thread
        await asyncio.to_thread(
            execute_sql_query,
            cursor,
            AGENTLOGS_UPDATE_EVALUATION,
            (json.dumps(existing_evaluation), log_id),
        )
        return True
    except (RuntimeError, ValueError, TypeError) as exc:
        logger.error(
            "Failed to update AgentLogs Evaluation for LogID %s: %s",
            log_id,
            exc,
        )
        return False


async def insert_document(
    cursor,
    document_id: str,
    text: str,
    metadata: dict = None,
) -> None:
    """
    Assumes an active cursor is provided.
    """
    loop = asyncio.get_event_loop()
    metadata_json = json.dumps(metadata) if metadata else None
    await loop.run_in_executor(
        None,
        cursor.execute,
        "INSERT INTO Documents (DocumentID, Text, Metadata) VALUES (?, ?, ?)",
        document_id,
        text,
        metadata_json,
    )


async def insert_chunk(
    cursor,
    chunk_id: str,
    document_id: str,
    text: str,
    embedding: str,
    model_name: str,
    model_version: str,
) -> None:
    """
    Inserts a new chunk into the Chunks table.
    Assumes an active cursor is provided.
    """
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        cursor.execute,
        "INSERT INTO Chunks (ChunkID, DocumentID, Text, Embedding, ModelName, "
        "ModelVersion) VALUES (?, ?, ?, ?, ?, ?)",
        chunk_id,
        document_id,
        text,
        embedding,
        model_name,
        model_version,
    )
