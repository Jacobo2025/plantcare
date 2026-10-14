"""Pruebas de la entrega de la interfaz web (el comportamiento de la API no cambia)."""
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_index_serves_html(client):
    res = client.get("/")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/html")
    assert "PlantCare" in res.text
    assert "/static/app.js" in res.text and "/static/styles.css" in res.text


@pytest.mark.parametrize("path", ["/static/app.js", "/static/styles.css"])
def test_static_assets_are_served(client, path):
    assert client.get(path).status_code == 200


def test_index_is_not_listed_in_api_schema(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/" not in paths
    for expected in ["/tasks", "/tasks/{task_id}", "/tasks/{task_id}/complete", "/reminders"]:
        assert expected in paths


def test_health_still_works(client):
    assert client.get("/health").json() == {"status": "ok"}
