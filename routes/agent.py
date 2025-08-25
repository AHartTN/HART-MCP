from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from plugins_folder.agent_core import Agent  # Import the Agent class
from utils import logger

agent_router = APIRouter()


@agent_router.post("/agent/reflexion")
async def agent_reflexion(request: Request):
    try:
        data = await request.json()
        if not data or "query" not in data:
            return JSONResponse(
                content={"error": "Missing required fields."}, status_code=400
            )
        # Use the Agent class for reflexion logic
        # For now, we'll use perform_rag_query as a placeholder for reflexion
        # In a real scenario, reflexion would involve more complex reasoning
        agent_id = data.get("agent_id", 1)  # Default agent_id for now
        log_id = data.get("log_id", 1)  # Default log_id for now
        agent = Agent(agent_id, "ReflexionAgent", "Reflexion")
        reflexion_result = await agent.perform_rag_query(data["query"], log_id)
        result = {"reflexion": reflexion_result["final_response"]}
        return JSONResponse(content=result, status_code=200)
    except KeyError as e:
        return JSONResponse(
            content={"error": f"Missing key: {str(e)}"}, status_code=400
        )
    except Exception as e:
        logger.error(f"Agent reflexion failed: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@agent_router.post("/agent/tree_of_thought")
async def agent_tree_of_thought_route(request: Request):
    try:
        data = await request.json()
        if not data or not all(k in data for k in ("agent_id", "log_id", "query")):
            return JSONResponse(
                content={"error": "Missing required fields."}, status_code=400
            )
        from tree_of_thought import initiate_tree_of_thought

        root_thought = await initiate_tree_of_thought(data["query"], data["agent_id"])
        if not root_thought:
            return JSONResponse(
                content={"error": "Failed to generate tree of thought."},
                status_code=500,
            )
        return JSONResponse(
            content={
                "message": "Tree of Thought generated successfully.",
                "tree_of_thought_root": root_thought.to_dict(),
            },
            status_code=200,
        )
    except Exception as e:
        logger.error(f"Tree of Thought agent failed: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@agent_router.post("/agent/bdi")
async def agent_bdi(request: Request):
    data = await request.json()
    if not data or not all(k in data for k in ("agent_id", "log_id")):
        return JSONResponse(
            content={"error": "Missing required fields."}, status_code=400
        )
    try:
        agent_id = data["agent_id"]
        log_id = data["log_id"]
        # Create an Agent instance
        agent = Agent(agent_id, "BDI_Agent", "BDI")
        # Update BDI state (beliefs, desires, intentions can be passed in data)
        new_beliefs = data.get("new_beliefs")
        new_desires = data.get("new_desires")
        new_intentions = data.get("new_intentions")

        await agent.update_bdi_state(log_id, new_beliefs, new_desires, new_intentions)

        response = {
            "message": "BDI state updated and intention formulated.",
            "intention": "formulated",
            "plan": "Agent plan formulated",
            "retrieved_info": "mocked RAG response for BDI",  # This should be replaced with actual RAG if BDI involves retrieval
        }
        logger.info(f"BDI state updated for AgentID: {agent_id}, LogID: {log_id}")
        return JSONResponse(content=response, status_code=200)
    except Exception as e:
        logger.error(f"agent_bdi error: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


def generate_response(data, status=200):
    return JSONResponse(content=data, status_code=status)
