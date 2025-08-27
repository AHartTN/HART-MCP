# In tests/conftest.py
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from db_connectors import get_milvus_client, get_neo4j_driver, get_sql_server_connection
from llm_connector import LLMClient
from server import app

# -- Mock LLM Client --


class MockLLMClient:
    """A concrete mock for the LLMClient that gives us full control in tests."""

    def __init__(self):
        """Initializes the mock, allowing response or error configuration."""
        self.response = ""
        self.error = None

    async def invoke(self, prompt: str) -> str:
        """Mocks the invoke method to return a set response or raise an error."""
        if self.error:
            raise self.error
        return self.response


@pytest.fixture
def mock_llm_client() -> MockLLMClient:
    """Provides a controllable mock of the LLMClient."""
    return MockLLMClient()


# -- Mock Database Clients --


@pytest.fixture
def mock_sql_connection():
    """Mocks the SQL Server connection and cursor."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []
    # Simply mock execute and set lastrowid directly
    mock_cursor.execute = MagicMock(return_value=None)
    mock_cursor.lastrowid = 1  # Set a default lastrowid for tests

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    # Mock async context manager methods
    mock_conn.__aenter__.return_value = mock_conn
    mock_conn.__aexit__ = AsyncMock(return_value=None)
    return mock_conn


@pytest.fixture
def mock_milvus_client():
    """Provides a mock of the MilvusClient."""
    mock_client = MagicMock()
    mock_client.search = AsyncMock(return_value=[])
    return mock_client


@pytest.fixture
def mock_neo4j_driver():
    """Provides a mock of the Neo4j Driver."""
    mock_session = MagicMock()
    mock_session.run = MagicMock()
    mock_session.close = MagicMock()

    mock_driver = MagicMock()
    mock_driver.session.return_value = mock_session
    # Mock async context manager methods
    mock_driver.close = AsyncMock(return_value=None)
    return mock_driver


# -- Main Test Client Fixture --


@pytest.fixture
def client(
    mock_llm_client: MockLLMClient,
    mock_sql_connection: MagicMock,
    mock_milvus_client: MagicMock,
    mock_neo4j_driver: MagicMock,
) -> TestClient:
    """
    Provides a FastAPI TestClient with all external dependencies (LLM, DBs)
    overridden by our mock instances.
    """
    # Override dependencies
    app.dependency_overrides[LLMClient] = lambda: mock_llm_client
    app.dependency_overrides[get_sql_server_connection] = lambda: mock_sql_connection
    app.dependency_overrides[get_milvus_client] = lambda: mock_milvus_client
    app.dependency_overrides[get_neo4j_driver] = lambda: mock_neo4j_driver

    with TestClient(app) as test_client:
        yield test_client

    # Clean up overrides after test
    app.dependency_overrides = {}
