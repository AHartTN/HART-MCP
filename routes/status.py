from fastapi import APIRouter
from fastapi.responses import JSONResponse

from utils import check_database_health

status_router = APIRouter()


@status_router.get("/status")
async def status():
    db_status = await check_database_health()

    return JSONResponse(
        content={
            "milvus": db_status["milvus"],
            "neo4j": db_status["neo4j"],
            "sql_server": db_status["sql_server"],
        },
        status_code=200,
    )
