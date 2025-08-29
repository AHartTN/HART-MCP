import asyncio
import datetime
import json
import logging
from typing import Callable, Dict, List, Optional

from llm_connector import LLMClient
from plugins_folder.tools import ToolRegistry
from project_state import ProjectState
from prompts import AGENT_CONSTITUTION
from utils import sql_connection_context
from plugins_folder.base_agent import BaseAgent


def get_utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    def __init__(
        self,
        agent_id: int,
        name: str,
        role: str,
        tool_registry: ToolRegistry,
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
        tool_registry: ToolRegistry,
        llm_client: LLMClient,
        update_callback: Optional[Callable] = None,
        project_state: Optional[ProjectState] = None,
    ):
        return cls(
            agent_id,
            f"Orchestrator_{agent_id}",
            "Mission Orchestrator",
            tool_registry,
            llm_client,
            update_callback,
            project_state,
        )

    async def run(
        self,
        mission_prompt: str,
        log_id: int,
        system_prompt_template: Optional[str] = None,
        update_callback_type_prefix: Optional[str] = None,
        update_callback: Optional[Callable] = None,
    ) -> dict:
        """Run orchestrator mission with proper template formatting."""
        # Use provided template or default orchestrator template
        if not system_prompt_template:
            system_prompt_template = (
                "You are {name}, an AI orchestrator agent with the role of {role}. "
                "Your primary goal is to break down complex missions and delegate sub-tasks to specialist agents using the available tools. "
                "You must always respond with a JSON object containing a 'thought' and an 'action'. "
                "The 'action' must contain a 'tool_name' and 'parameters'.\n"
                + AGENT_CONSTITUTION
            )
        
        # Use provided prefix or default
        callback_prefix = update_callback_type_prefix or "orchestrator"
        
        # Override the update callback if provided
        if update_callback and update_callback != self.update_callback:
            original_callback = self.update_callback
            self.update_callback = update_callback
            try:
                result = await super().run(
                    mission_prompt,
                    log_id,
                    system_prompt_template,
                    callback_prefix,
                )
                return result
            finally:
                self.update_callback = original_callback
        else:
            return await super().run(
                mission_prompt,
                log_id,
                system_prompt_template,
                callback_prefix,
            )


async def create_orchestrator_agent(
    agent_id: int,
    name: str,
    role: str,
    tool_registry: ToolRegistry,
    llm_client: LLMClient,
    update_callback: Optional[Callable] = None,
    project_state: Optional[ProjectState] = None,
) -> OrchestratorAgent:
    """
    Creates and returns an OrchestratorAgent instance.
    """
    return OrchestratorAgent(
        agent_id, name, role, tool_registry, llm_client, update_callback, project_state
    )
