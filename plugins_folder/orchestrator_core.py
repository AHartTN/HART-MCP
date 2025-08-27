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


def get_utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


logger = logging.getLogger(__name__)


class OrchestratorAgent:
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
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.bdi_state = {"beliefs": {}, "desires": [], "intentions": []}
        self.tool_registry = tool_registry
        self.scratchpad = []
        self.llm = llm_client
        self.update_callback = update_callback
        self.project_state = project_state

    @classmethod
    async def load_from_db(
        cls,
        agent_id: int,
        tool_registry: ToolRegistry,
        llm_client: LLMClient,
        update_callback: Optional[Callable] = None,
        project_state: Optional[ProjectState] = None,
    ):
        # For testing purposes, we will not load from the database.
        # Instead, we will create a new agent directly.
        return cls(
            agent_id,
            f"Orchestrator_{agent_id}",
            "Mission Orchestrator",
            tool_registry,
            llm_client,
            update_callback,
            project_state,
        )

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

    async def run(
        self,
        mission_prompt: str,
        log_id: int,
        update_callback: Optional[Callable] = None,
    ) -> dict:
        logger.info(
            "OrchestratorAgent %s starting mission: %s", self.name, mission_prompt
        )
        self.scratchpad = [f"Mission: {mission_prompt}"]
        final_answer = None

        if self.update_callback:
            await self.update_callback(
                {
                    "type": "orchestrator_mission_start",
                    "content": mission_prompt,
                    "agent_name": self.name,
                }
            )

        for step in range(10):  # Max 10 steps for the cognitive loop
            system_prompt = AGENT_CONSTITUTION
            persona_details = f"You are {self.name}, an AI orchestrator agent with the role of {self.role}. Your primary goal is to break down complex missions and delegate sub-tasks to specialist agents using the available tools. You must always respond with a JSON object containing a 'thought' and an 'action'. The 'action' must contain a 'tool' and a 'query'.\n"
            system_prompt = persona_details + system_prompt
            available_tools = ", ".join(self.tool_registry.get_tool_names())
            scratchpad_content = "\n".join(self.scratchpad)

            llm_prompt = f"""
{system_prompt}
Overall Mission: {mission_prompt}
Available Tools: {available_tools}
Scratchpad History:
{scratchpad_content}
Your next response MUST be a JSON object with two keys: 'thought' (string) and 'action' (object). The 'action' object MUST have two keys: 'tool_name' (string, name of the tool to use) and 'parameters' (object, a dictionary of named parameters for the tool). If you have completed the mission, use the 'FinishTool' and provide the final answer as the 'response' parameter.
Example: {{'thought': 'I need to delegate this task to a specialist.', 'action': {{'tool_name': 'DelegateToSpecialistTool', 'parameters': {{'mission_prompt': 'sub-task for specialist'}}}}}} """
            logger.info("LLM Prompt for step %s:\n%s", step, llm_prompt)

            if self.update_callback:
                await self.update_callback(
                    {
                        "type": "orchestrator_thought_process",
                        "content": f"Step {step}: Reasoning...",
                        "agent_name": self.name,
                    }
                )

            llm_response_text = await self.llm.invoke(llm_prompt)
            logger.info("LLM Raw Response: %s", llm_response_text)

            try:
                llm_response = json.loads(llm_response_text)
                thought = llm_response.get("thought")
                action = llm_response.get("action")

                if (
                    not thought
                    or not action
                    or "tool_name" not in action
                    or "parameters" not in action
                ):
                    raise ValueError(
                        "LLM response is not in the expected JSON format or missing keys."
                    )

                tool_name = action["tool_name"]
                parameters_for_tool = action["parameters"]

                self.scratchpad.append(f"Thought: {thought}")
                if self.update_callback:
                    await self.update_callback(
                        {
                            "type": "orchestrator_thought",
                            "content": thought,
                            "agent_name": self.name,
                        }
                    )

                if tool_name == "DelegateToSpecialistTool":
                    parameters_for_tool["log_id"] = log_id

                if tool_name == "FinishTool":
                    final_answer = parameters_for_tool.get("response")
                    self.scratchpad.append(f"Final Answer: {final_answer}")
                    if self.update_callback:
                        await self.update_callback(
                            {
                                "type": "orchestrator_final_answer",
                                "content": final_answer,
                                "agent_name": self.name,
                            }
                        )
                    break
                else:
                    logger.info(
                        "Attempting to use tool: %s with parameters: %s",
                        tool_name,
                        parameters_for_tool,
                    )
                    if self.update_callback:
                        await self.update_callback(
                            {
                                "type": "orchestrator_action",
                                "content": {
                                    "tool_name": tool_name,
                                    "parameters": parameters_for_tool,
                                },
                                "agent_name": self.name,
                            }
                        )

                    tool_result = await self.tool_registry.use_tool(
                        tool_name, **parameters_for_tool
                    )
                    observation = (
                        f"Observation: Tool Result ({tool_name}): {tool_result}"
                    )
                    logger.info(
                        "Tool '%s' executed. Result: %s", tool_name, tool_result
                    )

                    self.scratchpad.append(observation)
                    if self.update_callback:
                        await self.update_callback(
                            {
                                "type": "orchestrator_observation",
                                "content": observation,
                                "agent_name": self.name,
                            }
                        )

                    self.bdi_state["beliefs"].update(
                        {f"step_{step}_result": str(tool_result)}
                    )
                    await self.update_bdi_state(
                        log_id, new_beliefs={f"step_{step}_result": str(tool_result)}
                    )

            except json.JSONDecodeError as e:
                error_message = f"Error decoding JSON from LLM response: {e}. Response: {llm_response_text}"
                self.scratchpad.append(f"Error: {error_message}")
                logger.error(error_message)
                if self.update_callback:
                    await self.update_callback(
                        {
                            "type": "orchestrator_error",
                            "content": error_message,
                            "agent_name": self.name,
                        }
                    )
                break
            except ValueError as e:
                error_message = f"Error in ReAct loop (tool selection/execution): {e}"
                self.scratchpad.append(f"Error: {error_message}")
                logger.error(error_message)
                if self.update_callback:
                    await self.update_callback(
                        {
                            "type": "orchestrator_error",
                            "content": error_message,
                            "agent_name": self.name,
                        }
                    )
                break
            except Exception as e:
                error_message = f"An unexpected error occurred: {e}"
                self.scratchpad.append(f"Error: {error_message}")
                logger.error(error_message)
                if self.update_callback:
                    await self.update_callback(
                        {
                            "type": "orchestrator_error",
                            "content": error_message,
                            "agent_name": self.name,
                        }
                    )
                break

        if not final_answer:
            final_answer = (
                "No final answer generated within the given steps."  # Fallback
            )

        scratchpad_text = "\n".join(self.scratchpad)
        summary_prompt = f"""
Please summarize the following orchestrator mission scratchpad, focusing on key actions, observations, and outcomes. This summary will be used to update the orchestrator agent's long-term beliefs.

Scratchpad:
{scratchpad_text}"""
        mission_summary = await self.llm.invoke(summary_prompt)
        logger.info("Orchestrator Mission Summary for BDI update: %s", mission_summary)

        self.bdi_state["beliefs"].update(
            {"last_orchestrator_mission_summary": mission_summary}
        )
        await self.update_bdi_state(
            log_id, new_beliefs={"last_orchestrator_mission_summary": mission_summary}
        )

        self.bdi_state["beliefs"].update(
            {"final_orchestrator_mission_outcome": final_answer}
        )
        await self.update_bdi_state(
            log_id, new_beliefs={"final_orchestrator_mission_outcome": final_answer}
        )

        logger.info(
            "OrchestratorAgent %s completed mission with final answer: %s",
            self.name,
            final_answer,
        )
        return {"final_response": final_answer}


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
