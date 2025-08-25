import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cdc_consumer import process_change_log_entry, run_cdc_consumer
from config import MILVUS_COLLECTION


# Mock database connection functions
@pytest.fixture
def mock_db_connections():
    # SQL Server Connection
    mock_cursor = MagicMock()
    mock_sql_conn_instance = MagicMock()
    mock_sql_conn_instance.cursor.return_value = mock_cursor

    # Milvus Client
    mock_milvus_client_instance = MagicMock()
    mock_milvus_client_instance.insert = MagicMock()
    mock_milvus_client_instance.upsert = MagicMock()
    mock_milvus_client_instance.delete = MagicMock()

    # Neo4j Driver
    mock_neo4j_session = MagicMock()
    mock_neo4j_driver_instance = MagicMock()
    mock_neo4j_driver_instance.session.return_value.__enter__.return_value = (
        mock_neo4j_session
    )
    mock_neo4j_driver_instance.verify_connectivity = MagicMock()

    yield (
        mock_sql_conn_instance,
        mock_milvus_client_instance,
        mock_neo4j_driver_instance,
    )


# --- Helper for creating mock change entry ---
def create_mock_change_entry(change_id, source_table, source_id, change_type, payload):
    return type(
        "ChangeEntry",
        (object,),
        {
            "ChangeID": change_id,
            "SourceTable": source_table,
            "SourceID": source_id,
            "ChangeType": change_type,
            "Payload": json.dumps(payload),
        },
    )


# --- Tests for process_change_log_entry ---
def test_process_chunk_insert(mock_db_connections):
    _, mock_milvus_client, _ = mock_db_connections
    payload = {"ChunkID": "c1", "DocumentID": "d1", "Embedding": [0.1, 0.2, 0.3]}
    entry = create_mock_change_entry(1, "Chunks", "c1", "INSERT", payload)

    process_change_log_entry(entry, mock_milvus_client, MagicMock())

    mock_milvus_client.insert.assert_called_once_with(
        data=[{"id": "c1", "embedding": [0.1, 0.2, 0.3], "document_id": "d1"}],
        collection_name=MILVUS_COLLECTION,
    )


def test_process_chunk_update(mock_db_connections):
    _, mock_milvus_client, _ = mock_db_connections
    payload = {"ChunkID": "c1", "DocumentID": "d1", "Embedding": [0.4, 0.5, 0.6]}
    entry = create_mock_change_entry(1, "Chunks", "c1", "UPDATE", payload)

    process_change_log_entry(entry, mock_milvus_client, MagicMock())

    mock_milvus_client.upsert.assert_called_once_with(
        data=[{"id": "c1", "embedding": [0.4, 0.5, 0.6], "document_id": "d1"}],
        collection_name=MILVUS_COLLECTION,
    )


def test_process_chunk_delete(mock_db_connections):
    _, mock_milvus_client, _ = mock_db_connections
    payload = {"ChunkID": "c1"}
    entry = create_mock_change_entry(1, "Chunks", "c1", "DELETE", payload)

    process_change_log_entry(entry, mock_milvus_client, MagicMock())

    mock_milvus_client.delete.assert_called_once_with(
        ids=["c1"], collection_name=MILVUS_COLLECTION
    )


def test_process_agentlog_insert_update(mock_db_connections):
    _, _, mock_neo4j_driver = mock_db_connections
    payload = {
        "LogID": 1,
        "AgentID": 101,
        "QueryContent": "test query",
        "ThoughtTree": "{}",
        "BDIState": "{}",
        "Evaluation": "[]",
        "RetrievedChunks": "[]",
    }
    entry = create_mock_change_entry(1, "AgentLogs", "1", "INSERT", payload)

    process_change_log_entry(entry, MagicMock(), mock_neo4j_driver)

    run_calls = (
        mock_neo4j_driver.session.return_value.__enter__.return_value.run.call_args_list
    )
    assert len(run_calls) == 2
    # Agent node merge
    agent_call = run_calls[0]
    assert "MERGE (a:Agent {id: $agent_id})" in agent_call[0][0]
    assert agent_call[1]["agent_id"] == 101
    # AgentLog node merge
    log_call = run_calls[1]
    assert "MERGE (l:AgentLog {id: $log_id, agent_id: $agent_id})" in log_call[0][0]
    assert log_call[1]["log_id"] == 1


