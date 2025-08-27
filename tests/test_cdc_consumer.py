# In tests/test_cdc_consumer.py
import asyncio
import json
from unittest.mock import MagicMock, AsyncMock

import pytest

from cdc_consumer import process_change_log_entry, run_cdc_consumer
from config import MILVUS_COLLECTION


def create_mock_change_entry(change_id, source_table, source_id, change_type, payload):
    """Helper to create a mock change log entry with a JSON payload."""
    mock_entry = MagicMock()
    mock_entry.ChangeID = change_id
    mock_entry.SourceTable = source_table
    mock_entry.SourceID = source_id
    mock_entry.ChangeType = change_type
    mock_entry.Payload = json.dumps(payload)
    return mock_entry


@pytest.mark.asyncio
async def test_process_change_log_entry_chunk_insert(
    mock_milvus_client: MagicMock, mock_neo4j_driver: MagicMock
):
    """
    Tests that process_change_log_entry correctly handles a CHUNKS INSERT event.
    """
    # Arrange
    payload = {"ChunkID": "c1", "DocumentID": "d1", "Embedding": [0.1, 0.2, 0.3]}
    entry = create_mock_change_entry(1, "Chunks", "c1", "INSERT", payload)

    # Act
    await process_change_log_entry(entry, mock_milvus_client, mock_neo4j_driver)

    # Assert
    mock_milvus_client.upsert.assert_called_once_with(
        data=[{"id": "c1", "embedding": [0.1, 0.2, 0.3], "document_id": "d1"}],
        collection_name=MILVUS_COLLECTION,
    )


@pytest.mark.asyncio
async def test_run_cdc_consumer_single_pass(
    mock_sql_connection: MagicMock,
    mock_milvus_client: MagicMock,
    mock_neo4j_driver: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
):
    """
    Tests that run_cdc_consumer processes changes in a single pass.
    """
    # Arrange
    mock_cursor = AsyncMock()
    mock_sql_connection.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        (1, "Chunks", "c1", "INSERT", json.dumps({"ChunkID": "c1", "DocumentID": "d1", "Embedding": [0.1, 0.2, 0.3]}))
    ]

    monkeypatch.setattr("cdc_consumer.get_milvus_client", lambda: mock_milvus_client)
    monkeypatch.setattr("cdc_consumer.get_neo4j_driver", lambda: mock_neo4j_driver)
    monkeypatch.setattr("db_connectors.get_sql_server_connection", lambda: mock_sql_connection)

    # Act
    await run_cdc_consumer()

    # Assert
    mock_milvus_client.upsert.assert_called_once_with(
        data=[{"id": "c1", "embedding": [0.1, 0.2, 0.3], "document_id": "d1"}],
        collection_name=MILVUS_COLLECTION,
    )