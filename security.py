from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
import os

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == os.getenv("API_KEY"): # Replace with your actual API key validation logic
        return api_key
    else:
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="Could not validate API key")
