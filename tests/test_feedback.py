# In tests/test_feedback.py
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_feedback_submission_success(client: TestClient, mock_sql_connection: MagicMock):
    """
    Tests successful feedback submission to the /feedback endpoint.
    """
    # Arrange
    payload = {
        "log_id": 1,
        "feedback_text": "Great result!",
        "rating": 5,
        "feedback_type": "accuracy",
    }

    # Act
    response = client.post("/feedback", json=payload)

    # Assert
    response.raise_for_status()
    assert response.json() == {"message": "Feedback received and logged successfully."}


def test_feedback_submission_db_error(
    client: TestClient, mock_sql_connection: MagicMock
):
    """
    Tests how the /feedback endpoint handles a database error during submission.
    """
    # Arrange
    payload = {
        "log_id": 1,
        "feedback_text": "This will fail.",
        "rating": 1,
        "feedback_type": "error",
    }
    mock_sql_connection.cursor.return_value.execute.side_effect = Exception(
        "DB error"
    )

    # Act
    response = client.post("/feedback", json=payload)

    # Assert
    assert response.status_code == 500
    assert "Failed to log feedback" in response.text