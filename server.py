import logging

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from routes.agent import agent_router
from routes.feedback import feedback_router
from routes.health import health_router
from routes.ingest import ingest_router
from routes.mcp import mcp_router
from routes.retrieve import retrieve_router
from routes.status import status_router
from security import get_api_key

app = FastAPI(dependencies=[Depends(get_api_key)])

# Configure logging
logging.basicConfig(level=logging.INFO)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(agent_router)
app.include_router(feedback_router)
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(mcp_router)
app.include_router(retrieve_router)
app.include_router(status_router)


@app.get("/")
async def read_root():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
