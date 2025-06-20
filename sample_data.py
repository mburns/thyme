#!/usr/bin/env python3
"""
Sample data script for the Timeline App.
Run this script to populate the database with example events.
"""

from datetime import datetime
from typing import Any, Dict, List

from thyme import Event, app, db


def create_sample_events() -> List[Dict[str, Any]]:
    """Create sample events for the timeline"""

    events: List[Dict[str, Any]] = [
        {
            "title": "The First Computer",
            "description": "Charles Babbage designs the Analytical Engine, considered the first mechanical computer.",
            "start_date": datetime(1837, 1, 1),
            "media_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Charles_Babbage_-_1860.jpg/220px-Charles_Babbage_-_1860.jpg",
            "media_caption": "Charles Babbage, inventor of the Analytical Engine",
            "media_credit": "Wikimedia Commons",
            "group": "Technology",
            "background_color": "#4a90e2",
            "text_color": "#ffffff",
        },
        {
            "title": "World Wide Web",
            "description": "Tim Berners-Lee invents the World Wide Web at CERN.",
            "start_date": datetime(1989, 3, 12),
            "media_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/First_Web_Server.jpg/220px-First_Web_Server.jpg",
            "media_caption": "The first web server at CERN",
            "media_credit": "Wikimedia Commons",
            "group": "Technology",
            "background_color": "#50c878",
            "text_color": "#ffffff",
        },
        {
            "title": "First iPhone",
            "description": "Apple releases the first iPhone, revolutionizing mobile computing.",
            "start_date": datetime(2007, 6, 29),
            "media_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/32/IPhone_1st_Gen.svg/220px-IPhone_1st_Gen.svg.png",
            "media_caption": "The original iPhone",
            "media_credit": "Wikimedia Commons",
            "group": "Technology",
            "background_color": "#000000",
            "text_color": "#ffffff",
        },
        {
            "title": "Moon Landing",
            "description": "Neil Armstrong becomes the first human to walk on the Moon.",
            "start_date": datetime(1969, 7, 20),
            "media_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Aldrin_Apollo_11.jpg/220px-Aldrin_Apollo_11.jpg",
            "media_caption": "Buzz Aldrin on the Moon",
            "media_credit": "NASA",
            "group": "Space",
            "background_color": "#2c3e50",
            "text_color": "#ffffff",
        },
        {
            "title": "Fall of the Berlin Wall",
            "description": "The Berlin Wall falls, symbolizing the end of the Cold War.",
            "start_date": datetime(1989, 11, 9),
            "media_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Berlin_Wall_1989.jpg/220px-Berlin_Wall_1989.jpg",
            "media_caption": "People celebrating on the Berlin Wall",
            "media_credit": "Wikimedia Commons",
            "group": "History",
            "background_color": "#e74c3c",
            "text_color": "#ffffff",
        },
        {
            "title": "First Flight",
            "description": "The Wright brothers make the first controlled, sustained flight of a powered aircraft.",
            "start_date": datetime(1903, 12, 17),
            "media_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6f/Wright_brothers_first_flight.jpg/220px-Wright_brothers_first_flight.jpg",
            "media_caption": "The Wright brothers' first flight",
            "media_credit": "Wikimedia Commons",
            "group": "Aviation",
            "background_color": "#3498db",
            "text_color": "#ffffff",
        },
        {
            "title": "Declaration of Independence",
            "description": "The United States Declaration of Independence is adopted by the Continental Congress.",
            "start_date": datetime(1776, 7, 4),
            "media_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8d/Declaration_of_Independence_%281819%29%2C_by_John_Trumbull.jpg/220px-Declaration_of_Independence_%281819%29%2C_by_John_Trumbull.jpg",
            "media_caption": "Declaration of Independence painting by John Trumbull",
            "media_credit": "Wikimedia Commons",
            "group": "History",
            "background_color": "#8b4513",
            "text_color": "#ffffff",
        },
        {
            "title": "First Electric Light Bulb",
            "description": "Thomas Edison demonstrates the first practical incandescent light bulb.",
            "start_date": datetime(1879, 10, 21),
            "media_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9d/Edison_bulb.jpg/220px-Edison_bulb.jpg",
            "media_caption": "Early Edison light bulb",
            "media_credit": "Wikimedia Commons",
            "group": "Technology",
            "background_color": "#f39c12",
            "text_color": "#000000",
        },
    ]

    return events


def main() -> None:
    """Main function to populate the database"""
    with app.app_context():
        # Clear existing events
        Event.query.delete()

        # Create sample events
        events = create_sample_events()

        for event_data in events:
            event = Event(**event_data)
            db.session.add(event)

        # Commit all events
        db.session.commit()

        print(f"Successfully added {len(events)} sample events to the database!")
        print("You can now run the application and view the timeline.")


if __name__ == "__main__":
    main()
