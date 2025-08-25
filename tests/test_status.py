from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_status_dependencies():
    with patch("db_connectors.get_milvus_client") as mock_get_milvus_client:
        with patch("db_connectors.get_neo4j_driver") as mock_get_neo4j_driver:
            mock_milvus_client_instance = MagicMock()
            mock_neo4j_driver_instance = MagicMock()
            mock_get_milvus_client.return_value = mock_milvus_client_instance
            mock_get_neo4j_driver.return_value = mock_neo4j_driver_instance
            yield {
                "mock_get_milvus_client": mock_get_milvus_client,
                "mock_get_neo4j_driver": mock_get_neo4j_driver,
                "mock_milvus_client_instance": mock_milvus_client_instance,
                "mock_neo4j_driver_instance": mock_neo4j_driver_instance,
            }


def test_status_neo4j_disconnected(client, mock_status_dependencies):
    mock_status_dependencies["mock_get_neo4j_driver"].return_value = None
    response = client.get("/status")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "running"
    assert json_data["databases"] == {
        "milvus": "connected",
        "neo4j": "disconnected",
        "sql_server": "connected",
    }


@patch("db_connectors.get_sql_server_connection", return_value=None)
@patch("db_connectors.get_milvus_client", return_value=MagicMock())
@patch("db_connectors.get_neo4j_driver", return_value=MagicMock())
def test_status_sql_server_disconnected(mock_neo4j, mock_milvus, mock_sql, client):
    response = client.get("/status")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "running"
    assert json_data["databases"] == {
        "milvus": "connected",
        "neo4j": "connected",
        "sql_server": "disconnected",
    }


@patch("db_connectors.get_sql_server_connection", return_value=None)
@patch("db_connectors.get_milvus_client", return_value=None)
@patch("db_connectors.get_neo4j_driver", return_value=None)
def test_status_all_disconnected(mock_neo4j, mock_milvus, mock_sql, client):
    response = client.get("/status")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "running"
    assert json_data["databases"] == {
        "milvus": "disconnected",
        "neo4j": "disconnected",
        "sql_server": "disconnected",
    }


@patch(
    "db_connectors.get_sql_server_connection",
    side_effect=RuntimeError("Simulated error"),
)
@patch("db_connectors.get_milvus_client", return_value=MagicMock())
@patch("db_connectors.get_neo4j_driver", return_value=MagicMock())
def test_status_general_exception(mock_neo4j, mock_milvus, mock_sql, client):
    response = client.get("/status")
    assert (
        response.status_code == 200
    )  # Status endpoint should still return 200 even if DBs fail
    json_data = response.json()
    assert json_data["status"] == "running"
    assert json_data["databases"] == {
        "milvus": "connected",
        "neo4j": "connected",
        "sql_server": "disconnected",
    }
