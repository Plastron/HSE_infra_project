import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from app import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_version():
    response = client.get("/version")
    assert response.status_code == 200
    assert response.json() == {"version": "1.0.0"}


def test_get_topics():
    response = client.get("/api/topics")
    assert response.status_code == 200
    assert isinstance(response.json()["topics"], list)


def test_topic_not_found():
    response = client.get("/api/topics/nonexistent_topic_123")
    assert response.status_code == 404


@patch("app.generate_question_from_ai")
def test_generate_task_mock(mock_generate):
    # Мокаем ответ от GigaChat
    mock_generate.return_value = {
        "task": "Сколько будет 2+2?",
        "options": ["3", "4", "5", "6"],
        "correct_index": 1
    }

    response = client.post("/api/generate", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["task"] == "Сколько будет 2+2?"
    assert data["correct_index"] == 1
    assert len(data["options"]) == 4