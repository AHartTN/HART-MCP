from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient  # Import TestClient from fastapi.testclient

from server import app  # Import the main FastAPI app
from utils import chunk_text


# --- Fixtures ---
@pytest.fixture
def client():
    # Use FastAPI's TestClient
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_ingest_dependencies():
    with (
        patch("routes.ingest.allowed_file", return_value=True) as mock_allowed_file,
        patch(
            "routes.ingest.extract_text",
            return_value="This is a test document with some content to be chunked.",
        ) as mock_extract_text,
        patch("routes.ingest.get_sql_server_connection") as mock_get_sql_conn,
        patch(
            "routes.ingest.os.path.join", return_value="/mocked/path/test_file.txt"
        ) as mock_os_path_join,
        patch("routes.ingest.logger") as mock_logger,
        # No need to patch werkzeug.datastructures.FileStorage.save for FastAPI
    ):  # Add this line
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_sql_conn.return_value = mock_conn

        yield {
            "mock_allowed_file": mock_allowed_file,
            "mock_extract_text": mock_extract_text,
            "mock_get_sql_conn": mock_get_sql_conn,
            "mock_conn": mock_conn,
            "mock_cursor": mock_cursor,
            "mock_os_path_join": mock_os_path_join,
            "mock_logger": mock_logger,
        }


# --- Tests for chunk_text --- (These are fine, no changes needed)
def test_chunk_text_basic():
    text = "This is a test sentence. It has multiple words. We will chunk it."
    chunks = chunk_text(text, chunk_size=5, overlap=0)
    assert len(chunks) == 3
    assert chunks[0] == "This is a test sentence."
    assert chunks[1] == "It has multiple words. We"
    assert chunks[2] == "will chunk it."


def test_chunk_text_with_overlap():
    text = "The quick brown fox jumps over the lazy dog."
    chunks = chunk_text(text, chunk_size=5, overlap=2)
    assert len(chunks) == 3
    assert chunks[0] == "The quick brown fox jumps"
    assert chunks[1] == "fox jumps over the lazy"
    assert chunks[2] == "the lazy dog."


def test_chunk_text_empty():
    chunks = chunk_text("")
    assert chunks == []


def test_chunk_text_small_text_large_chunk_size():
    text = "Short text."
    chunks = chunk_text(text, chunk_size=100)
    assert len(chunks) == 1
    assert chunks[0] == "Short text."


# --- Tests for ingest_document ---
async def test_ingest_document_success(client, mock_ingest_dependencies):  # Make async
    mock_conn = mock_ingest_dependencies["mock_conn"]
    mock_cursor = mock_ingest_dependencies["mock_cursor"]
    

    # Mock the async methods of the cursor and connection
    mock_cursor.execute.return_value = None  # Mock execute to return None
    mock_cursor.fetchall.return_value = []  # Mock fetchall to return empty list
    mock_conn.commit.return_value = None  # Mock commit to return None

    # For FastAPI, file uploads are handled differently.
    # Use files parameter for multipart/form-data
    files = {"file": ("test.txt", BytesIO(b"dummy content"), "text/plain")}
    response = await client.post(
        "/ingest", files=files
    )  # Use await for async client post

    assert response.status_code == 200  # Expect 200 OK for success
    json_data = response.json()
    assert json_data.get("message") == "File ingested successfully"
    assert json_data["filename"] == "test.txt"  # Filename from files dict
    assert "document_id" in json_data
    assert (
        json_data["ingested_chunks"] == 1
    )  # Based on default mock_extract_text content and chunk_size=500

    # Verify SQL Server calls (adjusting for async mocks)
    # The actual calls will be wrapped in asyncio.to_thread, so direct mock.call_args_list might be tricky
    # Instead, we can check if the underlying methods were called.
    mock_cursor.execute.assert_called()
    mock_conn.commit.assert_called()


async def test_ingest_document_no_file_part(client):  # Make async
    response = await client.post("/ingest", data={})  # Use await
    assert response.status_code == 400
    assert response.json() == {
        "detail": "Field required"
    }  # FastAPI's default error for missing file


async def test_ingest_document_no_selected_file(client):  # Make async
    files = {"file": ("", BytesIO(b""), "text/plain")}  # Empty filename and content
    response = await client.post("/ingest", files=files)  # Use await
    assert response.status_code == 400
    assert response.json() == {
        "error": "File type not allowed"
    }  # Assuming allowed_file returns False for empty filename


async def test_ingest_document_disallowed_file_type(
    client, mock_ingest_dependencies
):  # Make async
    mock_ingest_dependencies["mock_allowed_file"].return_value = False
    files = {
        "file": ("test.exe", BytesIO(b"dummy content"), "application/octet-stream")
    }
    response = await client.post("/ingest", files=files)  # Use await
    assert response.status_code == 400  # Expect 400 for disallowed file type
    json_data = response.json()
    assert json_data == {"error": "File type not allowed"}


async def test_ingest_document_extract_text_failure(
    client, mock_ingest_dependencies
):  # Make async
    mock_ingest_dependencies["mock_extract_text"].return_value = None
    files = {"file": ("test.txt", BytesIO(b"dummy content"), "text/plain")}
    response = await client.post("/ingest", files=files)  # Use await
    assert response.status_code == 500  # Expect 500 for extraction failure
    json_data = response.json()
    assert json_data == {"error": "Failed to extract text from file."}


async def test_ingest_document_sql_server_connection_failure(  # Make async
    client, mock_ingest_dependencies
):
    mock_ingest_dependencies["mock_get_sql_conn"].side_effect = Exception(
        "Connection failed"
    )  # Simulate connection failure
    files = {"file": ("test.txt", BytesIO(b"dummy content"), "text/plain")}
    response = await client.post("/ingest", files=files)  # Use await
    assert response.status_code == 500  # Expect 500 for connection failure
    json_data = response.json()
    assert json_data.get("error") == "Failed to connect to SQL Server for ingestion."


# Use MagicMock and patch only within this test file
# Do not expect endpoint code to compensate for test logic
