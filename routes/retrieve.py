from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from rag_pipeline import get_embedding, search_milvus
from utils import logger, milvus_connection_context

retrieve_router = APIRouter()


class RetrieveSchema(BaseModel):
    query: str


@retrieve_router.post("/retrieve")
async def retrieve(request: Request):
    try:
        data = await request.json()
        if not data:
            logger.error("Bad request: no JSON payload")
            return JSONResponse(
                content={"error": "Bad request: no JSON payload"}, status_code=400
            )

        validated_data = RetrieveSchema(**data)
        query = validated_data.query

        query_embedding = await get_embedding(query)
        if query_embedding is None:
            logger.error("Failed to generate query embedding.")
            return JSONResponse(
                content={"error": "Failed to generate query embedding."},
                status_code=400,
            )

        async with milvus_connection_context() as milvus_client:  # Use async with
            if (
                milvus_client is None
            ):  # This check might become redundant if context manager handles connection errors
                logger.error("Failed to connect to Milvus.")
                return JSONResponse(
                    content={"error": "Failed to connect to Milvus."}, status_code=400
                )

            results = await search_milvus(milvus_client, query_embedding)
            if results is None or not results:
                logger.error("No results found.")
                return JSONResponse(
                    content={"error": "No results found."}, status_code=404
                )

            return JSONResponse(content={"results": results}, status_code=200)
    except Exception as e:
        logger.error(f"Internal server error: {e}")
        return JSONResponse(content={"error": "Internal server error"}, status_code=500)
