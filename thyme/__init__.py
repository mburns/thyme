from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///timeline.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Event(db.Model):
    id: int = db.Column(db.Integer, primary_key=True)
    title: str = db.Column(db.String(200), nullable=False)
    description: Optional[str] = db.Column(db.Text)
    start_date: datetime = db.Column(db.DateTime, nullable=False)
    end_date: Optional[datetime] = db.Column(db.DateTime)
    media_url: Optional[str] = db.Column(db.String(500))
    media_caption: Optional[str] = db.Column(db.String(200))
    media_credit: Optional[str] = db.Column(db.String(200))
    group: Optional[str] = db.Column(db.String(100))
    background_color: Optional[str] = db.Column(db.String(7))  # Hex color code
    text_color: Optional[str] = db.Column(db.String(7))  # Hex color code

    def to_timeline_format(self) -> Dict[str, Any]:
        """Convert event to TimelineJS3 format"""
        event_data: Dict[str, Any] = {
            "start_date": {
                "year": self.start_date.year,
                "month": self.start_date.month,
                "day": self.start_date.day,
            },
            "text": {"headline": self.title, "text": self.description or ""},
        }

        if self.end_date:
            event_data["end_date"] = {
                "year": self.end_date.year,
                "month": self.end_date.month,
                "day": self.end_date.day,
            }

        if self.media_url:
            event_data["media"] = {
                "url": self.media_url,
                "caption": self.media_caption or "",
                "credit": self.media_credit or "",
            }

        if self.group:
            event_data["group"] = self.group

        if self.background_color:
            event_data["background"] = {"color": self.background_color}

        if self.text_color:
            event_data["text"]["color"] = self.text_color

        return event_data


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/timeline")
def get_timeline_data() -> Any:
    """Return timeline data in TimelineJS3 format"""
    events: List[Event] = Event.query.order_by(Event.start_date).all()

    timeline_data: Dict[str, Any] = {
        "title": {
            "text": {
                "headline": "My Timeline",
                "text": "A timeline of important events",
            }
        },
        "events": [event.to_timeline_format() for event in events],
    }

    return jsonify(timeline_data)


@app.route("/api/events", methods=["GET"])
def get_events() -> str:
    """Return events for the admin interface"""
    events: List[Event] = Event.query.order_by(Event.start_date.desc()).all()
    return render_template("events_list.html", events=events)


@app.route("/api/events", methods=["POST"])
def add_event() -> str:
    """Add a new event via htmx"""
    data = request.form

    try:
        start_date = datetime.strptime(data["start_date"], "%Y-%m-%d")
        end_date = None
        if data.get("end_date"):
            end_date = datetime.strptime(data["end_date"], "%Y-%m-%d")

        event = Event(
            title=data["title"],
            description=data.get("description", ""),
            start_date=start_date,
            end_date=end_date,
            media_url=data.get("media_url", ""),
            media_caption=data.get("media_caption", ""),
            media_credit=data.get("media_credit", ""),
            group=data.get("group", ""),
            background_color=data.get("background_color", ""),
            text_color=data.get("text_color", ""),
        )

        db.session.add(event)
        db.session.commit()

        # Return the updated events list
        events = Event.query.order_by(Event.start_date.desc()).all()
        return render_template("events_list.html", events=events)

    except Exception as e:
        return f"Error: {str(e)}", 400


@app.route("/api/events/<int:event_id>", methods=["DELETE"])
def delete_event(event_id):
    """Delete an event"""
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()

    events = Event.query.order_by(Event.start_date.desc()).all()
    return render_template("events_list.html", events=events)


@app.route("/admin")
def admin():
    """Admin interface for managing events"""
    return render_template("admin.html")


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
