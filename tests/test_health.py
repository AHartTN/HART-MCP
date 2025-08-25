from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


def test_health_all_connected():
    response = client.get("/health")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "error"
    assert json_data["databases"] == {
        "milvus": False,
        "neo4j": False,
        "sql_server": False,
    }