def test_process_agentlog_delete(mock_db_connections):
    _, _, mock_neo4j_driver = mock_db_connections
    payload = {"LogID": 1}
    entry = create_mock_change_entry(1, "AgentLogs", "1", "DELETE", payload)

    process_change_log_entry(entry, MagicMock(), mock_neo4j_driver)

    mock_neo4j_driver.session.return_value.__enter__.return_value.run.assert_called_once()
    args, kwargs = (
        mock_neo4j_driver.session.return_value.__enter__.return_value.run.call_args
    )
    assert "MATCH (l:AgentLog {id: $log_id}) DETACH DELETE l" in args[0]
    assert kwargs["log_id"] == 1


def test_process_agent_insert_update(mock_db_connections):
    _, _, mock_neo4j_driver = mock_db_connections
    payload = {
        "AgentID": 101,
        "Name": "TestAgent",
        "Role": "Tester",
        "Status": "active",
    }
    entry = create_mock_change_entry(1, "Agents", "101", "INSERT", payload)

    process_change_log_entry(entry, MagicMock(), mock_neo4j_driver)

    run_calls = (
        mock_neo4j_driver.session.return_value.__enter__.return_value.run.call_args_list
    )
    assert len(run_calls) == 1
    agent_call = run_calls[0]
    assert (
        "MERGE (a:Agent {id: $agent_id, name: $name, role: $role, status: $status})"
        in agent_call[0][0]
    )
    assert agent_call[1]["agent_id"] == 101
    assert agent_call[1]["name"] == "TestAgent"


def test_process_agent_delete(mock_db_connections):
    _, _, mock_neo4j_driver = mock_db_connections
    payload = {"AgentID": 101}
    entry = create_mock_change_entry(1, "Agents", "101", "DELETE", payload)

    process_change_log_entry(entry, MagicMock(), mock_neo4j_driver)

    mock_neo4j_driver.session.return_value.__enter__.return_value.run.assert_called_once()
    args, kwargs = (
        mock_neo4j_driver.session.return_value.__enter__.return_value.run.call_args
    )
    assert "MATCH (a:Agent {id: $agent_id}) DETACH DELETE a" in args[0]
    assert kwargs["agent_id"] == 101


def test_process_document_insert_update(mock_db_connections):
    _, _, mock_neo4j_driver = mock_db_connections
    payload = {
        "DocumentID": "d1",
        "Title": "TestDoc",
        "SourceURL": "http://example.com",
    }
    entry = create_mock_change_entry(1, "Documents", "d1", "INSERT", payload)

    process_change_log_entry(entry, MagicMock(), mock_neo4j_driver)

    run_calls = (
        mock_neo4j_driver.session.return_value.__enter__.return_value.run.call_args_list
    )
    assert len(run_calls) == 1
    doc_call = run_calls[0]
    assert (
        "MERGE (d:Document {id: $document_id, title: $title, source_url: $source_url})"
        in doc_call[0][0]
    )
    assert doc_call[1]["document_id"] == "d1"
    assert doc_call[1]["title"] == "TestDoc"


def test_process_document_delete(mock_db_connections):
    _, _, mock_neo4j_driver = mock_db_connections
    payload = {"DocumentID": "d1"}
    entry = create_mock_change_entry(1, "Documents", "d1", "DELETE", payload)

    process_change_log_entry(entry, MagicMock(), mock_neo4j_driver)

    mock_neo4j_driver.session.return_value.__enter__.return_value.run.assert_called_once()
    args, kwargs = (
        mock_neo4j_driver.session.return_value.__enter__.return_value.run.call_args
    )
    assert "MATCH (d:Document {id: $document_id}) DETACH DELETE d" in args[0]
    assert kwargs["document_id"] == "d1"


# --- Tests for run_cdc_consumer (basic loop test) ---


