import asyncio
import datetime
import json
import logging
from typing import Callable, Dict, List, Optional

from llm_connector import LLMClient
from project_state import ProjectState
from prompts import AGENT_CONSTITUTION
from utils import sql_connection_context
from plugins_folder.base_agent import BaseAgent


def get_utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


logger = logging.getLogger(__name__)


class SpecialistAgent(BaseAgent):
    def __init__(
        self,
        agent_id: int,
        name: str,
        role: str,
        tool_registry,
        llm_client: LLMClient,
        update_callback: Optional[Callable] = None,
        project_state: Optional[ProjectState] = None,
    ):
        super().__init__(
            agent_id, name, role, tool_registry, llm_client, update_callback, project_state
        )

    @classmethod
    async def load_from_db(
        cls,
        agent_id: int,
        tool_registry,
        llm_client: LLMClient,
        update_callback: Optional[Callable] = None,
        project_state: Optional[ProjectState] = None,
    ):
        return cls(
            agent_id,
            f"Specialist_{agent_id}",
            "Specialist Task Executor",
            tool_registry,
            llm_client,
            update_callback,
            project_state,
        )

    async def run(
        self,
        mission_prompt: str,
        log_id: int,
        update_callback: Optional[Callable] = None,
    ) -> dict:
        system_prompt_template = (
            f"You are {{name}}, an AI agent with the role of {{role}}.\n"
            + AGENT_CONSTITUTION
        )
        return await super().run(
            mission_prompt,
            log_id,
            system_prompt_template,
            "specialist",
        )


async def create_agent(
    agent_id: int,
    name: str,
    role: str,
    tool_registry,
    llm_client: LLMClient,
    update_callback: Optional[Callable] = None,
    project_state: Optional[ProjectState] = None,
) -> "SpecialistAgent":
    """
    Creates and returns an Agent instance.
    """
    return await SpecialistAgent.load_from_db(
        agent_id, tool_registry, llm_client, update_callback, project_state
    )
