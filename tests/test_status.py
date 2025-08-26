import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# The client fixture is automatically provided by conftest.py


@pytest.mark.asyncio
async def test_status_all_connected(client):
    """
    Tests the /status endpoint when all database connections are healthy.
    """
    with patch("db_connectors.get_milvus_client", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("db_connectors.get_neo4j_driver", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("db_connectors.get_sql_server_connection", new_callable=AsyncMock, return_value=MagicMock()):

        response = client.get("/status")
        assert response.status_code == 200
        assert response.json() == {
            "status": "running",
            "databases": {
                "milvus": "connected",
                "neo4j": "connected",
                "sql_server": "connected",
            },
        }


@pytest.mark.asyncio
async def test_status_milvus_disconnected(client):
    """
    Tests the /status endpoint when Milvus connection is disconnected.
    """
    with patch("db_connectors.get_milvus_client", new_callable=AsyncMock, return_value=None), \
         patch("db_connectors.get_neo4j_driver", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("db_connectors.get_sql_server_connection", new_callable=AsyncMock, return_value=MagicMock()):

        response = client.get("/status")
        assert response.status_code == 200
        assert response.json() == {
            "status": "running",
            "databases": {
                "milvus": "disconnected",
                "neo4j": "connected",
                "sql_server": "connected",
            },
        }


@pytest.mark.asyncio
async def test_status_neo4j_disconnected(client):
    """
    Tests the /status endpoint when Neo4j connection is disconnected.
    """
    with patch("db_connectors.get_milvus_client", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("db_connectors.get_neo4j_driver", new_callable=AsyncMock, return_value=None), \
         patch("db_connectors.get_sql_server_connection", new_callable=AsyncMock, return_value=MagicMock()):

        response = client.get("/status")
        assert response.status_code == 200
        assert response.json() == {
            "status": "running",
            "databases": {
                "milvus": "connected",
                "neo4j": "disconnected",
                "sql_server": "connected",
            },
        }


@pytest.mark.asyncio
async def test_status_sql_server_disconnected(client):
    """
    Tests the /status endpoint when SQL Server connection is disconnected.
    """
    with patch("db_connectors.get_milvus_client", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("db_connectors.get_neo4j_driver", new_callable=AsyncMock, return_value=MagicMock()), \
         patch("db_connectors.get_sql_server_connection", new_callable=AsyncMock, return_value=None):

        response = client.get("/status")
        assert response.status_code == 200
        assert response.json() == {
            "status": "running",
            "databases": {
                "milvus": "connected",
                "neo4j": "connected",
                "sql_server": "disconnected",
            },
        }


@pytest.mark.asyncio
async def test_status_all_disconnected(client):
    """
    Tests the /status endpoint when all database connections are disconnected.
    """
    with patch("db_connectors.get_milvus_client", new_callable=AsyncMock, return_value=None), \
         patch("db_connectors.get_neo4j_driver", new_callable=AsyncMock, return_value=None), \
         patch("db_connectors.get_sql_server_connection", new_callable=AsyncMock, return_value=None):

        response = client.get("/status")
        assert response.status_code == 200
        assert response.json() == {
            "status": "running",
            "databases": {
                "milvus": "disconnected",
                "neo4j": "disconnected",
                "sql_server": "disconnected",
            },
        }