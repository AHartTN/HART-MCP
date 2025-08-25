from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models import FeedbackSchema
from utils import logger

feedback_router = APIRouter()


@feedback_router.post("/feedback")
async def feedback_route(feedback: FeedbackSchema):
    try:

        # ...existing code...
        return JSONResponse(content={"message": "Feedback received"}, status_code=200)
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
