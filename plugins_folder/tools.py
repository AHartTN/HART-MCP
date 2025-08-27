import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List

from project_state import ProjectState

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def execute(self, **kwargs):
        pass


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool):
        self._tools[tool.name] = tool

    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    async def use_tool(self, tool_name: str, **kwargs):
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found.")
        return await tool.execute(**kwargs)


class RAGTool(BaseTool):
    @property
    def name(self) -> str:
        return "RAG Tool"

    async def execute(self, **kwargs) -> dict:
        query = kwargs.get("query")
        if not query:
            raise ValueError("RAGTool requires a 'query' parameter.")
        logger.info(f"RAGTool executing with query: {query}")
        # Fleshed out RAG simulation
        simulated_data = {
            "query": query,
            "response": f"Detailed RAG response for '{query}'. This includes synthesized information from various sources.",
            "sources": [
                {"title": "Source A", "url": "http://example.com/a"},
                {"title": "Source B", "url": "http://example.com/b"},
            ],
            "confidence": 0.85,
        }
        return simulated_data


class Thought:
    def __init__(self, text: str, score: float, children: List["Thought"] = None):
        self.text = text
        self.score = score
        self.children = children or []

    def to_dict(self):
        return {
            "text": self.text,
            "score": self.score,
            "children": [child.to_dict() for child in self.children],
        }


class TreeOfThoughtTool(BaseTool):
    @property
    def name(self) -> str:
        return "Tree of Thought Tool"

    async def execute(self, **kwargs) -> Thought:
        problem = kwargs.get("problem")
        if not problem:
            raise ValueError("TreeOfThoughtTool requires a 'problem' parameter.")
        logger.info(f"TreeOfThoughtTool executing with problem: {problem}")
        # Fleshed out ToT simulation
        root_thought = Thought(f"Root thought for: {problem}", 1.0)

        # Simulate branching thoughts
        child1 = Thought(f"Sub-thought 1: Analyze {problem} components", 0.7)
        child2 = Thought(f"Sub-thought 2: Brainstorm solutions for {problem}", 0.9)

        grandchild1_1 = Thought(f"Detailing component A of {problem}", 0.6)
        grandchild1_2 = Thought(f"Detailing component B of {problem}", 0.8)

        child1.children.extend([grandchild1_1, grandchild1_2])

        root_thought.children.extend([child1, child2])

        return root_thought


class FinishTool(BaseTool):
    @property
    def name(self) -> str:
        return "FinishTool"

    async def execute(self, **kwargs):
        response = kwargs.get("response")
        if not response:
            raise ValueError("FinishTool requires a 'response' parameter.")
        logger.info(f"FinishTool executing with response: {response}")
        return response


class DelegateToSpecialistTool(BaseTool):
    def __init__(self, specialist_agent):
        from plugins_folder.agent_core import SpecialistAgent

        self.specialist_agent: SpecialistAgent = specialist_agent

    @property
    def name(self) -> str:
        return "DelegateToSpecialistTool"

    async def execute(self, **kwargs) -> dict:
        mission_prompt = kwargs.get("mission_prompt")
        log_id = kwargs.get("log_id")

        if not mission_prompt:
            raise ValueError(
                "DelegateToSpecialistTool requires a 'mission_prompt' parameter."
            )

        logger.info(f"DelegateToSpecialistTool delegating mission: {mission_prompt}")
        # The update_callback is passed down to the specialist so its thoughts are streamed.
        result = await self.specialist_agent.run(
            mission_prompt,
            log_id=log_id,
            update_callback=self.specialist_agent.update_callback,
        )
        return result


class WriteToSharedStateTool(BaseTool):
    def __init__(self, project_state: ProjectState):
        self._project_state = project_state

    @property
    def name(self) -> str:
        return "WriteToSharedStateTool"

    async def execute(self, **kwargs):
        key = kwargs.get("key")
        value = kwargs.get("value")

        if not key:
            raise ValueError("Missing 'key' in data for WriteToSharedStateTool.")
        logger.info(f"Writing to shared state: key='{key}'")
        self._project_state.update_state(key, value)
        return f"Successfully wrote to shared state with key '{key}'."


class ReadFromSharedStateTool(BaseTool):
    def __init__(self, project_state: ProjectState):
        self._project_state = project_state

    @property
    def name(self) -> str:
        return "ReadFromSharedStateTool"

    async def execute(self, **kwargs):
        key = kwargs.get("key")
        if not key:
            raise ValueError("ReadFromSharedStateTool requires a 'key' parameter.")
        logger.info(f"Reading from shared state: key='{key}'")
        value = self._project_state.get_state(key)
        if value is None:
            return f"No value found for key '{key}' in shared state."
        # If the value is complex (dict, list), it should be serialized to be returned.
        # The agent framework should handle this, but good to be mindful.
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value


class SendClarificationTool(BaseTool):
    def __init__(self, project_state: ProjectState):
        self._project_state = project_state

    @property
    def name(self) -> str:
        return "SendClarificationTool"

    async def execute(self, **kwargs):
        query = kwargs.get("query")
        if not query:
            raise ValueError("SendClarificationTool requires a 'query' parameter.")
        logger.info(f"Sending clarification to orchestrator: {query}")
        self._project_state.update_state("clarification_for_orchestrator", query)
        return "Successfully sent clarification to orchestrator."


class CheckForClarificationsTool(BaseTool):
    def __init__(self, project_state: ProjectState):
        self._project_state = project_state

    @property
    def name(self) -> str:
        return "CheckForClarificationsTool"

    async def execute(self, **kwargs):
        query = kwargs.get("query")
        if not query:
            raise ValueError("CheckForClarificationsTool requires a 'query' parameter.")
        logger.info("Checking for clarifications from specialists.")
        clarification = self._project_state.get_state("clarification_for_orchestrator")
        if clarification:
            # Clear the clarification after reading it
            self._project_state.update_state("clarification_for_orchestrator", None)
            return f"Clarification from specialist: {clarification}"
        else:
            return "No clarifications from specialists."
