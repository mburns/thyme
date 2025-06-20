import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(
    __name__,
    template_folder=os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates")
    ),
)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///timeline.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


# Association tables for many-to-many relationships
person_awards = db.Table(
    "person_awards",
    db.Column("person_id", db.Integer, db.ForeignKey("person.id"), primary_key=True),
    db.Column("award_id", db.Integer, db.ForeignKey("award.id"), primary_key=True),
    db.Column("award_date", db.DateTime),  # When the award was received
)

person_wars = db.Table(
    "person_wars",
    db.Column("person_id", db.Integer, db.ForeignKey("person.id"), primary_key=True),
    db.Column("war_id", db.Integer, db.ForeignKey("war.id"), primary_key=True),
    db.Column("role", db.String(100)),  # e.g., "commander", "soldier", "civilian"
)


class Person(db.Model):
    """People who appear in the timeline"""

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(200), nullable=False)
    wikidata_id: Optional[str] = db.Column(db.String(50), unique=True)
    birth_date: Optional[datetime] = db.Column(db.DateTime)
    death_date: Optional[datetime] = db.Column(db.DateTime)
    occupation: Optional[str] = db.Column(db.String(200))
    nationality: Optional[str] = db.Column(db.String(100))
    image_url: Optional[str] = db.Column(db.String(500))
    description: Optional[str] = db.Column(db.Text)

    # Relationships
    awards = db.relationship(
        "Award", secondary=person_awards, back_populates="recipients"
    )
    wars = db.relationship("War", secondary=person_wars, back_populates="participants")
    inventions = db.relationship("Invention", back_populates="inventor")

    def to_timeline_format(self) -> Dict[str, Any]:
        """Convert person's life events to TimelineJS3 format"""
        events = []

        # Birth event
        if self.birth_date:
            events.append(
                {
                    "start_date": {
                        "year": self.birth_date.year,
                        "month": self.birth_date.month,
                        "day": self.birth_date.day,
                    },
                    "text": {
                        "headline": f"Birth of {self.name}",
                        "text": f"Birth of {self.name}"
                        + (f", {self.occupation}" if self.occupation else ""),
                    },
                    "media": (
                        {
                            "url": self.image_url or "",
                            "caption": self.name,
                            "credit": "Wikimedia Commons",
                        }
                        if self.image_url
                        else None
                    ),
                    "group": "People",
                    "background": {"color": "#2e8b57"},
                    "text": {"color": "#ffffff"},
                }
            )

        # Death event
        if self.death_date:
            events.append(
                {
                    "start_date": {
                        "year": self.death_date.year,
                        "month": self.death_date.month,
                        "day": self.death_date.day,
                    },
                    "text": {
                        "headline": f"Death of {self.name}",
                        "text": f"Death of {self.name}"
                        + (f", {self.occupation}" if self.occupation else ""),
                    },
                    "media": (
                        {
                            "url": self.image_url or "",
                            "caption": self.name,
                            "credit": "Wikimedia Commons",
                        }
                        if self.image_url
                        else None
                    ),
                    "group": "People",
                    "background": {"color": "#8b0000"},
                    "text": {"color": "#ffffff"},
                }
            )

        return events


class Award(db.Model):
    """Awards and honors"""

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(200), nullable=False)
    wikidata_id: Optional[str] = db.Column(db.String(50), unique=True)
    category: Optional[str] = db.Column(db.String(100))  # e.g., "Nobel Prize", "Oscar"
    description: Optional[str] = db.Column(db.Text)
    image_url: Optional[str] = db.Column(db.String(500))

    # Relationships
    recipients = db.relationship(
        "Person", secondary=person_awards, back_populates="awards"
    )

    def to_timeline_format(self) -> Dict[str, Any]:
        """Convert award events to TimelineJS3 format"""
        events = []

        for person in self.recipients:
            # Get award date from association table
            award_date = (
                db.session.query(person_awards.c.award_date)
                .filter_by(person_id=person.id, award_id=self.id)
                .scalar()
            )

            if award_date:
                events.append(
                    {
                        "start_date": {
                            "year": award_date.year,
                            "month": award_date.month,
                            "day": award_date.day,
                        },
                        "text": {
                            "headline": f"{person.name} received {self.name}",
                            "text": f"{person.name} received {self.name}"
                            + (f" for {self.description}" if self.description else ""),
                        },
                        "media": (
                            {
                                "url": person.image_url or self.image_url or "",
                                "caption": person.name,
                                "credit": "Wikimedia Commons",
                            }
                            if (person.image_url or self.image_url)
                            else None
                        ),
                        "group": "Awards",
                        "background": {"color": "#FFD700"},
                        "text": {"color": "#000000"},
                    }
                )

        return events


