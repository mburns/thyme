from datetime import datetime

import pytest

from thyme import Event, app, db


@pytest.fixture(scope="module")
def test_app():
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def test_to_timeline_format_minimal(test_app):
    event = Event(
        title="Test Event",
        description="Test Description",
        start_date=datetime(2020, 1, 1),
    )
    result = event.to_timeline_format()
    assert result["start_date"] == {"year": 2020, "month": 1, "day": 1}
    assert result["text"]["headline"] == "Test Event"
    assert result["text"]["text"] == "Test Description"
    assert "end_date" not in result
    assert "media" not in result
    assert "group" not in result
    assert "background" not in result
    assert "color" not in result["text"]


def test_to_timeline_format_full(test_app):
    event = Event(
        title="Full Event",
        description="Full Desc",
        start_date=datetime(2021, 2, 3),
        end_date=datetime(2021, 2, 4),
        media_url="http://img.com/img.jpg",
        media_caption="A caption",
        media_credit="A credit",
        group="Group1",
        background_color="#ffffff",
        text_color="#000000",
    )
    result = event.to_timeline_format()
    assert result["end_date"] == {"year": 2021, "month": 2, "day": 4}
    assert result["media"] == {
        "url": "http://img.com/img.jpg",
        "caption": "A caption",
        "credit": "A credit",
    }
    assert result["group"] == "Group1"
    assert result["background"] == {"color": "#ffffff"}
    assert result["text"]["color"] == "#000000"
