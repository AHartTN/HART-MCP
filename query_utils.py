import asyncio  # Import asyncio
import json
from contextlib import asynccontextmanager  # Import asynccontextmanager

# All query templates and connection/context managers in one place.

# --- SQL Server Query Templates ---
AGENTLOGS_SELECT_EVALUATION = "SELECT Evaluation FROM AgentLogs WHERE LogID = ?"
AGENTLOGS_UPDATE_EVALUATION = "UPDATE AgentLogs SET Evaluation = ? WHERE LogID = ?"
DOCUMENT_SELECT_LIKE = "SELECT * FROM Documents WHERE DocumentContent LIKE ?"
DOCUMENT_SELECT_VECTOR = """
SELECT TOP 5 DocumentID, Text 
FROM Chunks 
WHERE Text IS NOT NULL
ORDER BY ChunkID
"""
AGENTLOG_INSERT = (
    "INSERT INTO AgentLogs (AgentID, QueryContent, ResponseContent, ThoughtTree, BDIState, Evaluation, RetrievedChunks) "
    "VALUES (?, ?, ?, ?, ?, ?, ?);"
)
AGENTLOG_UPDATE_THOUGHTTREE = "UPDATE AgentLogs SET ThoughtTree = ? WHERE LogID = ?"
DOCUMENT_INSERT = (
    "INSERT INTO Documents (DocumentID, Title, SourceURL, DocumentContent) "
    "VALUES (?, ?, ?, ?)"
)
CHUNK_INSERT = (
    "INSERT INTO Chunks (ChunkID, DocumentID, Text, Embedding, "
    "ModelName, ModelVersion) VALUES (?, ?, ?, ?, ?, ?)"
)
CHANGELOG_SELECT = (
    "SELECT ChangeID, SourceTable, SourceID, ChangeType, Payload "
    "FROM ChangeLog WHERE ChangeID > ? ORDER BY ChangeID ASC"
)

# --- SQL Server Connection Context ---


@asynccontextmanager  # Changed to asynccontextmanager
async def sql_server_connection_context(conn):  # Changed to async def
    cursor = None
    try:
        cursor = await asyncio.to_thread(conn.cursor)  # Run cursor() in a thread
        yield conn, cursor
    finally:
        if cursor:
            await asyncio.to_thread(cursor.close)  # Run close() in a thread
        # conn.close() is handled by the caller of get_sql_server_connection
        # or by the sql_connection_context in utils.py


# --- Neo4j Query Templates ---
SEARCH_NODES_CONTAINS_TEXT = """
    MATCH (n)
    WHERE toLower(n.text) CONTAINS toLower($query)
    OPTIONAL MATCH (n)-[r]-(m)
    RETURN n.text AS text, COLLECT({relationship: type(r), related_text: m.text}) AS related_info
    LIMIT 5
    """


AGENT_MERGE = "MERGE (a:Agent {id: $agent_id})"
AGENTLOG_MERGE = "MERGE (l:AgentLog {id: $log_id, agent_id: $agent_id})"
AGENTLOG_DELETE = "MATCH (l:AgentLog {id: $log_id}) DETACH DELETE l"
AGENT_DELETE = "MATCH (a:Agent {id: $agent_id}) DETACH DELETE a"
DOCUMENT_MERGE = (
    "MERGE (d:Document {id: $document_id, title: $title, source_url: $source_url})"
)
DOCUMENT_DELETE = "MATCH (d:Document {id: $document_id}) DETACH DELETE d"

# --- Milvus Query Templates ---
# Add Milvus search templates as needed


# --- Generic Query Execution ---


def execute_sql_query(
    cursor,
    query: str,
    params: tuple = (),
):
    cursor.execute(query, params)
    return cursor


def execute_neo4j_query(driver, query: str, params: dict | None = None):
    if params is None:
        params = {}
    with driver.session() as session:
        return session.run(query, **params)


# Add Milvus execution helpers as needed


async def insert_document(
    cursor,
    document_id: str,
    text: str,
    metadata: dict | None = None,
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
