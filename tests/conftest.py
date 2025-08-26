import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from server import app
from llm_connector import LLMClient
from db_connectors import get_sql_server_connection
from project_state import ProjectState


@pytest.fixture
def mock_llm_client():
    mock = MagicMock(spec=LLMClient)
    yield mock

@pytest.fixture
def mock_db_connection():
    mock = MagicMock()
    yield mock

@pytest.fixture
def mock_project_state():
    mock = MagicMock(spec=ProjectState)
    yield mock

@pytest.fixture
def client(mock_llm_client, mock_db_connection, mock_project_state):
    app.dependency_overrides[LLMClient] = lambda: mock_llm_client
    app.dependency_overrides[get_sql_server_connection] = lambda: mock_db_connection
    app.dependency_overrides[ProjectState] = lambda: mock_project_state

    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear() # Clear overrides after test

# Existing fixtures
@pytest.fixture
def set_sql_server_env():
    # Stub fixture for SQL Server environment
    yield


@pytest.fixture
def set_milvus_env():
    # Stub fixture for Milvus environment
    yield


@pytest.fixture
def set_neo4j_env():
    # Stub fixture for Neo4j environment
    yield