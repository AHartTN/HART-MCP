import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTasks

from db_connectors import get_sql_server_connection
from models import MCPSchema, MCPSchemaResponse
from plugins import call_plugin
from plugins_folder.tools import ToolRegistry, RAGTool, TreeOfThoughtTool, FinishTool # Import FinishTool
from llm_connector import LLMClient # Import LLMClient
from plugins_folder.agent_core import Agent # Import Agent

mcp_router = APIRouter()


@mcp_router.post("/mcp")
async def mcp(validated_data: MCPSchema):
    query = validated_data.query
    agent_id = validated_data.agent_id

    async def event_generator():
        try:
            # 1. Create initial database log and get log_id
            try:
                conn = await get_sql_server_connection()
            except Exception:
                conn = None

            if not conn:
                yield json.dumps({"error": "Failed to connect to SQL Server for logging."}))
                return

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
                yield json.dumps({"error": f"Failed to log agent: {e}"})
                return

            # Create ToolRegistry and register tools
            tool_registry = ToolRegistry()
            tool_registry.register_tool(RAGTool())
            tool_registry.register_tool(TreeOfThoughtTool())
            tool_registry.register_tool(FinishTool()) # Register FinishTool

            # Instantiate the new LLMClient
            llm_client = LLMClient()

            # Create a queue for streaming updates
            update_queue = asyncio.Queue()

            # Define the update_callback function
            async def update_callback(message: dict):
                await update_queue.put(message)

            # Load agent from DB or create a new one if not found
            agent = await Agent.load_from_db(agent_id, tool_registry, llm_client, update_callback)
            if not agent:
                # If agent not found, create a new one with default values
                agent = await call_plugin(
                    "create_agent", agent_id, f"Agent_{agent_id}", "Task Planner", tool_registry, llm_client, update_callback
                )
                if not agent:
                    yield json.dumps({"error": "Failed to create agent."}))
                    return

            # Call the agent's new run method in a background task, passing the update_callback.
            agent_task = asyncio.create_task(agent.run(query, log_id, update_callback))

            # Stream updates from the queue
            while True:
                try:
                    message = await asyncio.wait_for(update_queue.get(), timeout=1.0) # Adjust timeout as needed
                    yield f"data: {json.dumps(message)}\n\n"
                except asyncio.TimeoutError:
                    pass # No new message, continue waiting

                if agent_task.done():
                    # Agent task is done, check for any remaining messages in the queue
                    while not update_queue.empty():
                        message = await update_queue.get()
                        yield f"data: {json.dumps(message)}\n\n"
                    break # Exit the streaming loop

            # After the agent task is done, yield the final result
            final_result = agent_task.result()
            yield f"data: {json.dumps({"status": "completed", "result": final_result})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({"error": f"MCP error: {e}"})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")