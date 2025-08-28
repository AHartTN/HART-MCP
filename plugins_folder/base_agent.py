import asyncio
import datetime
import json
import logging
from typing import Callable, Dict, List, Optional
from abc import ABC, abstractmethod

from llm_connector import LLMClient
from project_state import ProjectState
from plugins_folder.tools import ToolRegistry
from utils import sql_connection_context
from utils.error_handlers import ErrorCode, safe_execute, StandardizedError


def get_utc_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Enhanced base agent with improved error handling and modular design."""
    
    def __init__(
        self,
        agent_id: int,
        name: str,
        role: str,
        tool_registry: ToolRegistry,
        llm_client: LLMClient,
        update_callback: Optional[Callable] = None,
        project_state: Optional[ProjectState] = None,
        max_steps: int = 10,
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
        self.max_steps = max_steps
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Enhanced state tracking
        self.execution_history = []
        self.current_mission = None
        self.performance_metrics = {
            "missions_completed": 0,
            "missions_failed": 0,
            "average_steps": 0,
            "tools_used": {}
        }

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
                    )
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

    @safe_execute(ErrorCode.AGENT_EXECUTION)
    async def run(
        self,
        mission_prompt: str,
        log_id: int,
        system_prompt_template: str,
        update_callback_type_prefix: str,
    ) -> dict:
        """Enhanced agent execution with robust error handling and performance tracking."""
        self.current_mission = mission_prompt
        start_time = datetime.datetime.now()
        
        self._logger.info(f"Agent {self.name} starting mission: {mission_prompt}")
        self.scratchpad = [f"Mission: {mission_prompt}"]
        final_answer = None
        step = 0

        if self.update_callback:
            await self.update_callback({
                "type": f"{update_callback_type_prefix}_mission_start",
                "content": mission_prompt,
                "agent_name": self.name,
            })

        try:
            for step in range(self.max_steps):
                # Defensive check - ensure system_prompt_template is a string
                if not isinstance(system_prompt_template, str):
                    self._logger.error(f"system_prompt_template is not a string: {type(system_prompt_template)} = {system_prompt_template}")
                    system_prompt_template = (
                        "You are {name}, an AI agent with the role of {role}. "
                        "You must always respond with a JSON object containing a 'thought' and an 'action'. "
                        "The 'action' must contain a 'tool_name' and 'parameters'."
                    )
                
                self._logger.debug(f"system_prompt_template type: {type(system_prompt_template)}")
                self._logger.debug(f"system_prompt_template content: {system_prompt_template[:100]}...")
                
                try:
                    system_prompt = system_prompt_template.format(name=self.name, role=self.role)
                except KeyError as e:
                    self._logger.error(f"KeyError in system_prompt_template.format(): {e}")
                    self._logger.error(f"system_prompt_template content: {repr(system_prompt_template)}")
                    # Use fallback template
                    system_prompt_template = (
                        "You are {name}, an AI agent with the role of {role}. "
                        "You must always respond with a JSON object containing a 'thought' and an 'action'. "
                        "The 'action' must contain a 'tool_name' and 'parameters'."
                    )
                    system_prompt = system_prompt_template.format(name=self.name, role=self.role)
                available_tools = ", ".join(self.tool_registry.get_tool_names())
                scratchpad_content = "\n".join(self.scratchpad[-5:])  # Limit context

                llm_prompt = f"""{system_prompt}
Overall Mission: {mission_prompt}
Available Tools: {available_tools}
Recent Progress:
{scratchpad_content}

Respond with VALID JSON only:
{{"thought": "your reasoning here", "action": {{"tool_name": "tool_name", "parameters": {{}}}}}}

