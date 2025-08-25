import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from models import MCPSchema
from db_connectors import get_sql_server_connection
from plugins import call_plugin

mcp_router = APIRouter()


@mcp_router.post("/mcp")
async def mcp(validated_data: MCPSchema):
    try:
        query = validated_data.query
        agent_id = validated_data.agent_id
        agent = await call_plugin(
            "create_agent", agent_id, f"Agent_{agent_id}", "Task Planner"
        )
        if not agent:
            return JSONResponse(
                content={"error": "Failed to create agent."}, status_code=500
            )
        try:
            conn = await get_sql_server_connection()
        except Exception:
            conn = None
        if not conn:
            return JSONResponse(
                content={"error": "Failed to connect to SQL Server for logging."},
                status_code=500,
            )
        try:
            cursor = await asyncio.to_thread(conn.cursor)  # Blocking call in thread
            await asyncio.to_thread(  # Blocking call in thread
                cursor.execute,
                "INSERT INTO AgentLogs (AgentID, QueryContent, BDIState) VALUES (?, ?, ?)",
                agent_id,
                query,
                json.dumps(getattr(agent, "bdi_state", {})),
            )
            await asyncio.to_thread(conn.commit)  # Blocking call in thread
            log_id = await asyncio.to_thread(
                getattr, cursor, "lastrowid", None
            )  # Blocking call in thread
        except Exception:
            return JSONResponse(
                content={"error": "Failed to log agent."},
                status_code=500
            )
        response = {
            "agent_id": agent_id,
            "query": query,
            "log_id": log_id,
            "status": "success",
        }
        return JSONResponse(content=response, status_code=200)
    except Exception as e:
        return JSONResponse(content={"error": "MCP error: " + str(e)}, status_code=500)