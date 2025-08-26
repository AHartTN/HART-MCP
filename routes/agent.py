from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from plugins_folder.agent_core import SpecialistAgent as Agent  # Import the Agent class
from utils import logger

agent_router = APIRouter()


def generate_response(data, status=200):
    return JSONResponse(content=data, status_code=status)