Use "finish" tool when complete: {{"thought": "Mission completed", "action": {{"tool_name": "finish", "parameters": {{"response": "final answer"}}}}}}"""

                if self.update_callback:
                    await self.update_callback({
                        "type": f"{update_callback_type_prefix}_thought_process",
                        "content": f"Step {step}: Reasoning...",
                        "agent_name": self.name,
                    })

                # Get LLM response with enhanced error handling
                llm_response_text = await self._get_llm_response(llm_prompt)
                if not llm_response_text:
                    break

                # Parse and validate response
                parsed_response = self._parse_llm_response(llm_response_text)
                if not parsed_response:
                    break

                thought = parsed_response["thought"]
                action = parsed_response["action"]
                tool_name = action["tool_name"]
                parameters_for_tool = action["parameters"]

                # Record thought
                self.scratchpad.append(f"Step {step} - Thought: {thought}")
                if self.update_callback:
                    await self.update_callback({
                        "type": f"{update_callback_type_prefix}_thought", 
                        "content": thought, 
                        "agent_name": self.name
                    })

                # Handle finish condition
                if tool_name == "finish":
                    final_answer = parameters_for_tool.get("response") or parameters_for_tool.get("result", "Mission completed")
                    self.scratchpad.append(f"Final Answer: {final_answer}")
                    if self.update_callback:
                        await self.update_callback({
                            "type": f"{update_callback_type_prefix}_final_answer",
                            "content": final_answer,
                            "agent_name": self.name,
                        })
                    break

                # Execute tool
                success = await self._execute_tool(
                    tool_name, parameters_for_tool, step, log_id, update_callback_type_prefix
                )
                if not success:
                    break

        except Exception as e:
            error_msg = f"Critical error in agent execution: {e}"
            self._logger.error(error_msg, exc_info=True)
            if self.update_callback:
                await self.update_callback({
                    "type": f"{update_callback_type_prefix}_error",
                    "content": error_msg,
                    "agent_name": self.name,
                })

        # Finalize mission
        return await self._finalize_mission(final_answer, log_id, start_time, step)

    async def _get_llm_response(self, prompt: str) -> str:
        """Get LLM response with retry logic."""
        try:
            response = await self.llm.invoke(prompt)
            self._logger.debug(f"LLM Response length: {len(response)} chars")
            return response.strip()
        except Exception as e:
            self._logger.error(f"LLM invocation failed: {e}")
            return ""

    def _parse_llm_response(self, response_text: str) -> dict:
        """Parse LLM response with robust error handling."""
        try:
            # Clean the response
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            parsed = json.loads(cleaned)
            
            # Validate structure
            if not isinstance(parsed, dict):
                raise ValueError("Response must be a JSON object")
            
            if "thought" not in parsed or "action" not in parsed:
                raise ValueError("Missing required keys: thought, action")
            
            action = parsed["action"]
            if not isinstance(action, dict) or "tool_name" not in action or "parameters" not in action:
                raise ValueError("Invalid action structure")

            return parsed

        except (json.JSONDecodeError, ValueError) as e:
            self._logger.error(f"JSON parsing failed: {e}. Response: {response_text[:200]}...")
            
            # Try to extract meaningful parts for fallback
            if "finish" in response_text.lower():
                return {
                    "thought": "Attempting to complete mission",
                    "action": {"tool_name": "finish", "parameters": {"response": "Mission completed with parsing issues"}}
                }
            
            return None

    async def _execute_tool(self, tool_name: str, parameters: dict, step: int, log_id: int, callback_prefix: str) -> bool:
        """Execute tool with comprehensive error handling."""
        try:
            self._logger.info(f"Step {step}: Using tool {tool_name} with params: {list(parameters.keys())}")
            
            if self.update_callback:
                await self.update_callback({
                    "type": f"{callback_prefix}_action",
                    "content": {"tool_name": tool_name, "parameters": parameters},
                    "agent_name": self.name,
                })

            # Execute tool
            tool_result = await self.tool_registry.use_tool(tool_name, **parameters)
            
            # Record result
            observation = f"Step {step} - Tool {tool_name} result: {str(tool_result)[:200]}..."
            self.scratchpad.append(observation)
            
            if self.update_callback:
                await self.update_callback({
                    "type": f"{callback_prefix}_observation",
                    "content": observation,
                    "agent_name": self.name,
                })

            # Update BDI state
            self.bdi_state["beliefs"][f"step_{step}_result"] = str(tool_result)[:500]
            await self.update_bdi_state(log_id, new_beliefs={f"step_{step}_result": str(tool_result)[:500]})
            
            # Track tool usage
            if tool_name not in self.performance_metrics["tools_used"]:
                self.performance_metrics["tools_used"][tool_name] = 0
            self.performance_metrics["tools_used"][tool_name] += 1

            return True

        except Exception as e:
            error_msg = f"Tool execution failed - {tool_name}: {e}"
            self._logger.error(error_msg, exc_info=True)
            self.scratchpad.append(f"Error: {error_msg}")
            
            if self.update_callback:
                await self.update_callback({
                    "type": f"{callback_prefix}_error",
                    "content": error_msg,
                    "agent_name": self.name,
                })
            
            return False

    async def _finalize_mission(self, final_answer: str, log_id: int, start_time: datetime.datetime, steps_taken: int) -> dict:
        """Finalize mission with comprehensive reporting."""
        if not final_answer:
            final_answer = f"Mission incomplete after {steps_taken} steps. Check logs for details."

        # Generate mission summary
        scratchpad_text = "\n".join(self.scratchpad)
        try:
            summary_prompt = f"""Summarize this agent mission focusing on key actions and outcomes:

{scratchpad_text}

Provide a concise summary in 2-3 sentences."""
            
            mission_summary = await self.llm.invoke(summary_prompt)
        except Exception as e:
            mission_summary = f"Mission summary generation failed: {e}"

        # Update performance metrics
        duration = (datetime.datetime.now() - start_time).total_seconds()
        if final_answer and "incomplete" not in final_answer.lower():
            self.performance_metrics["missions_completed"] += 1
        else:
            self.performance_metrics["missions_failed"] += 1
        
        total_missions = self.performance_metrics["missions_completed"] + self.performance_metrics["missions_failed"]
        if total_missions > 0:
            self.performance_metrics["average_steps"] = (
                self.performance_metrics["average_steps"] * (total_missions - 1) + steps_taken
            ) / total_missions

        # Update BDI state
        self.bdi_state["beliefs"].update({
            "last_mission_summary": mission_summary,
            "final_mission_outcome": final_answer,
            "mission_duration_seconds": duration,
            "steps_taken": steps_taken
        })
        
        await self.update_bdi_state(log_id, new_beliefs={
            "last_mission_summary": mission_summary,
            "final_mission_outcome": final_answer
        })

        # Record execution history
        self.execution_history.append({
            "mission": self.current_mission,
            "result": final_answer,
            "duration": duration,
            "steps": steps_taken,
            "timestamp": datetime.datetime.now().isoformat()
        })

        # Keep only last 10 missions in history
        if len(self.execution_history) > 10:
            self.execution_history = self.execution_history[-10:]

        self._logger.info(f"Agent {self.name} completed mission. Duration: {duration:.2f}s, Steps: {steps_taken}")
        
        return {
            "final_response": final_answer,
            "mission_summary": mission_summary,
            "duration_seconds": duration,
            "steps_taken": steps_taken,
            "performance_metrics": self.performance_metrics.copy()
        }

    async def get_agent_status(self) -> dict:
        """Get comprehensive agent status."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role,
            "current_mission": self.current_mission,
            "bdi_state": self.bdi_state,
            "performance_metrics": self.performance_metrics,
            "recent_executions": self.execution_history[-3:],
            "available_tools": self.tool_registry.get_tool_names() if self.tool_registry else []
        }
