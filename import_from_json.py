#!/usr/bin/env python3
"""
Imports data from local JSON files into TrailBase.
"""
import json
import os
from datetime import datetime
from typing import Optional

from trailbase_client import TimelineTrailBaseSync


def parse_wikidata_date(date_str: str) -> Optional[datetime]:
    """Parses a Wikidata date string into a datetime object."""
    try:
        if date_str.startswith("+"):
            date_str = date_str[1:]
        date_part = date_str.split("T")[0]
        return datetime.strptime(date_part, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def get_value(item: dict, key: str) -> Optional[str]:
    """Safely gets a value from a nested dictionary."""
    return item.get(key, {}).get("value")


def process_people_file(filepath: str, trailbase_client: TimelineTrailBaseSync):
    """Processes a JSON file containing people data."""
    print(f"Processing people file: {filepath}")
    with open(filepath, "r") as f:
        data = json.load(f)

    for item in data:
        wikidata_id = get_value(item, "item").split("/")[-1]
        
        # Check if person already exists
        existing_people = trailbase_client.get_people({"wikidata_id": wikidata_id})
        if existing_people:
            print(f"  - Skipping existing person: {get_value(item, 'itemLabel')}")
            continue

        person_data = {
            "name": get_value(item, "itemLabel"),
            "description": get_value(item, "itemDescription"),
            "wikidata_id": wikidata_id,
            "image_url": get_value(item, "image"),
        }

        # Add dates if available
        birth_date = parse_wikidata_date(get_value(item, "birthDate"))
        if birth_date:
            person_data["birth_date"] = birth_date.isoformat()

        death_date = parse_wikidata_date(get_value(item, "deathDate"))
        if death_date:
            person_data["death_date"] = death_date.isoformat()

        try:
            trailbase_client.create_person(person_data)
            print(f"  - Added new person: {person_data['name']}")
        except Exception as e:
            print(f"  - Error adding person {person_data['name']}: {e}")


def process_events_file(filepath: str, trailbase_client: TimelineTrailBaseSync):
    """Processes a JSON file containing event data."""
    print(f"Processing events file: {filepath}")
    with open(filepath, "r") as f:
        data = json.load(f)

    for item in data:
        event_data = {
            "title": get_value(item, "itemLabel"),
            "description": get_value(item, "itemDescription"),
            "group": "General Events",
        }

        # Add start date if available
        start_date = parse_wikidata_date(get_value(item, "pointInTime"))
        if start_date:
            event_data["start_date"] = start_date.isoformat()
        else:
            print(f"  - Skipping event without date: {event_data['title']}")
            continue

        # Add media if available
        image_url = get_value(item, "image")
        if image_url:
            event_data["media_url"] = image_url

        try:
            trailbase_client.create_event(event_data)
            print(f"  - Added new event: {event_data['title']}")
        except Exception as e:
            print(f"  - Error adding event {event_data['title']}: {e}")


def main():
    """Main function to import data from all new JSON files."""
    trailbase_client = TimelineTrailBaseSync()
    
    if not os.path.exists("data"):
        print("No data directory found. Run fetch_wikidata.py first.")
        return

    for filename in os.listdir("data"):
        if not filename.endswith(".json"):
            continue

        filepath = os.path.join("data", filename)
        if filename.startswith("people"):
            process_people_file(filepath, trailbase_client)
        elif filename.startswith("events"):
            process_events_file(filepath, trailbase_client)
        
        # Move processed file to avoid re-importing
        processed_path = os.path.join("data", "processed", filename)
        os.makedirs(os.path.dirname(processed_path), exist_ok=True)
        os.rename(filepath, processed_path)
        print(f"Moved processed file to: {processed_path}")

    print("\nImport process complete.")


if __name__ == "__main__":
    main() 