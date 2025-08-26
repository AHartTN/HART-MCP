import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from db_connectors import get_sql_server_connection, get_milvus_client, get_neo4j_driver


@pytest.mark.asyncio
async def test_get_sql_server_connection_mocked():
    """
    Tests get_sql_server_connection by mocking the underlying pyodbc.connect.
    """
    with patch("pyodbc.connect", return_value=MagicMock()) as mock_connect:
        conn = await get_sql_server_connection()
        assert conn is not None
        mock_connect.assert_called_once()


@pytest.mark.asyncio
async def test_get_milvus_client_mocked():
    """
    Tests get_milvus_client by mocking the underlying MilvusClient.
    """
    # Patch asyncio.to_thread to return a mocked MilvusClient instance
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
        mock_milvus_client_instance = MagicMock()
        mock_to_thread.return_value = mock_milvus_client_instance

        client = await get_milvus_client()
        assert client is not None
        assert client == mock_milvus_client_instance # Ensure the returned client is our mock
        mock_to_thread.assert_called_once() # Verify asyncio.to_thread was called


@pytest.mark.asyncio
async def test_get_neo4j_driver_mocked():
    """
    Tests get_neo4j_driver by mocking the underlying neo4j.GraphDatabase.driver.
    """
    # Patch asyncio.to_thread to return a mocked Neo4j driver instance
    with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
        mock_neo4j_driver_instance = MagicMock()
        mock_to_thread.return_value = mock_neo4j_driver_instance

        driver = await get_neo4j_driver()
        assert driver is not None
        assert driver == mock_neo4j_driver_instance # Ensure the returned driver is our mock
        mock_to_thread.assert_called_once() # Verify asyncio.to_thread was called
