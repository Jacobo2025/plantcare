"""Pruebas de los endpoints HTTP con TestClient."""
from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import get_service
from app.service import CareCalendarService

TODAY = date.today()


@pytest.fixture
def client():
    service = CareCalendarService(today_provider=lambda: TODAY)
    app.dependency_overrides[get_service] = lambda: service
    yield TestClient(app)
    app.dependency_overrides.clear()


def payload(days_offset=0, **overrides):
    body = {
        "plant_name": "Monstera",
        "care_type": "riego",
        "scheduled_date": (TODAY + timedelta(days=days_offset)).isoformat(),
        "description": "Regar con poca agua",
    }
    body.update(overrides)
    return body


def test_create_task_returns_201_and_pending(client):
    res = client.post("/tasks", json=payload(3))
    assert res.status_code == 201
    assert res.json()["status"] == "pendiente"


def test_past_task_is_listed_as_overdue(client):
    client.post("/tasks", json=payload(-2))
    tasks = client.get("/tasks").json()
    assert tasks[0]["status"] == "vencida"


def test_completed_task_keeps_status(client):
    task_id = client.post("/tasks", json=payload(-2)).json()["id"]
    res = client.post(f"/tasks/{task_id}/complete")
    assert res.status_code == 200 and res.json()["status"] == "completada"
    assert client.get("/tasks").json()[0]["status"] == "completada"
    assert client.get(f"/tasks/{task_id}").json()["status"] == "completada"


@pytest.mark.parametrize(
    "bad",
    [
        payload(plant_name=""),
        payload(care_type="fumigacion"),
        payload(scheduled_date="no-es-fecha"),
        {"care_type": "riego"},
    ],
)
def test_invalid_data_returns_422(client, bad):
    assert client.post("/tasks", json=bad).status_code == 422


def test_unknown_task_returns_404(client):
    assert client.get(f"/tasks/{uuid4()}").status_code == 404
    assert client.post(f"/tasks/{uuid4()}/complete").status_code == 404


def test_invalid_task_id_returns_422(client):
    assert client.get("/tasks/abc").status_code == 422


def test_reminders_endpoint(client):
    client.post("/tasks", json=payload(-1))
    client.post("/tasks", json=payload(2))
    client.post("/tasks", json=payload(30))
    res = client.get("/reminders", params={"days_ahead": 7})
    assert [r["days_until_due"] for r in res.json()] == [-1, 2]


def test_reminders_rejects_negative_days(client):
    assert client.get("/reminders", params={"days_ahead": -1}).status_code == 422


def test_filter_by_status(client):
    client.post("/tasks", json=payload(-1))
    client.post("/tasks", json=payload(5))
    res = client.get("/tasks", params={"status": "vencida"})
    assert len(res.json()) == 1
