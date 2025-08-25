import logging

from fastapi import FastAPI

from routes.agent import agent_router
from routes.feedback import feedback_router
from routes.health import health_router
from routes.ingest import ingest_router
from routes.mcp import mcp_router
from routes.retrieve import retrieve_router
from routes.status import status_router

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Include routers
app.include_router(agent_router)
app.include_router(feedback_router)
app.include_router(health_router)
app.include_router(ingest_router)
app.include_router(mcp_router)
app.include_router(retrieve_router)
app.include_router(status_router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
