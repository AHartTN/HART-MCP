import asyncio
import datetime
import json
import logging
from typing import Dict, List

from utils import sql_connection_context
from llm_connector import LLMClient # Import the new LLMClient
from prompts import AGENT_CONSTITUTION
from plugins_folder.tools import ToolRegistry # Assuming ToolRegistry is in plugins_folder/tools.py


def get_utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


logger = logging.getLogger(__name__)


class Agent:
    def __init__(self, agent_id: int, name: str, role: str, tool_registry, llm_client: LLMClient):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.bdi_state = {"beliefs": {}, "desires": [], "intentions": []}
        self.tool_registry = tool_registry
        self.scratchpad = []  # Initialize scratchpad as an empty list
        self.llm = llm_client  # Store the LLMClient instance

    @classmethod
    async def load_from_db(cls, agent_id: int, tool_registry, llm_client: LLMClient):
        async with sql_connection_context() as (sql_server_conn, cursor):
            if cursor is None:
                raise RuntimeError("Failed to obtain database cursor for loading agent.")
            
            await asyncio.to_thread(
                cursor.execute,
                "SELECT AgentID, Name, Role, BDIState FROM Agents WHERE AgentID = ?",
                agent_id,
            )
            row = await asyncio.to_thread(cursor.fetchone)
            if row:
                agent_id, name, role, bdi_state_json = row
                agent = cls(agent_id, name, role, tool_registry, llm_client)
                if bdi_state_json:
                    agent.bdi_state = json.loads(bdi_state_json)
                return agent
            else:
                return None

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

    async def run(self, mission_prompt: str, log_id: int) -> dict:
        logger.info(f"Agent {self.name} starting mission: {mission_prompt}")
        self.scratchpad = [f"Mission: {mission_prompt}"] # Initialize scratchpad as a list
        final_answer = None

        for step in range(10):  # Max 10 steps for the cognitive loop
            # b. Reason: Construct a detailed system prompt.
            system_prompt = AGENT_CONSTITUTION
            # Add agent-specific persona to the system prompt
            persona_details = f"You are {self.name}, an AI agent with the role of {self.role}.\n"
            system_prompt = persona_details + system_prompt
            available_tools = ", ".join(self.tool_registry.get_tool_names())
            scratchpad_content = "\n".join(self.scratchpad)
            
            llm_prompt = (
                f"{system_prompt}"
                f"Overall Mission: {mission_prompt}\n"
                f"Available Tools: {available_tools}\n"
                f"Scratchpad History:\n{scratchpad_content}\n"
                "Your next response MUST be a JSON object with two keys: 'thought' (string) and 'action' (object). The 'action' object MUST have two keys: 'tool' (string, name of the tool to use) and 'query' (string, the input for the tool). If you have completed the mission, use the 'FinishTool' and provide the final answer as the query.\n"
                "Example: {\"thought\": \"I need to use the RAG tool to get more information.\", \"action\": {\"tool\": \"RAG Tool\", \"query\": \"information about X\"}}"
            )
            logger.info(f"LLM Prompt for step {step}:\n{llm_prompt}")

            # c. Call self.llm.invoke(prompt) to get the agent's next thought and action.
            llm_response_text = await self.llm.invoke(llm_prompt)
            logger.info(f"LLM Raw Response: {llm_response_text}")

            try:
                llm_response = json.loads(llm_response_text)
                thought = llm_response.get("thought")
                action = llm_response.get("action")

                if not thought or not action or "tool" not in action or "query" not in action:
                    raise ValueError("LLM response is not in the expected JSON format or missing keys.")

                tool_name = action["tool"]
                query_for_tool = action["query"]

                self.scratchpad.append(f"Thought: {thought}")

                # e. Act: If the chosen tool is FinishTool, break the loop and return the result.
                if tool_name == "FinishTool":
                    final_answer = query_for_tool
                    self.scratchpad.append(f"Final Answer: {final_answer}")
                    break
                else:
                    logger.info(f"Attempting to use tool: {tool_name} with query: {query_for_tool}")
                    tool_result = await self.tool_registry.use_tool(tool_name, query_for_tool)
                    observation = f"Observation: Tool Result ({tool_name}): {tool_result}"
                    logger.info(f"Tool '{tool_name}' executed. Result: {tool_result}")

                    # f. Observe: Append the tool's output (the "observation") to the scratchpad.
                    self.scratchpad.append(observation)

                    # Update BDI state (beliefs, desires, intentions can be updated based on tool results)
                    self.bdi_state["beliefs"].update({f"step_{step}_result": str(tool_result)})
                    await self.update_bdi_state(log_id, new_beliefs={f"step_{step}_result": str(tool_result)})

            except json.JSONDecodeError as e:
                error_message = f"Error decoding JSON from LLM response: {e}. Response: {llm_response_text}"
                self.scratchpad.append(f"Error: {error_message}")
                logger.error(error_message)
                break
            except ValueError as e:
                error_message = f"Error in ReAct loop (tool selection/execution): {e}"
                self.scratchpad.append(f"Error: {error_message}")
                logger.error(error_message)
                break
            except Exception as e:
                error_message = f"An unexpected error occurred: {e}"
                self.scratchpad.append(f"Error: {error_message}")
                logger.error(error_message)
                break

        if not final_answer:
            final_answer = "No final answer generated within the given steps." # Fallback

        # Reflect on the scratchpad and update beliefs
        summary_prompt = f"Please summarize the following mission scratchpad, focusing on key actions, observations, and outcomes. This summary will be used to update the agent's long-term beliefs.\n\nScratchpad:\n{\"\n\".join(self.scratchpad)}"
        mission_summary = await self.llm.invoke(summary_prompt)
        logger.info(f"Mission Summary for BDI update: {mission_summary}")

        # Update BDI state with the mission summary
        self.bdi_state["beliefs"].update({"last_mission_summary": mission_summary})
        await self.update_bdi_state(log_id, new_beliefs={"last_mission_summary": mission_summary})

        # Final update of BDI state with the overall outcome
        self.bdi_state["beliefs"].update({"final_mission_outcome": final_answer})
        await self.update_bdi_state(log_id, new_beliefs={"final_mission_outcome": final_answer})

        logger.info(f"Agent {self.name} completed mission with final answer: {final_answer}")
        return {"final_response": final_answer}


async def create_agent(agent_id: int, name: str, role: str, tool_registry, llm_client: LLMClient) -> Agent:
    """
    Creates and returns an Agent instance.
    """
    return Agent(agent_id, name, role, tool_registry, llm_client)