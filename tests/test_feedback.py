import pytest
from unittest.mock import AsyncMock, patch

# The client fixture is automatically provided by conftest.py


@pytest.mark.asyncio
async def test_feedback_submission_success(client):
    """
    Tests successful feedback submission to the /feedback endpoint.
    Mocks the underlying database interaction.
    """
    payload = {
        "log_id": 1,
        "feedback_text": "Great result!",
        "rating": 5,
        "feedback_type": "accuracy",
    }

    # Mock the database function that handles feedback submission
    with patch("db_connectors.update_agent_log_evaluation", new_callable=AsyncMock) as mock_update_agent_log_evaluation:
        mock_update_agent_log_evaluation.return_value = True # Simulate successful update

        response = client.post("/feedback", json=payload)

        assert response.status_code == 200
        json_data = response.json()
        assert "message" in json_data
        assert "Feedback received" in json_data["message"] # Corrected assertion

        # Verify that the database function was called with the correct arguments
        mock_update_agent_log_evaluation.assert_called_once()
        args, kwargs = mock_update_agent_log_evaluation.call_args
        # The first argument is the cursor, which is mocked internally by the endpoint
        # We are interested in the log_id and the new_entry dictionary
        assert args[1] == payload["log_id"]
        assert isinstance(args[2], dict)
        assert args[2]["feedback_text"] == payload["feedback_text"]
        assert args[2]["rating"] == payload["rating"]
        assert args[2]["feedback_type"] == payload["feedback_type"]