class War(db.Model):
    """Wars and conflicts"""

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(200), nullable=False)
    wikidata_id: Optional[str] = db.Column(db.String(50), unique=True)
    start_date: Optional[datetime] = db.Column(db.DateTime)
    end_date: Optional[datetime] = db.Column(db.DateTime)
    description: Optional[str] = db.Column(db.Text)
    image_url: Optional[str] = db.Column(db.String(500))

    # Relationships
    participants = db.relationship(
        "Person", secondary=person_wars, back_populates="wars"
    )

    def to_timeline_format(self) -> Dict[str, Any]:
        """Convert war events to TimelineJS3 format"""
        events = []

        if self.start_date:
            events.append(
                {
                    "start_date": {
                        "year": self.start_date.year,
                        "month": self.start_date.month,
                        "day": self.start_date.day,
                    },
                    "end_date": (
                        {
                            "year": self.end_date.year,
                            "month": self.end_date.month,
                            "day": self.end_date.day,
                        }
                        if self.end_date
                        else None
                    ),
                    "text": {
                        "headline": f"Start of {self.name}",
                        "text": f"Start of {self.name}"
                        + (f", {self.description}" if self.description else ""),
                    },
                    "media": (
                        {
                            "url": self.image_url or "",
                            "caption": self.name,
                            "credit": "Wikimedia Commons",
                        }
                        if self.image_url
                        else None
                    ),
                    "group": "Wars",
                    "background": {"color": "#dc143c"},
                    "text": {"color": "#ffffff"},
                }
            )

        return events


class Invention(db.Model):
    """Technological inventions and discoveries"""

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(200), nullable=False)
    wikidata_id: Optional[str] = db.Column(db.String(50), unique=True)
    invention_date: Optional[datetime] = db.Column(db.DateTime)
    description: Optional[str] = db.Column(db.Text)
    image_url: Optional[str] = db.Column(db.String(500))
    inventor_id: Optional[int] = db.Column(db.Integer, db.ForeignKey("person.id"))

    # Relationships
    inventor = db.relationship("Person", back_populates="inventions")

    def to_timeline_format(self) -> Dict[str, Any]:
        """Convert invention events to TimelineJS3 format"""
        events = []

        if self.invention_date:
            events.append(
                {
                    "start_date": {
                        "year": self.invention_date.year,
                        "month": self.invention_date.month,
                        "day": self.invention_date.day,
                    },
                    "text": {
                        "headline": f"Invention of {self.name}",
                        "text": f"Invention of {self.name}"
                        + (f" by {self.inventor.name}" if self.inventor else "")
                        + (f", {self.description}" if self.description else ""),
                    },
                    "media": (
                        {
                            "url": self.image_url or "",
                            "caption": self.name,
                            "credit": "Wikimedia Commons",
                        }
                        if self.image_url
                        else None
                    ),
                    "group": "Technology",
                    "background": {"color": "#4169e1"},
                    "text": {"color": "#ffffff"},
                }
            )

        return events


class SpaceEvent(db.Model):
    """Space exploration events"""

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(200), nullable=False)
    wikidata_id: Optional[str] = db.Column(db.String(50), unique=True)
    event_date: Optional[datetime] = db.Column(db.DateTime)
    description: Optional[str] = db.Column(db.Text)
    image_url: Optional[str] = db.Column(db.String(500))

    def to_timeline_format(self) -> Dict[str, Any]:
        """Convert space events to TimelineJS3 format"""
        events = []

        if self.event_date:
            events.append(
                {
                    "start_date": {
                        "year": self.event_date.year,
                        "month": self.event_date.month,
                        "day": self.event_date.day,
                    },
                    "text": {
                        "headline": self.name,
                        "text": f"{self.name}"
                        + (f", {self.description}" if self.description else ""),
                    },
                    "media": (
                        {
                            "url": self.image_url or "",
                            "caption": self.name,
                            "credit": "Wikimedia Commons",
                        }
                        if self.image_url
                        else None
                    ),
                    "group": "Space",
                    "background": {"color": "#2c3e50"},
                    "text": {"color": "#ffffff"},
                }
            )

        return events


# Legacy Event model for backward compatibility (can be removed later)
class Event(db.Model):
    """Legacy event model - kept for backward compatibility"""

    id: int = db.Column(db.Integer, primary_key=True)
    title: str = db.Column(db.String(200), nullable=False)
    description: Optional[str] = db.Column(db.Text)
    start_date: datetime = db.Column(db.DateTime, nullable=False)
    end_date: Optional[datetime] = db.Column(db.DateTime)
    media_url: Optional[str] = db.Column(db.String(500))
    media_caption: Optional[str] = db.Column(db.String(200))
    media_credit: Optional[str] = db.Column(db.String(200))
    group: Optional[str] = db.Column(db.String(100))
    background_color: Optional[str] = db.Column(db.String(7))
    text_color: Optional[str] = db.Column(db.String(7))

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
    all_events = []

    # Get events from all entity types
    people = Person.query.all()
    for person in people:
        all_events.extend(person.to_timeline_format())

    awards = Award.query.all()
    for award in awards:
        all_events.extend(award.to_timeline_format())

    wars = War.query.all()
    for war in wars:
        all_events.extend(war.to_timeline_format())

    inventions = Invention.query.all()
    for invention in inventions:
        all_events.extend(invention.to_timeline_format())

    space_events = SpaceEvent.query.all()
    for space_event in space_events:
        all_events.extend(space_event.to_timeline_format())

    # Legacy events
    legacy_events = Event.query.all()
    for event in legacy_events:
        all_events.append(event.to_timeline_format())

    # Sort all events by start date
    all_events.sort(
        key=lambda x: (
            x["start_date"]["year"],
            x["start_date"]["month"],
            x["start_date"]["day"],
        )
    )

    timeline_data: Dict[str, Any] = {
        "title": {
            "text": {
                "headline": "My Timeline",
                "text": "A timeline of important events",
            }
        },
        "events": all_events,
    }

    return jsonify(timeline_data)


@app.route("/api/events", methods=["GET"])
def get_events() -> str:
    """Return events for the admin interface"""
    # For now, return legacy events - this can be updated to show all entity types
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
