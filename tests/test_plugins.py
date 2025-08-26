import pytest
from unittest.mock import AsyncMock, MagicMock
import json # Import json

from plugins_folder.tools import ToolRegistry, DelegateToSpecialistTool, FinishTool
from plugins_folder.agent_core import SpecialistAgent


@pytest.mark.asyncio
async def test_tool_registry_registration_and_execution():
    """
    Tests that tools can be registered with the ToolRegistry and executed.
    """
    registry = ToolRegistry()

    # Create a simple mock tool
    mock_tool = MagicMock()
    mock_tool.name = "MockTool"
    mock_tool.execute = AsyncMock(return_value="MockTool executed successfully")

    registry.register_tool(mock_tool)

    # Assert that the tool is registered
    assert "MockTool" in registry.get_tool_names()

    # Execute the tool and assert its return value
    result = await registry.use_tool("MockTool", "test query")
    assert result == "MockTool executed successfully"
    mock_tool.execute.assert_called_once_with("test query")


@pytest.mark.asyncio
async def test_delegate_to_specialist_tool_execution():
    """
    Tests that DelegateToSpecialistTool correctly calls the SpecialistAgent's run method.
    """
    mock_specialist_agent = AsyncMock(spec=SpecialistAgent)
    mock_specialist_agent.run.return_value = {"final_response": "Delegated task completed."}
    mock_specialist_agent.update_callback = AsyncMock() # Added update_callback

    delegate_tool = DelegateToSpecialistTool(specialist_agent=mock_specialist_agent)

    mission_prompt = "Perform this sub-task."
    log_id = 123 # Example log_id
    # Pass a JSON string with mission_prompt and log_id
    query_json = json.dumps({"mission_prompt": mission_prompt, "log_id": log_id})

    result = await delegate_tool.execute(query_json)

    mock_specialist_agent.run.assert_awaited_once_with(
        mission_prompt,
        log_id=log_id,
        update_callback=mock_specialist_agent.update_callback
    )
    assert result == {"final_response": "Delegated task completed."}