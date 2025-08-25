import asyncio
import datetime
import json
import logging
from typing import Dict, List

from utils import sql_connection_context


def get_utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, agent_id: int, name: str, role: str):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.bdi_state = {"beliefs": {}, "desires": [], "intentions": []}

    async def perform_rag_query(self, query: str, log_id: int) -> dict:
        # Simulate RAG response for test and production
        return {
            "final_response": f"RAG response for query '{query}' and log_id {log_id}"
        }

    async def initiate_tot(self, problem: str, log_id: int):
        # Simulate ToT root node for test and production
        class Thought:
            def __init__(self, text, score, children=None):
                self.text = text
                self.score = score
                self.children = children or []

        return Thought(f"Root: {problem}", 1.0, [])

    async def update_bdi_state(
        self,
        log_id: int,
        new_beliefs: Dict = None,
        new_desires: List = None,
        new_intentions: List = None,
    ):
        async with sql_connection_context() as (sql_server_conn, cursor):
            if cursor is None or not hasattr(cursor, "execute"):
                if sql_server_conn and hasattr(sql_server_conn, "close"):
                    await asyncio.to_thread(
                        sql_server_conn.close
                    )  # Ensure close is awaited if it's blocking
                logger.error("Failed to obtain database cursor for BDI state update.")
                return
            try:
                if new_beliefs:
                    self.bdi_state["beliefs"].update(new_beliefs)
                if new_desires:
                    self.bdi_state["desires"].extend(new_desires)
                if new_intentions:
                    self.bdi_state["intentions"].extend(new_intentions)

                await asyncio.to_thread(
                    cursor.execute,
                    "UPDATE AgentLogs SET BDIState = ? WHERE LogID = ?",
                    json.dumps(self.bdi_state),
                    log_id,
                )
                if hasattr(sql_server_conn, "commit"):
                    await asyncio.to_thread(sql_server_conn.commit)
                logger.info(
                    "Updated BDIState for LogID %s for agent %s.",
                    log_id,
                    self.name,
                )
            except RuntimeError as exc:
                logger.error(
                    "Error updating BDIState for LogID %s: %s",
                    log_id,
                    exc,
                )


async def create_agent(agent_id: int, name: str, role: str) -> Agent:
    """
    Creates and returns an Agent instance.
    """
    return Agent(agent_id, name, role)
