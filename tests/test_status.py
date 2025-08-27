# In tests/test_status.py
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_status_all_connected(client: TestClient):
    """
    Tests the /status endpoint when all mocked database connections are healthy.
    By default, our mock fixtures in conftest.py are 'healthy'.
    """
    # Arrange (no special arrangement needed, mocks are healthy by default)

    # Act
    response = client.get("/status")

    # Assert
    response.raise_for_status()
    assert response.json() == {
        "status": "running",
        "databases": {
            "milvus": "connected",
            "neo4j": "connected",
            "sql_server": "connected",
        },
    }


def test_status_one_disconnected(client: TestClient, mock_neo4j_driver: MagicMock):
    """
    Tests the /status endpoint when one database (Neo4j) is disconnected.
    """
    # Arrange: Simulate a failure in one of the mock database clients.
    # We can make the mock raise an error when a method is called.
    mock_neo4j_driver.session.return_value.run.side_effect = Exception(
        "Connection failed"
    )

    # Act
    response = client.get("/status")

    # Assert
    response.raise_for_status()  # The endpoint itself should still be operational
    assert response.json() == {
        "status": "running",
        "databases": {
            "milvus": "connected",
            "neo4j": "disconnected",  # This should now reflect the failure
            "sql_server": "connected",
        },
    }