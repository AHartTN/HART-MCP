# In tests/test_ingest.py
from io import BytesIO
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_ingest_file_success(client: TestClient, mock_sql_connection: MagicMock):
    """
    Tests the /ingest endpoint's happy path for a single file.
    """
    # Arrange
    file_content = b"This is the content of the test file."

    # Act
    response = client.post(
        "/ingest",
        files={"file": ("test.txt", file_content, "text/plain")},
    )

    # Assert
    response.raise_for_status()
    json_data = response.json()

    assert json_data["message"] == "File ingested successfully"
    assert json_data["filename"] == "test.txt"
    assert "document_id" in json_data
    assert json_data["ingested_chunks"] > 0


def test_ingest_no_file(client: TestClient):
    """
    Tests that the /ingest endpoint returns an error if no file is provided.
    """
    # Arrange (no file)

    # Act
    response = client.post("/ingest", files={})

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "No file uploaded."}


def test_ingest_db_error(client: TestClient, mock_sql_connection: MagicMock):
    """
    Tests how the /ingest endpoint handles a database error during ingestion.
    """
    # Arrange
    file_content = b"This is the content of the test file."
    mock_sql_connection.cursor.return_value.execute.side_effect = Exception(
        "DB error"
    )

    # Act
    response = client.post(
        "/ingest",
        files={"file": ("test.txt", file_content, "text/plain")},
    )

    # Assert
    assert response.status_code == 500
    assert "Failed to ingest file" in response.text