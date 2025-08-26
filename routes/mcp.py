import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.background import BackgroundTasks

from db_connectors import get_sql_server_connection
from llm_connector import LLMClient  # Import LLMClient
from models import MCPSchema, MCPSchemaResponse
from plugins import call_plugin
from plugins_folder.agent_core import SpecialistAgent  # Import SpecialistAgent
from plugins_folder.orchestrator_core import \
    OrchestratorAgent  # Import OrchestratorAgent
from plugins_folder.tools import (DelegateToSpecialistTool,  # Import new tools
                                  FinishTool, RAGTool, ToolRegistry,
                                  TreeOfThoughtTool)

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

            # Instantiate the new LLMClient
            llm_client = LLMClient()

            # Create a queue for streaming updates
            update_queue = asyncio.Queue()

            # Define the update_callback function
            async def update_callback(message: dict):
                await update_queue.put(message)

            # Create SpecialistAgent with its tools
            specialist_tool_registry = ToolRegistry()
            specialist_tool_registry.register_tool(RAGTool())
            specialist_tool_registry.register_tool(TreeOfThoughtTool())
            specialist_tool_registry.register_tool(FinishTool())

            specialist_agent = await SpecialistAgent.load_from_db(
                agent_id=agent_id, 
                tool_registry=specialist_tool_registry, 
                llm_client=llm_client, 
                update_callback=update_callback
            )
            if not specialist_agent:
                specialist_agent = await call_plugin(
                    "create_specialist_agent", 
                    agent_id, 
                    f"Specialist_{agent_id}", 
                    "Specialist Task Executor", 
                    specialist_tool_registry, 
                    llm_client, 
                    update_callback
                )
                if not specialist_agent:
                    yield json.dumps({"error": "Failed to create specialist agent."}))
                    return

            # Create DelegateToSpecialistTool
            delegate_tool = DelegateToSpecialistTool(specialist_agent=specialist_agent)

            # Create OrchestratorAgent with its own ToolRegistry containing only DelegateToSpecialistTool
            orchestrator_tool_registry = ToolRegistry()
            orchestrator_tool_registry.register_tool(delegate_tool)
            orchestrator_tool_registry.register_tool(FinishTool()) # Orchestrator also needs a FinishTool

            orchestrator_agent = await OrchestratorAgent.load_from_db(
                agent_id=agent_id + 1, # Use a different ID for orchestrator for now
                tool_registry=orchestrator_tool_registry, 
                llm_client=llm_client, 
                update_callback=update_callback
            )
            if not orchestrator_agent:
                orchestrator_agent = await call_plugin(
                    "create_orchestrator_agent", 
                    agent_id + 1, 
                    f"Orchestrator_{agent_id}", 
                    "Mission Orchestrator", 
                    orchestrator_tool_registry, 
                    llm_client, 
                    update_callback
                )
                if not orchestrator_agent:
                    yield json.dumps({"error": "Failed to create orchestrator agent."}))
                    return

            # Pass the user's mission to the Orchestrator's run method
            agent_task = asyncio.create_task(orchestrator_agent.run(query, log_id, update_callback))

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
            yield f"data: {json.dumps({"status": "completed", "result": final_result})}\"\n\n"

        except Exception as e:
            yield f"data: {json.dumps({"error": f"MCP error: {e}"})}\"\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")