@pytest.mark.asyncio
async def test_run_cdc_consumer_no_changes(mock_db_connections):
    mock_sql_conn, _, _ = mock_db_connections
    mock_sql_conn.cursor.return_value.fetchall.return_value = []  # No changes
    from unittest.mock import AsyncMock

    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        orig_sleep = asyncio.sleep
        side_effect_state = {"called": False}

        async def side_effect(*args, **kwargs):
            if side_effect_state["called"]:
                raise Exception("Stop loop")
            side_effect_state["called"] = True
            await orig_sleep(0)

        mock_sleep.side_effect = side_effect
        with patch(
            "cdc_consumer.get_sql_server_connection", new_callable=AsyncMock
        ) as mock_get_sql_conn:
            mock_get_sql_conn.return_value = mock_sql_conn
            try:
                await run_cdc_consumer()
            except Exception as e:
                assert str(e) == "Stop loop"
        assert any(
            "SELECT ChangeID" in str(call[0][0])
            for call in mock_sql_conn.cursor.return_value.execute.call_args_list
        )


@pytest.mark.asyncio
async def test_run_cdc_consumer_with_changes(mock_db_connections):
    mock_sql_conn, mock_milvus_client, mock_neo4j_driver = mock_db_connections

    payload = {
        "ChunkID": "c1",
        "DocumentID": "d1",
        "Embedding": [0.1] * 1536,
    }
    mock_sql_conn.cursor.return_value.fetchall.side_effect = [
        [(1, "Chunks", "c1", "INSERT", json.dumps(payload))],
        [],
    ]

    with (
        patch("asyncio.sleep") as mock_sleep,
        patch(
            "cdc_consumer.get_sql_server_connection",
            new_callable=lambda: AsyncMock(return_value=mock_sql_conn),
        ),
        patch("cdc_consumer.get_milvus_client", return_value=mock_milvus_client),
        patch("cdc_consumer.get_neo4j_driver", return_value=mock_neo4j_driver),
    ):
        orig_sleep = asyncio.sleep
        side_effect_state = {"called": False}

        async def side_effect(*args, **kwargs):
            if side_effect_state["called"]:
                raise Exception("Stop loop")
            side_effect_state["called"] = True
            await orig_sleep(0)

        mock_sleep.side_effect = side_effect

        try:
            await run_cdc_consumer()
        except Exception as e:
            assert str(e) == "Stop loop"

        mock_sql_conn.cursor.return_value.execute.assert_any_call(
            "SELECT ChangeID, SourceTable, SourceID, ChangeType, Payload FROM ChangeLog WHERE ChangeID > ? ORDER BY ChangeID ASC",
            0,
        )
        assert mock_sql_conn.cursor.return_value.execute.call_count == 1
        mock_milvus_client.insert.assert_called_once()


@pytest.mark.asyncio
async def test_run_cdc_consumer_reconnection_success():
    sql_conn_1 = None
    sql_conn_2 = MagicMock()
    milvus_1 = None
    milvus_2 = MagicMock()
    neo4j_1 = None
    neo4j_2 = MagicMock()
    neo4j_2.verify_connectivity = MagicMock()

    with (
        patch(
            "cdc_consumer.get_sql_server_connection",
            new_callable=lambda: AsyncMock(side_effect=[sql_conn_1, sql_conn_2]),
        ) as mock_get_sql_conn,
        patch(
            "cdc_consumer.get_milvus_client",
            side_effect=[milvus_1, milvus_2],
        ) as mock_get_milvus_client,
        patch(
            "cdc_consumer.get_neo4j_driver",
            side_effect=[neo4j_1, neo4j_2],
        ) as mock_get_neo4j_driver,
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        patch("cdc_consumer.logger") as mock_logger,
    ):
        await run_cdc_consumer()

        assert mock_get_sql_conn.call_count == 2
        assert mock_get_milvus_client.call_count == 2
        assert mock_get_neo4j_driver.call_count == 2

        mock_logger.info.assert_any_call(
            "Attempting to re-establish database connections..."
        )
        mock_logger.error.assert_any_call(
            "Failed to re-establish all database connections. Retrying in 10 seconds."
        )
        mock_logger.info.assert_any_call(
            "Successfully re-established database connections."
        )

        mock_sleep.assert_called_once_with(10)
