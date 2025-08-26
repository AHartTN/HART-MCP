import asyncio
import logging
import os
import traceback
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import List

import PyPDF2
import pytesseract
import speech_recognition as sr
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from PIL import Image

from db_connectors import (
    get_milvus_client,
    get_neo4j_driver,
    get_sql_server_connection,
)

logger = logging.getLogger(__name__)


@asynccontextmanager # Changed to asynccontextmanager
async def neo4j_connection_context(): # Changed to async def
    """
    Asynchronous context manager for Neo4j driver.
    Ensures the driver is properly closed.
    """
    from db_connectors import get_neo4j_driver

    driver = None
    try:
        driver = await get_neo4j_driver() # Await the async function
        yield driver
    finally:
        if driver:
            # Neo4j driver.close() is synchronous, run in a thread
            await asyncio.to_thread(driver.close)


@asynccontextmanager
async def sql_connection_context():
    """
    Asynchronous context manager for SQL Server connection and cursor.
    Ensures connection and cursor are properly closed.
    """
    conn = None
    cursor = None
    try:
        conn = await get_sql_server_connection()
        if conn:
            cursor = await asyncio.to_thread(conn.cursor)  # Run cursor() in a thread
        yield conn, cursor
    finally:
        if cursor:
            await asyncio.to_thread(cursor.close)  # Run close() in a thread
        if conn:
            await asyncio.to_thread(conn.close)  # Run close() in a thread


"""
This module provides utility functions for the MCP server.
"""


logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "mp3", "wav"}


@asynccontextmanager
async def milvus_connection_context():
    """
    Asynchronous context manager for Milvus client.
    Ensures the client is properly closed.
    """
    client = None
    try:
        from db_connectors import get_milvus_client

        client = await get_milvus_client()  # Await the async function
        yield client
    finally:
        if client:
            try:
                # MilvusClient.close() is synchronous, run in a thread
                await asyncio.to_thread(client.close)
            except Exception as e:
                logger.error("Error closing Milvus client: %s", e)


def get_secret_from_keyvault(
    secret_name: str, vault_url: str | None = None
) -> str | None:
    """
    Retrieve a secret from Azure Key Vault using default credentials.
    """
    vault_url = vault_url or os.getenv("AZURE_KEYVAULT_URL")
    if not vault_url:
        logger.error("Key Vault URL not set.")
        return None
    try:
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_url, credential=credential)
        secret = client.get_secret(secret_name)
        return secret.value
    except Exception as e:
        logger.error(
            "Failed to retrieve secret '%s' from Key Vault: %s", secret_name, e
        )
        return None


def allowed_file(filename: str) -> bool:
    """
    Check if the file extension is allowed.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text(file_path: str, file_extension: str) -> str | None:
    """
    Extract text from a file based on its extension.
    """
    try:
        if file_extension == "txt":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        elif file_extension == "pdf":
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() for page in reader.pages)
        elif file_extension in {"png", "jpg", "jpeg"}:
            return pytesseract.image_to_string(Image.open(file_path))
        elif file_extension in {"mp3", "wav"}:
            recognizer = sr.Recognizer()
            with sr.AudioFile(file_path) as source:
                audio = recognizer.record(source)
            return recognizer.recognize_google(audio)
        else:
            logger.warning(
                "Unsupported file type for text extraction: %s", file_extension
            )
            return None
    except Exception as e:
        logger.error("Failed to extract text from %s: %s", file_path, e)
        return None


async def update_agent_log_feedback(
    log_id: int, feedback_text: str, rating: int | None, feedback_type: str
) -> tuple[bool, str | None]:
    """
    Updates the AgentLogs table's Evaluation JSON column with new feedback.
    Returns a tuple (success: bool, error_message: str | None).
    """
    try:
        async with sql_connection_context() as (sql_server_conn, cursor):
            if not sql_server_conn:
                return False, ("Failed to connect to SQL Server for logging feedback.")

            new_feedback_entry = {
                "timestamp": datetime.now().isoformat(),
                "text": feedback_text,
                "rating": rating,
                "type": feedback_type,
            }

            from db_connectors import update_agent_log_evaluation

            if not await update_agent_log_evaluation(
                cursor, log_id, new_feedback_entry
            ):
                return False, (f"Failed to update evaluation for LogID {log_id}.")

            await asyncio.to_thread(sql_server_conn.commit)  # Await commit
            logger.info("Feedback successfully updated for LogID: %s", log_id)
            return True, None

    except Exception as e:
        logger.error(
            "Error updating agent log feedback for LogID %s: %s\n%s",
            log_id,
            e,
            traceback.format_exc(),
        )
        return False, "Internal server error during feedback update."

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Simple text chunking function.
    """
    if not text:
        return []
    chunks = []
    words = text.split()
    i = 0
    while i < len(words):
        end = i + chunk_size
        chunk = " ".join(words[i:end])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks


async def check_database_health():
    milvus_ok = False
    neo4j_ok = False
    sql_server_ok = False

    # Check Milvus
    try:
        milvus_client = await get_milvus_client()
        if milvus_client:
            milvus_ok = True
            if hasattr(milvus_client, "close"):
                await milvus_client.close()
    except Exception:
        milvus_ok = False

    # Check Neo4j
    try:
        neo4j_driver = await get_neo4j_driver()
        if neo4j_driver:
            neo4j_ok = True
            if hasattr(neo4j_driver, "close"):
                await neo4j_driver.close()
    except Exception:
        neo4j_ok = False

    # Check SQL Server
    try:
        sql_conn = await get_sql_server_connection()
        if sql_conn is not None:
            sql_server_ok = True
            if hasattr(sql_conn, "close"):
                await sql_conn.close()
    except Exception:
        sql_server_ok = False

    return {
        "milvus": milvus_ok,
        "neo4j": neo4j_ok,
        "sql_server": sql_server_ok,
    }