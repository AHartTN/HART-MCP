# In tests/test_db_connectors.py
from unittest.mock import MagicMock

import pytest

from db_connectors import (
    get_milvus_client,
    get_neo4j_driver,
    get_sql_server_connection,
)


@pytest.mark.asyncio
async def test_get_sql_server_connection(mock_sql_connection: MagicMock):
    """
    Tests the get_sql_server_connection function.
    """
    # Arrange (no arrangement needed, fixture is already a mock)

    # Act
    async with get_sql_server_connection() as conn:
        # Assert
        assert conn is not None


@pytest.mark.asyncio
async def test_get_milvus_client(mock_milvus_client: MagicMock):
    """
    Tests the get_milvus_client function.
    """
    # Arrange (no arrangement needed, fixture is already a mock)

    # Act
    client = await get_milvus_client()

    # Assert
    assert client is not None


@pytest.mark.asyncio
async def test_get_neo4j_driver(mock_neo4j_driver: MagicMock):
    """
    Tests the get_neo4j_driver function.
    """
    # Arrange (no arrangement needed, fixture is already a mock)

    # Act
    driver = await get_neo4j_driver()

    # Assert
    assert driver is not None