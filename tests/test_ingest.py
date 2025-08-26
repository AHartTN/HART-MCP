from io import BytesIO
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# The client fixture is automatically provided by conftest.py
from utils import chunk_text # Keep existing chunk_text tests
# No need to import TestClient or define client fixture here


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
@pytest.mark.asyncio
async def test_ingest_document_success(client):
    """
    Tests successful document ingestion to the /ingest endpoint.
    Mocks external dependencies like text extraction and database operations.
    """
    mock_file_content = "This is a test document with some content to be chunked."
    mock_extracted_text = "This is a test document with some content to be chunked."

    with patch("utils.extract_text", new_callable=AsyncMock, return_value=mock_extracted_text), \
         patch("db_connectors.get_sql_server_connection", new_callable=AsyncMock) as mock_get_sql_server_connection, \
         patch("db_connectors.insert_document", new_callable=AsyncMock) as mock_insert_document, \
         patch("db_connectors.insert_chunk", new_callable=AsyncMock) as mock_insert_chunk:

        # Configure mock_get_sql_server_connection to return a mock connection with a mock cursor
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_sql_server_connection.return_value = mock_conn

        files = {"file": ("test.txt", BytesIO(mock_file_content.encode("utf-8")), "text/plain")}
        response = client.post("/ingest", files=files)

        assert response.status_code == 200
        json_data = response.json()
        assert json_data.get("message") == "File ingested successfully"
        assert json_data["filename"] == "test.txt"
        assert "document_id" in json_data
        assert json_data["ingested_chunks"] > 0 # Expect at least one chunk

        mock_insert_document.assert_called_once()
        mock_insert_chunk.assert_called() # Called for each chunk
        mock_conn.commit.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_document_failure_extract_text(client):
    """
    Tests document ingestion failure when text extraction fails.
    """
    with patch("utils.extract_text", new_callable=AsyncMock, return_value=None): # Simulate extraction failure
        files = {"file": ("test.txt", BytesIO(b"dummy content"), "text/plain")}
        response = client.post("/ingest", files=files)

        assert response.status_code == 500
        json_data = response.json() # Get json_data here
        assert json_data.get("error") == "Failed to extract text from file."


@pytest.mark.asyncio
async def test_ingest_document_failure_db_connection(client):
    """
    Tests document ingestion failure when database connection cannot be established.
    """
    mock_file_content = "This is a test document."
    mock_extracted_text = "This is a test document."

    with patch("utils.extract_text", new_callable=AsyncMock, return_value=mock_extracted_text), \
         patch("db_connectors.get_sql_server_connection", new_callable=AsyncMock, return_value=None): # Simulate DB connection failure

        files = {"file": ("test.txt", BytesIO(mock_file_content.encode("utf-8")), "text/plain")}
        response = client.post("/ingest", files=files)

        assert response.status_code == 500
        json_data = response.json() # Get json_data here
        assert json_data.get("error") == "Failed to connect to SQL Server for ingestion."
