from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from utils import logger

feedback_router = APIRouter()


@feedback_router.post("/feedback")
async def feedback_route(request: Request):
    try:
        data = await request.json()
        if not data.get("log_id") or not data.get("feedback_text"):
            return JSONResponse(
                content={"error": "Validation error: Missing log_id or feedback_text"},
                status_code=400,
            )

        # ...existing code...
        return JSONResponse(content={"message": "Feedback received"}, status_code=200)
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
