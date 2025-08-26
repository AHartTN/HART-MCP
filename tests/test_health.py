import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# The client fixture is automatically provided by conftest.py


@pytest.mark.asyncio
async def test_health_endpoint_all_healthy(client):
    """
    Tests the /health endpoint when all database connections are healthy.
    """
    with patch("utils.check_database_health", new_callable=AsyncMock) as mock_check_database_health:
        mock_check_database_health.return_value = {
            "milvus": True,
            "neo4j": True,
            "sql_server": True,
        }
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "databases": {
                "milvus": True,
                "neo4j": True,
                "sql_server": True,
            },
        }


@pytest.mark.asyncio
async def test_health_endpoint_milvus_unhealthy(client):
    """
    Tests the /health endpoint when Milvus connection is unhealthy.
    """
    with patch("utils.check_database_health", new_callable=AsyncMock) as mock_check_database_health:
        mock_check_database_health.return_value = {
            "milvus": False,
            "neo4j": True,
            "sql_server": True,
        }
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "degraded",
            "databases": {
                "milvus": False,
                "neo4j": True,
                "sql_server": True,
            },
        }


@pytest.mark.asyncio
async def test_health_endpoint_neo4j_unhealthy(client):
    """
    Tests the /health endpoint when Neo4j connection is unhealthy.
    """
    with patch("utils.check_database_health", new_callable=AsyncMock) as mock_check_database_health:
        mock_check_database_health.return_value = {
            "milvus": True,
            "neo4j": False,
            "sql_server": True,
        }
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "degraded",
            "databases": {
                "milvus": True,
                "neo4j": False,
                "sql_server": True,
            },
        }


@pytest.mark.asyncio
async def test_health_endpoint_sql_server_unhealthy(client):
    """
    Tests the /health endpoint when SQL Server connection is unhealthy.
    """
    with patch("utils.check_database_health", new_callable=AsyncMock) as mock_check_database_health:
        mock_check_database_health.return_value = {
            "milvus": True,
            "neo4j": True,
            "sql_server": False,
        }
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "degraded",
            "databases": {
                "milvus": True,
                "neo4j": True,
                "sql_server": False,
            },
        }


@pytest.mark.asyncio
async def test_health_endpoint_all_disconnected(client):
    """
    Tests the /health endpoint when all database connections are disconnected.
    """
    with patch("utils.check_database_health", new_callable=AsyncMock) as mock_check_database_health:
        mock_check_database_health.return_value = {
            "milvus": False,
            "neo4j": False,
            "sql_server": False,
        }
        response = client.get("/health")
        assert response.status_code == 500 # Should return 500 if all are disconnected
        assert response.json() == {
            "status": "error",
            "databases": {
                "milvus": False,
                "neo4j": False,
                "sql_server": False,
            },
        }
