from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


def test_feedback_endpoint():
    payload = {
        "log_id": 1,
        "feedback_text": "Great result!",
        "rating": 5,
        "feedback_type": "accuracy",
    }
    response = client.post("/feedback", json=payload)
    assert response.status_code in (200, 404, 500)
    json_data = response.json()
    if response.status_code == 200:
        assert "message" in json_data
    else:
        assert "error" in json_data
