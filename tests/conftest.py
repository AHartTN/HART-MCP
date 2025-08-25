import pytest
from fastapi.testclient import TestClient

from server import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


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
