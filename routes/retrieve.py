from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models import RetrieveSchema
from rag_pipeline import get_embedding, search_milvus
from utils import logger, milvus_connection_context

retrieve_router = APIRouter()


@retrieve_router.post("/retrieve")
async def retrieve(validated_data: RetrieveSchema):
    try:
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
