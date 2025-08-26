from fastapi import APIRouter
from fastapi.responses import JSONResponse


agent_router = APIRouter()


def generate_response(data, status=200):
    return JSONResponse(content=data, status_code=status)
