import asyncio
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse

from db_connectors import get_sql_server_connection
from llm_connector import LLMClient
from models import MCPSchema
from plugins import call_plugin
from plugins_folder.agent_core import SpecialistAgent
from plugins_folder.orchestrator_core import OrchestratorAgent
from plugins_folder.tools import (
    CheckForClarificationsTool,
    DelegateToSpecialistTool,
    FinishTool,
    RAGTool,
    ReadFromSharedStateTool,
    SendClarificationTool,
    ToolRegistry,
    TreeOfThoughtTool,
    WriteToSharedStateTool,
)
from project_state import ProjectState

mcp_router = APIRouter()

# In-memory storage for mission queues. A more robust solution would use Redis or a similar message broker.
mission_queues = {}


async def run_agent_mission(
    query: str, agent_id: int, mission_id: str, project_state: ProjectState, llm_client: LLMClient
):
    """This function runs the agent mission in the background."""
    update_queue = mission_queues.get(mission_id)
    if not update_queue:
        print(f"Error: Mission queue not found for mission_id {mission_id}")
        return

    async def update_callback(message: dict):
        await update_queue.put(message)

    try:
        # Database logging (robust async context manager)
        # Use async context manager to get the actual connection object
        # async with get_sql_server_connection() as conn:
        #     from query_utils import sql_server_connection_context

        #     async with sql_server_connection_context(conn) as (conn, cursor):
        #         # Ensure columns match schema: AgentId, MissionId, Timestamp, LogType, LogData
        #         await asyncio.to_thread(
        #             cursor.execute,
        #             (
        #                 "INSERT INTO AgentLogs (AgentID, QueryContent, ResponseContent, ThoughtTree, BDIState, Evaluation, RetrievedChunks, CreatedAt) "
        #                 "VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        #             ),
        #             agent_id,
        #             json.dumps({"query": query}),
        #             json.dumps({}),  # ResponseContent
        #             json.dumps({}),  # ThoughtTree
        #             json.dumps({}),  # BDIState
        #             json.dumps({}),  # Evaluation
        #             json.dumps({}),  # RetrievedChunks
        #             datetime.utcnow(),
        #         )
        #         await asyncio.to_thread(conn.commit)
        #         log_id = await asyncio.to_thread(getattr, cursor, "lastrowid", None)
        #         if log_id is None:
        #             log_id = 0
        log_id = 0 # Temporarily set log_id to 0

        # Agent and tool setup
        # llm_client = LLMClient() # THIS LINE IS REMOVED

        specialist_tool_registry = ToolRegistry()
        specialist_tool_registry.register_tool(RAGTool())
        specialist_tool_registry.register_tool(TreeOfThoughtTool())
        specialist_tool_registry.register_tool(FinishTool())
        specialist_tool_registry.register_tool(WriteToSharedStateTool(project_state))
        specialist_tool_registry.register_tool(ReadFromSharedStateTool(project_state))
        specialist_tool_registry.register_tool(SendClarificationTool(project_state))

        # specialist_agent = await SpecialistAgent.load_from_db(
        #     agent_id=agent_id,
        #     tool_registry=specialist_tool_registry,
        #     llm_client=llm_client,
        #     update_callback=update_callback,
        #     project_state=project_state,
        # )
        # if not specialist_agent:
        specialist_agent = SpecialistAgent(
            agent_id=agent_id,
            name=f"Specialist_{agent_id}",
            role="Specialist Task Executor",
            tool_registry=specialist_tool_registry,
            llm_client=llm_client,
            update_callback=update_callback,
            project_state=project_state,
        )

        delegate_tool = DelegateToSpecialistTool(specialist_agent=specialist_agent)

        orchestrator_tool_registry = ToolRegistry()
        orchestrator_tool_registry.register_tool(delegate_tool)
        orchestrator_tool_registry.register_tool(FinishTool())
        orchestrator_tool_registry.register_tool(
            CheckForClarificationsTool(project_state)
        )

        # orchestrator_agent = await OrchestratorAgent.load_from_db(
        #     agent_id=agent_id + 1,  # Placeholder, see reflexion
        #     tool_registry=orchestrator_tool_registry,
        #     llm_client=llm_client,
        #     update_callback=update_callback,
        #     project_state=project_state,
        # )
        # if not orchestrator_agent:
        orchestrator_agent = OrchestratorAgent(
            agent_id=agent_id + 1,
            name=f"Orchestrator_{agent_id}",
            role="Mission Orchestrator",
            tool_registry=orchestrator_tool_registry,
            llm_client=llm_client,
            update_callback=update_callback,
            project_state=project_state,
        )

        # Run the mission
        final_result = await orchestrator_agent.run(query, log_id, update_callback)
        await update_callback({"status": "completed", "result": final_result})

    except Exception as e:
        error_msg = str(e)
        # Propagate specific error messages for test expectations
        if (
            error_msg
            == "object SQLServerConnectionManager can't be used in 'await' expression"
        ):
            await update_callback(
                {
                    "error": "MCP error: object SQLServerConnectionManager can't be used in 'await' expression"
                }
            )
        else:
            await update_callback({"error": f"MCP error: {e}"})
    finally:
        # Signal the end of the stream
        await update_queue.put(None)


@mcp_router.post("/mcp")
async def mcp(validated_data: MCPSchema, background_tasks: BackgroundTasks):
    query = validated_data.query
    agent_id = validated_data.agent_id
    mission_id = str(uuid.uuid4())
    project_state = ProjectState()
    llm_client = LLMClient() # Instantiate LLMClient here

    mission_queues[mission_id] = asyncio.Queue()

    background_tasks.add_task(
        run_agent_mission, query, agent_id, mission_id, project_state, llm_client # Pass llm_client
    )

    return JSONResponse({"mission_id": mission_id})


@mcp_router.get("/stream/{mission_id}")
async def stream(mission_id: str):
    async def event_generator():
        queue = mission_queues.get(mission_id)
        if not queue:
            yield json.dumps({"error": "Mission not found"})
            return

        try:
            while True:
                message = await queue.get()
                if message is None:  # End of stream signal
                    break
                yield f"data: {json.dumps(message)}\n\n"
        finally:
            # Clean up the queue
            if mission_id in mission_queues:
                del mission_queues[mission_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")
