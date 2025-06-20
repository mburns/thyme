from datetime import datetime

import pytest

from thyme import Event, app, db


@pytest.fixture(scope="function")
def client():
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


def create_event():
    event = Event(
        title="API Event",
        description="API Desc",
        start_date=datetime(2022, 5, 6),
    )
    db.session.add(event)
    db.session.commit()
    return event


def test_get_timeline(client):
    with app.app_context():
        db.session.query(Event).delete()
        db.session.commit()
        create_event()
    resp = client.get("/api/timeline")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "events" in data
    assert data["events"][0]["text"]["headline"] == "API Event"


def test_get_events(client):
    with app.app_context():
        create_event()
    resp = client.get("/api/events")
    assert resp.status_code == 200
    assert b"API Event" in resp.data


def test_add_event(client):
    resp = client.post(
        "/api/events",
        data={
            "title": "New Event",
            "description": "New Desc",
            "start_date": "2023-01-01",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"New Event" in resp.data


def test_delete_event(client):
    with app.app_context():
        event = create_event()
        event_id = event.id
    resp = client.delete(f"/api/events/{event_id}")
    assert resp.status_code == 200
    assert b"API Event" not in resp.data
