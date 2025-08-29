import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import Depends, FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from routes.agent import agent_router
from routes.feedback import feedback_router
from routes.health import health_router
from routes.ingest import ingest_router
from routes.mcp import mcp_router
from routes.retrieve import retrieve_router
from routes.status import status_router
from security import get_api_key
from config import MILVUS_HOST, MILVUS_PORT, NEO4J_URI, SQL_SERVER_SERVER


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown."""
    # Startup
    logging.info("🚀 HART-MCP starting up...")
    yield
    # Shutdown
    logging.info("🛑 HART-MCP shutting down...")


app = FastAPI(
    title="HART-MCP",
    description="Multi-Agent Control Plane with RAG and Tree of Thought",
    version="1.0.0",
    dependencies=[Depends(get_api_key)],
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/hart-mcp.log", mode="a"),
    ],
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.localhost", "testserver"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


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
    """Serve the main application page."""
    try:
        return FileResponse("static/index.html")
    except FileNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"message": "Frontend not built. Run 'npm run build' first."},
        )


@app.get("/api/info")
async def get_api_info():
    """Get API information and system status."""
    return {
        "name": "HART-MCP",
        "version": "1.0.0",
        "description": "Multi-Agent Control Plane with RAG and Tree of Thought",
        "components": {
            "sql_server": f"{SQL_SERVER_SERVER}",
            "milvus": f"{MILVUS_HOST}:{MILVUS_PORT}",
            "neo4j": f"{NEO4J_URI}",
        },
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "path": request.url.path},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for production."""
    logging.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "path": request.url.path},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
