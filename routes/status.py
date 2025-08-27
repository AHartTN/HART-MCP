from fastapi import APIRouter
from fastapi.responses import JSONResponse

from utils import check_database_health

status_router = APIRouter()


@status_router.get("/status")
async def status():
    from utils import check_database_health

    db_status = await check_database_health()
    databases = {
        "milvus": "connected" if db_status["milvus"] else "disconnected",
        "neo4j": "connected" if db_status["neo4j"] else "disconnected",
        "sql_server": "connected" if db_status["sql_server"] else "disconnected",
    }
    return JSONResponse(
        content={
            "status": "running",
            "databases": databases,
        },
        status_code=200,
    )
