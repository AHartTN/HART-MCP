import os
import uuid

import aiofiles
from fastapi import APIRouter, File, UploadFile, Depends
from fastapi.responses import JSONResponse

from db_connectors import get_sql_server_connection
from query_utils import insert_document
from utils import allowed_file, extract_text
from security import get_api_key

ingest_router = APIRouter(dependencies=[Depends(get_api_key)])


@ingest_router.post("/ingest")
async def ingest_document(file: UploadFile = File(...)):  # noqa: B008
    if not file.filename or not allowed_file(file.filename):
        return JSONResponse(
            content={"error": "File type not allowed"},
            status_code=400,
        )
    file_extension = file.filename.rsplit(".", 1)[1].lower()
    save_path = os.path.join("uploads", file.filename)
    async with aiofiles.open(save_path, "wb") as f:
        await f.write(await file.read())
    try:
        text_content = extract_text(save_path, file_extension)
        if text_content is None:
            raise Exception("Failed to extract text from file.")
        conn_manager = get_sql_server_connection()
        if conn_manager is None:
            raise Exception("Failed to connect to SQL Server for ingestion.")
        # Support both async and sync context manager for test mocks
        if hasattr(conn_manager, "__aenter__"):
            try:
                conn = await conn_manager.__aenter__()
            except Exception as inner_e:
                raise Exception(str(inner_e)) from inner_e
        elif hasattr(conn_manager, "__enter__"):
            try:
                conn = conn_manager.__enter__()
            except Exception as inner_e:
                raise Exception(str(inner_e)) from inner_e
        else:
            conn = conn_manager
        if not conn:
            raise Exception("Failed to connect to SQL Server for ingestion.")
        cursor = conn.cursor()
        document_id = str(uuid.uuid4())
        await insert_document(
            cursor,
            document_id,
            text_content,
            {"filename": file.filename, "save_path": save_path},
        )
        conn.commit()
        return JSONResponse(
            content={"message": "Document ingested successfully."}, status_code=200
        )
    except Exception as e:

        def find_error_message(exc, target):
            while exc:
                msg = str(exc)
                if target in msg:
                    return True
                exc = getattr(exc, "__cause__", None) or getattr(
                    exc, "__context__", None
                )
            return False

        if find_error_message(e, "Failed to extract text from file."):
            return JSONResponse(
                content={"error": "Failed to extract text from file."}, status_code=500
            )
        if find_error_message(e, "Failed to connect to SQL Server for ingestion."):
            return JSONResponse(
                content={"error": "Failed to connect to SQL Server for ingestion."},
                status_code=500,
            )
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)


__all__ = ["ingest_router"]
