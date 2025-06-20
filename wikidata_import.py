#!/usr/bin/env python3
"""
Wikidata Import Script for Timeline App

This script pulls events from Wikidata and inserts them into the timeline database.
It fetches presidents, famous people, and major world events.
"""

import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

# Add the project root to the path so we can import thyme
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thyme import Event, app, db


class WikidataImporter:
    """Importer for Wikidata events"""

    def __init__(self):
        self.base_url = "https://www.wikidata.org/w/api.php"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Thyme Timeline App/1.0 (https://github.com/yourusername/thyme)"
            }
        )

    def search_entities(
        self, query: str, entity_type: str = "item"
    ) -> List[Dict[str, Any]]:
        """Search for entities in Wikidata"""
        params = {
            "action": "wbsearchentities",
            "format": "json",
            "language": "en",
            "type": entity_type,
            "search": query,
            "limit": 10,
        }

        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("search", [])
        except Exception as e:
            print(f"Error searching for {query}: {e}")
            return []

    def get_entity_data(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed data for a Wikidata entity"""
        params = {
            "action": "wbgetentities",
            "format": "json",
            "ids": entity_id,
            "languages": "en",
            "props": "labels|descriptions|claims|sitelinks",
        }

        try:
            response = self.session.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("entities", {}).get(entity_id)
        except Exception as e:
            print(f"Error getting entity {entity_id}: {e}")
            return None

    def extract_date(self, claim: Dict[str, Any]) -> Optional[datetime]:
        """Extract date from Wikidata claim"""
        try:
            time_value = claim.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            time = time_value.get("time", "")

            if not time:
                return None

            # Wikidata dates are in format: +2023-01-01T00:00:00Z
            # Remove the + and parse
            if time.startswith("+"):
                time = time[1:]

            # Parse the date part (before T)
            date_str = time.split("T")[0]
            return datetime.strptime(date_str, "%Y-%m-%d")
        except Exception as e:
            print(f"Error parsing date: {e}")
            return None

    def extract_label(self, entity_data: Dict[str, Any]) -> str:
        """Extract English label from entity data"""
        labels = entity_data.get("labels", {})
        return labels.get("en", {}).get("value", "Unknown")

    def extract_description(self, entity_data: Dict[str, Any]) -> str:
        """Extract English description from entity data"""
        descriptions = entity_data.get("descriptions", {})
        return descriptions.get("en", {}).get("value", "")

    def get_image_url(self, entity_data: Dict[str, Any]) -> Optional[str]:
        """Get image URL from entity data"""
        claims = entity_data.get("claims", {})
        image_claims = claims.get("P18", [])  # P18 is "image"

        if image_claims:
            claim = image_claims[0]
            image_name = claim.get("mainsnak", {}).get("datavalue", {}).get("value", "")
            if image_name:
                # Convert to Wikimedia Commons URL
                image_name = image_name.replace(" ", "_")
                return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{image_name[:1]}/{image_name[:2]}/{image_name}/220px-{image_name}"

        return None

    def get_birth_date(self, entity_data: Dict[str, Any]) -> Optional[datetime]:
        """Get birth date from entity data"""
        claims = entity_data.get("claims", {})
        birth_claims = claims.get("P569", [])  # P569 is "date of birth"

        if birth_claims:
            return self.extract_date(birth_claims[0])

        return None

    def get_death_date(self, entity_data: Dict[str, Any]) -> Optional[datetime]:
        """Get death date from entity data"""
        claims = entity_data.get("claims", {})
        death_claims = claims.get("P570", [])  # P570 is "date of death"

        if death_claims:
            return self.extract_date(death_claims[0])

        return None

    def get_event_date(self, entity_data: Dict[str, Any]) -> Optional[datetime]:
        """Get event date from entity data"""
        claims = entity_data.get("claims", {})

        # Try different date properties
        date_properties = [
            "P585",
            "P580",
            "P582",
        ]  # point in time, start time, end time

        for prop in date_properties:
            date_claims = claims.get(prop, [])
            if date_claims:
                date_obj = self.extract_date(date_claims[0])
                if date_obj:
                    return date_obj

        return None

    def import_presidents(self) -> List[Event]:
        """Import US Presidents"""
        print("Importing US Presidents...")
        events = []

        # Search for US Presidents
        presidents = self.search_entities("President of the United States")

        for president in presidents[:20]:  # Limit to first 20
            entity_id = president["id"]
            entity_data = self.get_entity_data(entity_id)

            if not entity_data:
                continue

            name = self.extract_label(entity_data)
            description = self.extract_description(entity_data)
            birth_date = self.get_birth_date(entity_data)
            death_date = self.get_death_date(entity_data)
            image_url = self.get_image_url(entity_data)

            if birth_date:
                event = Event(
                    title=f"Birth of {name}",
                    description=f"Birth of {name}, {description}",
                    start_date=birth_date,
                    media_url=image_url or "",
                    media_caption=name,
                    media_credit="Wikimedia Commons",
                    group="Presidents",
                    background_color="#1f4e79",
                    text_color="#ffffff",
                )
                events.append(event)

            if death_date:
                event = Event(
                    title=f"Death of {name}",
                    description=f"Death of {name}, {description}",
                    start_date=death_date,
                    media_url=image_url or "",
                    media_caption=name,
                    media_credit="Wikimedia Commons",
                    group="Presidents",
                    background_color="#8b0000",
                    text_color="#ffffff",
                )
                events.append(event)

            time.sleep(1)  # Be nice to Wikidata API

        return events

    def import_famous_people(self) -> List[Event]:
        """Import famous people from various fields"""
        print("Importing famous people...")
        events = []

        # Search queries for different types of famous people
        searches = [
            ("Albert Einstein", "scientist"),
            ("William Shakespeare", "writer"),
            ("Leonardo da Vinci", "artist"),
            ("Mozart", "composer"),
            ("Marie Curie", "scientist"),
            ("Vincent van Gogh", "artist"),
            ("Charles Darwin", "scientist"),
            ("Isaac Newton", "scientist"),
            ("Galileo Galilei", "scientist"),
            ("Beethoven", "composer"),
        ]

        for name, category in searches:
            entities = self.search_entities(name)

            if not entities:
                continue

            entity_data = self.get_entity_data(entities[0]["id"])

            if not entity_data:
                continue

            full_name = self.extract_label(entity_data)
            description = self.extract_description(entity_data)
            birth_date = self.get_birth_date(entity_data)
            death_date = self.get_death_date(entity_data)
            image_url = self.get_image_url(entity_data)

            if birth_date:
                event = Event(
                    title=f"Birth of {full_name}",
                    description=f"Birth of {full_name}, {description}",
                    start_date=birth_date,
                    media_url=image_url or "",
                    media_caption=full_name,
                    media_credit="Wikimedia Commons",
                    group=category.title(),
                    background_color="#2e8b57",
                    text_color="#ffffff",
                )
                events.append(event)

            if death_date:
                event = Event(
                    title=f"Death of {full_name}",
                    description=f"Death of {full_name}, {description}",
                    start_date=death_date,
                    media_url=image_url or "",
                    media_caption=full_name,
                    media_credit="Wikimedia Commons",
                    group=category.title(),
                    background_color="#8b0000",
                    text_color="#ffffff",
                )
                events.append(event)

            time.sleep(1)  # Be nice to Wikidata API

        return events

    def import_major_events(self) -> List[Event]:
        """Import major world events"""
        print("Importing major world events...")
        events = []

        # Search for major historical events
        event_searches = [
            ("World War II", "War"),
            ("World War I", "War"),
            ("French Revolution", "Revolution"),
            ("Industrial Revolution", "Revolution"),
            ("American Civil War", "War"),
            ("Declaration of Independence", "Politics"),
            ("Moon Landing", "Space"),
            ("Fall of Berlin Wall", "Politics"),
            ("First Flight", "Aviation"),
            ("Invention of Telephone", "Technology"),
            ("Invention of Light Bulb", "Technology"),
            ("Discovery of Penicillin", "Science"),
            ("First Computer", "Technology"),
            ("Internet", "Technology"),
            ("First iPhone", "Technology"),
        ]

        for event_name, category in event_searches:
            entities = self.search_entities(event_name)

            if not entities:
                continue

            entity_data = self.get_entity_data(entities[0]["id"])

            if not entity_data:
                continue

            full_name = self.extract_label(entity_data)
            description = self.extract_description(entity_data)
            event_date = self.get_event_date(entity_data)
            image_url = self.get_image_url(entity_data)

            if event_date:
                event = Event(
                    title=full_name,
                    description=description,
                    start_date=event_date,
                    media_url=image_url or "",
                    media_caption=full_name,
                    media_credit="Wikimedia Commons",
                    group=category,
                    background_color="#ff8c00",
                    text_color="#ffffff",
                )
                events.append(event)

            time.sleep(1)  # Be nice to Wikidata API

        return events


def main():
    """Main function to import Wikidata events"""
    print("Starting Wikidata import...")

    with app.app_context():
        # Create importer
        importer = WikidataImporter()

        # Import different types of events
        all_events = []

        # Import presidents
        presidents = importer.import_presidents()
        all_events.extend(presidents)
        print(f"Imported {len(presidents)} president events")

        # Import famous people
        famous_people = importer.import_famous_people()
        all_events.extend(famous_people)
        print(f"Imported {len(famous_people)} famous people events")

        # Import major events
        major_events = importer.import_major_events()
        all_events.extend(major_events)
        print(f"Imported {len(major_events)} major events")

        # Add events to database
        print(f"Adding {len(all_events)} events to database...")
        for event in all_events:
            db.session.add(event)

        db.session.commit()

        print(f"Successfully imported {len(all_events)} events from Wikidata!")
        print("You can now view the timeline at http://localhost:5000")


if __name__ == "__main__":
    main()
