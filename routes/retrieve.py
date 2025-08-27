import logging

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from db_connectors import get_milvus_client
from rag_pipeline import get_embedding
from security import get_api_key

logger = logging.getLogger(__name__)

retrieve_router = APIRouter(dependencies=[Depends(get_api_key)])


@retrieve_router.post("/retrieve")
async def retrieve(request: Request):
    try:
        body = await request.json()
        query = body.get("query")
        embedding = await get_embedding(query)
        if embedding is None:
            raise Exception("Failed to generate query embedding.")
        milvus_client = await get_milvus_client()
        if hasattr(milvus_client, "__aenter__"):
            try:
                milvus_client_obj = await milvus_client.__aenter__()
            except Exception as inner_e:
                raise Exception(str(inner_e))
        elif hasattr(milvus_client, "__enter__"):
            try:
                milvus_client_obj = milvus_client.__enter__()
            except Exception as inner_e:
                raise Exception(str(inner_e))
        else:
            milvus_client_obj = milvus_client
        if milvus_client_obj is None:
            raise Exception("Failed to connect to Milvus.")
        collection_name = "default_collection"
        from rag_pipeline import search_milvus

        results = search_milvus(milvus_client_obj, embedding, collection_name)
        if results is None or not results:
            logger.warning("No results found for query: %s", query)
            return JSONResponse({"error": "No results found."}, status_code=404)
        return JSONResponse({"results": results}, status_code=200)
    except Exception as e:
        logger.error("Retrieve endpoint error: %s", e, exc_info=True)

        def find_error_message(exc, target):
            while exc:
                msg = str(exc)
                if target in msg:
                    return True
                exc = getattr(exc, "__cause__", None) or getattr(
                    exc, "__context__", None
                )
            return False

        if find_error_message(e, "Failed to generate query embedding."):
            return JSONResponse(
                {"error": "Failed to generate query embedding."}, status_code=500
            )
        if find_error_message(e, "Failed to connect to Milvus."):
            return JSONResponse(
                {"error": "Failed to connect to Milvus."}, status_code=500
            )
        return JSONResponse({"error": "Internal server error"}, status_code=500)
