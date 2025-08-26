import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio # Import asyncio

from cdc_consumer import process_change_log_entry, run_cdc_consumer
from config import MILVUS_COLLECTION # Assuming MILVUS_COLLECTION is needed for Milvus operations


# Helper for creating mock change entry
def create_mock_change_entry(change_id, source_table, source_id, change_type, payload):
    mock_entry = MagicMock()
    mock_entry.ChangeID = change_id
    mock_entry.SourceTable = source_table
    mock_entry.SourceID = source_id
    mock_entry.ChangeType = change_type
    mock_entry.Payload = json.dumps(payload)
    return mock_entry


@pytest.mark.asyncio # Mark as async
async def test_process_change_log_entry_chunk_insert(): # Make async
    """
    Tests that process_change_log_entry correctly handles a CHUNKS INSERT event.
    """
    mock_milvus_client = MagicMock()
    mock_neo4j_driver = MagicMock() # Not used in this specific test, but passed

    payload = {"ChunkID": "c1", "DocumentID": "d1", "Embedding": [0.1, 0.2, 0.3]}
    entry = create_mock_change_entry(1, "Chunks", "c1", "INSERT", payload)

    await process_change_log_entry(entry, mock_milvus_client, mock_neo4j_driver) # Await the call

    mock_milvus_client.upsert.assert_called_once_with( # Changed from insert to upsert
        data=[{"id": "c1", "embedding": [0.1, 0.2, 0.3], "document_id": "d1"}],
        collection_name=MILVUS_COLLECTION,
    )


@pytest.mark.asyncio
async def test_run_cdc_consumer_stops_after_one_iteration(mock_db_connection: MagicMock):
    """
    Tests that run_cdc_consumer processes one change and then stops,
    simulating a controlled loop termination.
    """
    # Mock SQL Server connection to return one change, then no more
    mock_cursor = AsyncMock()
    mock_db_connection.cursor.return_value.__aenter__.return_value = mock_cursor
    mock_cursor.fetchall.side_effect = [
        [create_mock_change_entry(1, "Chunks", "c1", "INSERT", {"ChunkID": "c1", "DocumentID": "d1", "Embedding": [0.1, 0.2, 0.3]})],
        [] # No more changes on subsequent calls
    ]

    # Mock Milvus and Neo4j clients for process_change_log_entry
    mock_milvus_client = MagicMock()
    mock_neo4j_driver = MagicMock()

    # Patch the actual get_milvus_client and get_neo4j_driver calls within run_cdc_consumer
    with patch("cdc_consumer.get_milvus_client", return_value=mock_milvus_client), \
         patch("cdc_consumer.get_neo4j_driver", return_value=mock_neo4j_driver): \

        # Patch asyncio.sleep to break the infinite loop after one iteration
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError] # Allow one sleep, then cancel

            try:
                await run_cdc_consumer()
            except asyncio.CancelledError:
                pass # Expected to stop the loop

    # Assert that process_change_log_entry was called once
    # For simplicity, we'll check the mock_milvus_client.upsert call
    mock_milvus_client.upsert.assert_called_once_with( # Changed from insert to upsert
        data=[{"id": "c1", "embedding": [0.1, 0.2, 0.3], "document_id": "d1"}],
        collection_name=MILVUS_COLLECTION,
    )
    # Verify that the SQL query to fetch changes was executed
    mock_cursor.execute.assert_called_once()
    assert "SELECT ChangeID, SourceTable, SourceID, ChangeType, Payload FROM ChangeLog" in mock_cursor.execute.call_args[0][0]
