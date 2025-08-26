from unittest.mock import AsyncMock, patch


def test_health_endpoint(client):
    with patch(
        "utils.check_database_health", new_callable=AsyncMock
    ) as mock_check_database_health:
        with patch(
            "utils.get_milvus_client", new_callable=AsyncMock
        ) as mock_get_milvus_client:
            with patch(
                "utils.get_neo4j_driver", new_callable=AsyncMock
            ) as mock_get_neo4j_driver:
                with patch(
                    "utils.get_sql_server_connection", new_callable=AsyncMock
                ) as mock_get_sql_server_connection:
                    # Configure the mock for check_database_health to return an awaitable dictionary
                    mock_check_database_health.return_value = {
                        "milvus": True,
                        "neo4j": True,
                        "sql_server": True,
                    }

                    # Configure the mocks for the individual database connectors
                    mock_get_milvus_client.return_value = AsyncMock()
                    mock_get_neo4j_driver.return_value = AsyncMock()
                    mock_get_sql_server_connection.return_value = AsyncMock()

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
