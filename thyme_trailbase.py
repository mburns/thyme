#!/usr/bin/env python3
"""
Flask application using TrailBase as the backend.
"""
import os
from typing import Any

from flask import Flask, jsonify, render_template, request
from trailbase_client import TimelineTrailBaseSync

app = Flask(
    __name__,
    template_folder=os.path.abspath(
        os.path.join(os.path.dirname(__file__), "templates")
    ),
)

# Initialize TrailBase client
trailbase_client = TimelineTrailBaseSync()


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/timeline")
def get_timeline_data() -> Any:
    """Return timeline data in TimelineJS3 format"""
    try:
        timeline_data = trailbase_client.get_timeline_data()
        return jsonify(timeline_data)
    except Exception as e:
        print(f"Error getting timeline data: {e}")
        return jsonify({"error": "Failed to get timeline data"}), 500


@app.route("/api/events", methods=["GET"])
def get_events() -> str:
    """Return events for the admin interface"""
    try:
        events = trailbase_client.get_events()
        return render_template("events_list.html", events=events)
    except Exception as e:
        print(f"Error getting events: {e}")
        return render_template("events_list.html", events=[])


@app.route("/api/events", methods=["POST"])
def add_event() -> Any:
    """Add a new event"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get("title") or not data.get("start_date"):
            return jsonify({"error": "Title and start_date are required"}), 400
        
        # Create the event
        event = trailbase_client.create_event(data)
        return jsonify(event), 201
    except Exception as e:
        print(f"Error adding event: {e}")
        return jsonify({"error": "Failed to add event"}), 500


@app.route("/api/events/<int:event_id>", methods=["DELETE"])
def delete_event(event_id: int) -> Any:
    """Delete an event"""
    try:
        success = trailbase_client.delete_event(event_id)
        if success:
            return jsonify({"message": "Event deleted successfully"}), 200
        else:
            return jsonify({"error": "Event not found"}), 404
    except Exception as e:
        print(f"Error deleting event: {e}")
        return jsonify({"error": "Failed to delete event"}), 500


@app.route("/admin")
def admin() -> str:
    return render_template("admin.html")


@app.route("/api/people", methods=["GET"])
def get_people() -> Any:
    """Get all people"""
    try:
        people = trailbase_client.get_people()
        return jsonify(people)
    except Exception as e:
        print(f"Error getting people: {e}")
        return jsonify({"error": "Failed to get people"}), 500


@app.route("/api/people", methods=["POST"])
def add_person() -> Any:
    """Add a new person"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get("name"):
            return jsonify({"error": "Name is required"}), 400
        
        # Create the person
        person = trailbase_client.create_person(data)
        return jsonify(person), 201
    except Exception as e:
        print(f"Error adding person: {e}")
        return jsonify({"error": "Failed to add person"}), 500


@app.route("/api/awards", methods=["GET"])
def get_awards() -> Any:
    """Get all awards"""
    try:
        awards = trailbase_client.get_awards()
        return jsonify(awards)
    except Exception as e:
        print(f"Error getting awards: {e}")
        return jsonify({"error": "Failed to get awards"}), 500


@app.route("/api/wars", methods=["GET"])
def get_wars() -> Any:
    """Get all wars"""
    try:
        wars = trailbase_client.get_wars()
        return jsonify(wars)
    except Exception as e:
        print(f"Error getting wars: {e}")
        return jsonify({"error": "Failed to get wars"}), 500


@app.route("/api/inventions", methods=["GET"])
def get_inventions() -> Any:
    """Get all inventions"""
    try:
        inventions = trailbase_client.get_inventions()
        return jsonify(inventions)
    except Exception as e:
        print(f"Error getting inventions: {e}")
        return jsonify({"error": "Failed to get inventions"}), 500


@app.route("/api/space-events", methods=["GET"])
def get_space_events() -> Any:
    """Get all space events"""
    try:
        space_events = trailbase_client.get_space_events()
        return jsonify(space_events)
    except Exception as e:
        print(f"Error getting space events: {e}")
        return jsonify({"error": "Failed to get space events"}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000) 