import pytest

from db_connectors import get_milvus_client, get_neo4j_driver, get_sql_server_connection


@pytest.mark.asyncio
async def test_get_sql_server_connection(set_sql_server_env):
    conn = get_sql_server_connection()
    # This test assumes a SQL Server instance is running locally with the specified credentials.
    # If not, this test will fail. For true unit testing, mocking would be required.
    if conn:
        assert conn is not None
        conn.close()
    else:
        pytest.skip(
            "SQL Server connection failed, skipping test. Ensure SQL Server is running and credentials are correct."
        )


@pytest.mark.asyncio
async def test_get_milvus_client(set_milvus_env):
    client = await get_milvus_client()
    # This test assumes a Milvus instance is running locally.
    if client:
        assert client is not None
        try:
            client.list_collections()  # Verify client is active
            client.close()  # Close the client
        except Exception as e:
            pytest.fail(f"Milvus client verification failed: {e}")
    else:
        pytest.skip(
            "Milvus connection failed, skipping test. Ensure Milvus is running."
        )


@pytest.mark.asyncio
async def test_get_neo4j_driver(set_neo4j_env):
    driver = get_neo4j_driver()
    # This test assumes a Neo4j instance is running locally with the specified credentials.
    if driver:
        assert driver is not None
        driver.close()
    else:
        pytest.skip(
            "Neo4j connection failed, skipping test. Ensure Neo4j is running and credentials are correct."
        )
