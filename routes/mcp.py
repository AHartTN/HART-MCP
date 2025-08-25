import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from db_connectors import get_sql_server_connection
from models import MCPSchema, MCPSchemaResponse
from plugins import call_plugin
from plugins_folder.tools import ToolRegistry, RAGTool, TreeOfThoughtTool

mcp_router = APIRouter()


@mcp_router.post("/mcp", response_model=MCPSchemaResponse)
async def mcp(validated_data: MCPSchema):
    try:
        query = validated_data.query
        agent_id = validated_data.agent_id

        # 1. Create initial database log and get log_id
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
            cursor = await asyncio.to_thread(conn.cursor)
            await asyncio.to_thread(
                cursor.execute,
                "INSERT INTO AgentLogs (AgentID, QueryContent, BDIState) VALUES (?, ?, ?)",
                agent_id,
                query,
                json.dumps({}),  # Initial empty BDIState
            )
            await asyncio.to_thread(conn.commit)
            log_id = await asyncio.to_thread(getattr, cursor, "lastrowid", None)
        except Exception as e:
            print(f"Exception during database operations: {e}")
            return JSONResponse(
                content={"error": "Failed to log agent."}, status_code=500
            )

        # Create ToolRegistry and register tools
        tool_registry = ToolRegistry()
        tool_registry.register_tool(RAGTool())
        tool_registry.register_tool(TreeOfThoughtTool())

        # Call the create_agent plugin to get a fresh agent instance, passing the tool_registry.
        agent = await call_plugin(
            "create_agent", agent_id, f"Agent_{agent_id}", "Task Planner", tool_registry
        )
        if not agent:
            return JSONResponse(
                content={"error": "Failed to create agent."}, status_code=500
            )

        # Call the agent's new run method, passing it the mission prompt and the log_id.
        final_result = await agent.run(query, log_id)

        # Take the final result from the run method and include it in the JSON response.
        response_content = {
            "agent_id": agent_id,
            "query": query,
            "log_id": log_id,
            "status": "success",
            "result": final_result,  # Include the final result
        }
        return JSONResponse(content=response_content, status_code=200)

    except Exception as e:
        return JSONResponse(content={"error": "MCP error: " + str(e)}, status_code=500)
