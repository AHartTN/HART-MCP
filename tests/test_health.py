# In tests/test_health.py
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_health_endpoint_all_healthy(
    client: TestClient,
    mock_sql_connection: MagicMock,
    mock_milvus_client: MagicMock,
    mock_neo4j_driver: MagicMock,
):
    """
    Tests the /health endpoint when all database connections are healthy.
    """
    # Arrange (no changes needed, fixtures are healthy by default)

    # Act
    response = client.get("/health")

    # Assert
    response.raise_for_status()
    assert response.json() == {
        "status": "ok",
        "databases": {
            "milvus": True,
            "neo4j": True,
            "sql_server": True,
        },
    }


def test_health_endpoint_milvus_unhealthy(
    client: TestClient,
    mock_sql_connection: MagicMock,
    mock_milvus_client: MagicMock,
    mock_neo4j_driver: MagicMock,
):
    """
    Tests the /health endpoint when Milvus connection is unhealthy.
    """
    # Arrange
    mock_milvus_client.search.side_effect = Exception("Milvus is down")

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "databases": {
            "milvus": False,
            "neo4j": True,
            "sql_server": True,
        },
    }


def test_health_endpoint_neo4j_unhealthy(
    client: TestClient,
    mock_sql_connection: MagicMock,
    mock_milvus_client: MagicMock,
    mock_neo4j_driver: MagicMock,
):
    """
    Tests the /health endpoint when Neo4j connection is unhealthy.
    """
    # Arrange
    mock_neo4j_driver.session.return_value.run.side_effect = Exception("Neo4j is down")

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "databases": {
            "milvus": True,
            "neo4j": False,
            "sql_server": True,
        },
    }


def test_health_endpoint_sql_server_unhealthy(
    client: TestClient,
    mock_sql_connection: MagicMock,
    mock_milvus_client: MagicMock,
    mock_neo4j_driver: MagicMock,
):
    """
    Tests the /health endpoint when SQL Server connection is unhealthy.
    """
    # Arrange
    mock_sql_connection.cursor.return_value.execute.side_effect = Exception(
        "SQL Server is down"
    )

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "status": "degraded",
        "databases": {
            "milvus": True,
            "neo4j": True,
            "sql_server": False,
        },
    }


def test_health_endpoint_all_disconnected(
    client: TestClient,
    mock_sql_connection: MagicMock,
    mock_milvus_client: MagicMock,
    mock_neo4j_driver: MagicMock,
):
    """
    Tests the /health endpoint when all database connections are disconnected.
    """
    # Arrange
    mock_milvus_client.search.side_effect = Exception("Milvus is down")
    mock_neo4j_driver.session.return_value.run.side_effect = Exception("Neo4j is down")
    mock_sql_connection.cursor.return_value.execute.side_effect = Exception(
        "SQL Server is down"
    )

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 500
    assert response.json() == {
        "status": "error",
        "databases": {
            "milvus": False,
            "neo4j": False,
            "sql_server": False,
        },
    }