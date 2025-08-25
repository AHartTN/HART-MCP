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
    def __init__(self, agent_id: int, name: str, role: str, tool_registry):
        self.agent_id = agent_id
        self.name = name
        self.role = role
        self.bdi_state = {"beliefs": {}, "desires": [], "intentions": []}
        self.tool_registry = tool_registry

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
        scratchpad = []
        final_answer = None

        # Fleshed out LLM for tool selection and reasoning
        async def simulate_llm_reasoning(current_mission, available_tools, scratchpad_content):
            reasoning = ""
            tool_to_use = ""
            query_for_tool = ""
            final_answer = ""

            # Step 1: Analyze current state based on scratchpad
            if not scratchpad_content:
                reasoning = f"The mission '{current_mission}' has just started. I need to generate a high-level plan to address it. The 'Tree of Thought Tool' is suitable for this purpose."
                tool_to_use = "Tree of Thought Tool"
                query_for_tool = current_mission
            elif "Root thought for:" in scratchpad_content and "Detailed RAG response for" not in scratchpad_content:
                reasoning = "A high-level plan (Tree of Thought) has been generated. Now I need to gather detailed information related to this plan using the 'RAG Tool'."
                # Extract the plan from the scratchpad
                plan_line = next((line for line in scratchpad_content.split('\n') if "Root thought for:" in line), "")
                plan_query = plan_line.replace("Tool Result (Tree of Thought Tool): ", "").replace("Root thought for: ", "").strip()
                query_for_tool = plan_query
                tool_to_use = "RAG Tool"
            elif "Detailed RAG response for" in scratchpad_content:
                reasoning = "I have gathered detailed information using the RAG Tool. I should now be able to formulate a final answer based on the mission and the retrieved data."
                final_answer = f"Mission '{current_mission}' completed. Final answer based on RAG data: {scratchpad_content}"
            else:
                reasoning = "Current state is unclear or requires further analysis. I will try to use the RAG tool to get more information."
                tool_to_use = "RAG Tool"
                query_for_tool = current_mission # Fallback

            logger.info(f"LLM Reasoning: {reasoning}")

            response_parts = []
            if tool_to_use:
                response_parts.append(f"Tool: {tool_to_use}")
                response_parts.append(f"Query: {query_for_tool}")
            if final_answer:
                response_parts.append(f"Final Answer: {final_answer}")

            return " | ".join(response_parts)

        for step in range(5):  # Max 5 steps for the cognitive loop
            scratchpad_content = "\n".join(scratchpad)
            llm_response = await simulate_llm_reasoning(
                mission_prompt, self.tool_registry._tools.values(), scratchpad_content
            )
            logger.info(f"LLM Response: {llm_response}")

            if "Final Answer:" in llm_response:
                final_answer = llm_response.split("Final Answer:", 1)[1].strip()
                scratchpad.append(f"Final Answer: {final_answer}")
                break

            try:
                tool_part, query_part = llm_response.split(" | Query: ", 1)
                tool_name = tool_part.replace("Tool: ", "").strip()
                query_for_tool = query_part.strip()

                # Act: Use the tool
                tool_result = await self.tool_registry.use_tool(tool_name, query_for_tool)
                logger.info(f"Tool '{tool_name}' executed. Result: {tool_result}")

                # Observe: Append result to scratchpad
                scratchpad.append(f"Tool Result ({tool_name}): {tool_result}")

                # Update BDI state (beliefs, desires, intentions can be updated based on tool results)
                # For simplicity, we'll just update beliefs with the latest tool result
                self.bdi_state["beliefs"].update({f"step_{step}_result": str(tool_result)})
                await self.update_bdi_state(log_id, new_beliefs={f"step_{step}_result": str(tool_result)})

            except ValueError as e:
                scratchpad.append(f"Error parsing LLM response or using tool: {e}")
                logger.error(f"Error in ReAct loop: {e}")
                break

        if not final_answer:
            final_answer = "No final answer generated within the given steps." # Fallback

        # Final update of BDI state with the overall outcome
        self.bdi_state["beliefs"].update({"final_mission_outcome": final_answer})
        await self.update_bdi_state(log_id, new_beliefs={"final_mission_outcome": final_answer})

        logger.info(f"Agent {self.name} completed mission with final answer: {final_answer}")
        return {"final_response": final_answer}


async def create_agent(agent_id: int, name: str, role: str, tool_registry) -> Agent:
    """
    Creates and returns an Agent instance.
    """
    return Agent(agent_id, name, role, tool_registry)
