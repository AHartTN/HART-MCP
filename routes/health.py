from fastapi import APIRouter
from fastapi.responses import JSONResponse

from utils import check_database_health

health_router = APIRouter()


@health_router.get("/health")
async def health():
    db_status = await check_database_health()

    if all(db_status.values()):
        return JSONResponse(
            content={
                "status": "ok",
                "databases": db_status,
            },
            status_code=200,
        )
    elif any(db_status.values()):
        return JSONResponse(
            content={
                "status": "degraded",
                "databases": db_status,
            },
            status_code=200,
        )
    else:
        return JSONResponse(
            content={
                "status": "error",
                "databases": db_status,
            },
            status_code=500,
        )
