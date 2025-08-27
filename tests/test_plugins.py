# In tests/test_plugins.py
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from plugins_folder.agent_core import SpecialistAgent
from plugins_folder.tools import DelegateToSpecialistTool, ToolRegistry


@pytest.mark.asyncio
async def test_tool_registry_registration_and_execution():
    """
    Tests that tools can be registered with the ToolRegistry and executed.
    """
    # Arrange
    registry = ToolRegistry()
    mock_tool = MagicMock()
    mock_tool.name = "MockTool"
    mock_tool.execute = AsyncMock(return_value="MockTool executed successfully")

    # Act
    registry.register_tool(mock_tool)
    result = await registry.use_tool("MockTool", "test query")

    # Assert
    assert "MockTool" in registry.get_tool_names()
    assert result == "MockTool executed successfully"


@pytest.mark.asyncio
async def test_delegate_to_specialist_tool_execution():
    """
    Tests that DelegateToSpecialistTool correctly calls the SpecialistAgent's run method.
    """
    # Arrange
    mock_specialist_agent = AsyncMock(spec=SpecialistAgent)
    mock_specialist_agent.run.return_value = {
        "final_response": "Delegated task completed."
    }
    delegate_tool = DelegateToSpecialistTool(specialist_agent=mock_specialist_agent)
    mission_prompt = "Perform this sub-task."
    log_id = 123
    query_json = json.dumps({"mission_prompt": mission_prompt, "log_id": log_id})

    # Act
    result = await delegate_tool.execute(query_json)

    # Assert
    mock_specialist_agent.run.assert_awaited_once_with(
        mission_prompt, log_id=log_id, update_callback=delegate_tool.update_callback
    )
    assert result == {"final_response": "Delegated task completed."}