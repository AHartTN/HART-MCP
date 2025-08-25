import asyncio
import os
import uuid

import aiofiles
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from db_connectors import get_sql_server_connection, insert_document
from rag_pipeline import get_embedding
from utils import allowed_file, chunk_text, extract_text, logger

ingest_router = APIRouter()


@ingest_router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):  # noqa: B008
    # ...existing code...
    if not allowed_file(file.filename):
        return JSONResponse(content={"error": "File type not allowed"}, status_code=400)
    file_extension = file.filename.rsplit(".", 1)[1].lower()
    save_path = os.path.join("uploads", file.filename)
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(await file.read())
    text_content = extract_text(save_path, file_extension)
    if text_content is None:
        return JSONResponse(
            content={"error": "Failed to extract text from file."}, status_code=500
        )
    try:
        sql_server_conn = await get_sql_server_connection()
    except Exception as e:
        logger.error("Error connecting to SQL Server for ingestion: %s", e)
        return JSONResponse(
            content={"error": "Failed to connect to SQL Server for ingestion."},
            status_code=500,
        )
    cursor = await asyncio.to_thread(sql_server_conn.cursor)  # Blocking call in thread
    document_id = str(uuid.uuid4())
    try:
        # insert_document is already async and uses asyncio.to_thread internally
        await insert_document(
            cursor,
            document_id,
            text_content,
            {"filename": file.filename, "save_path": save_path},
        )
        document_inserted = True
    except Exception as e:
        logger.error(f"Insert document failed: {e}")
        document_inserted = False
    # Chunk ingestion logic
    chunks = chunk_text(text_content)
    ingested_chunks_count = 0
    embedding_failed = False
    for i, chunk_text_content in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        embedding = await get_embedding(chunk_text_content)
        if embedding is None:
            logger.warning(
                f"Failed to generate embedding for chunk {i + 1} of {file.filename}. Skipping chunk."
            )
            embedding_failed = True
            continue
        try:
            embedding_str = str(embedding)
            await asyncio.to_thread(  # Blocking call in thread
                cursor.execute,
                "INSERT INTO Chunks (ChunkID, DocumentID, Text, Embedding, ModelName, ModelVersion) VALUES (?, ?, ?, ?, ?, ?)",
                chunk_id,
                document_id,
                chunk_text_content,
                embedding_str,
                "all-MiniLM-L6-v2",
                "1.0",
            )
            ingested_chunks_count += 1
            document_inserted = True
        except Exception as e:
            logger.error(f"Insert chunk failed: {e}")
    if not document_inserted:
        return JSONResponse(
            content={"error": "Failed to insert document into database."},
            status_code=500,
        )
    if embedding_failed and ingested_chunks_count == 0:
        return JSONResponse(
            content={"error": "Failed to generate embeddings for all chunks."},
            status_code=500,
        )
    try:
        if hasattr(sql_server_conn, "commit"):
            await asyncio.to_thread(sql_server_conn.commit)  # Blocking call in thread
    except Exception as e:
        logger.error(f"Commit failed: {e}")
    logger.info(
        f"Ingested {ingested_chunks_count} chunks for document {file.filename}."
    )
    return JSONResponse(
        content={
            "message": "File ingested successfully",
            "filename": file.filename,
            "document_id": document_id,
            "ingested_chunks": ingested_chunks_count,
            "filetype": file_extension,
        },
        status_code=200,
    )
    # ...existing code...


# Export for tests
__all__ = ["ingest_router"]
