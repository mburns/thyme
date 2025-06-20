#!/usr/bin/env python3
"""
Advanced Wikidata Import Script using SPARQL

This script uses SPARQL queries to pull events from Wikidata and inserts them into the timeline database.
It provides more comprehensive and accurate data retrieval than the basic API version.
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

# Add the project root to the path so we can import thyme
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from thyme import Event, app, db


class WikidataSPARQLImporter:
    """Advanced importer for Wikidata events using SPARQL"""

    def __init__(self):
        self.sparql_url = "https://query.wikidata.org/sparql"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Thyme Timeline App/1.0 (https://github.com/yourusername/thyme)",
                "Accept": "application/sparql-results+json",
            }
        )

    def execute_sparql_query(self, query: str) -> List[Dict[str, Any]]:
        """Execute a SPARQL query and return results"""
        try:
            response = self.session.get(
                self.sparql_url, params={"query": query, "format": "json"}
            )
            response.raise_for_status()
            data = response.json()
            return data.get("results", {}).get("bindings", [])
        except Exception as e:
            print(f"Error executing SPARQL query: {e}")
            return []

    def parse_wikidata_date(self, date_str: str) -> Optional[datetime]:
        """Parse Wikidata date format"""
        try:
            # Wikidata dates are in format: +2023-01-01T00:00:00Z
            if date_str.startswith("+"):
                date_str = date_str[1:]

            # Parse the date part (before T)
            date_part = date_str.split("T")[0]
            return datetime.strptime(date_part, "%Y-%m-%d")
        except Exception as e:
            print(f"Error parsing date {date_str}: {e}")
            return None

    def get_image_url(self, image_name: str) -> str:
        """Convert Wikidata image name to Wikimedia Commons URL"""
        if not image_name:
            return ""

        # Clean the image name
        image_name = image_name.replace(" ", "_")

        # Generate Wikimedia Commons URL
        return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{image_name[:1]}/{image_name[:2]}/{image_name}/220px-{image_name}"

    def import_us_presidents(self) -> List[Event]:
        """Import US Presidents using SPARQL"""
        print("Importing US Presidents...")
        events = []

        query = """
        SELECT ?president ?presidentLabel ?birthDate ?deathDate ?image ?description
        WHERE {
          ?president wdt:P39 wd:Q11696 .  # Position held: President of the United States
          OPTIONAL { ?president wdt:P569 ?birthDate . }
          OPTIONAL { ?president wdt:P570 ?deathDate . }
          OPTIONAL { ?president wdt:P18 ?image . }
          OPTIONAL { ?president schema:description ?description . FILTER(LANG(?description) = "en") }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
        }
        ORDER BY ?birthDate
        LIMIT 30
        """

        results = self.execute_sparql_query(query)

        for result in results:
            president_label = result.get("presidentLabel", {}).get(
                "value", "Unknown President"
            )
            birth_date = result.get("birthDate", {}).get("value", "")
            death_date = result.get("deathDate", {}).get("value", "")
            image = result.get("image", {}).get("value", "")
            description = result.get("description", {}).get("value", "")

            # Create birth event
            if birth_date:
                birth_datetime = self.parse_wikidata_date(birth_date)
                if birth_datetime:
                    event = Event(
                        title=f"Birth of {president_label}",
                        description=(
                            f"Birth of {president_label}, {description}"
                            if description
                            else f"Birth of {president_label}"
                        ),
                        start_date=birth_datetime,
                        media_url=self.get_image_url(image),
                        media_caption=president_label,
                        media_credit="Wikimedia Commons",
                        group="Presidents",
                        background_color="#1f4e79",
                        text_color="#ffffff",
                    )
                    events.append(event)

            # Create death event
            if death_date:
                death_datetime = self.parse_wikidata_date(death_date)
                if death_datetime:
                    event = Event(
                        title=f"Death of {president_label}",
                        description=(
                            f"Death of {president_label}, {description}"
                            if description
                            else f"Death of {president_label}"
                        ),
                        start_date=death_datetime,
                        media_url=self.get_image_url(image),
                        media_caption=president_label,
                        media_credit="Wikimedia Commons",
                        group="Presidents",
                        background_color="#8b0000",
                        text_color="#ffffff",
                    )
                    events.append(event)

        return events

    def import_famous_scientists(self) -> List[Event]:
        """Import famous scientists using SPARQL"""
        print("Importing famous scientists...")
        events = []

        query = """
        SELECT ?scientist ?scientistLabel ?birthDate ?deathDate ?image ?description
        WHERE {
          ?scientist wdt:P106 wd:Q37226 .  # Occupation: scientist
          ?scientist wdt:P569 ?birthDate .
          OPTIONAL { ?scientist wdt:P570 ?deathDate . }
          OPTIONAL { ?scientist wdt:P18 ?image . }
          OPTIONAL { ?scientist schema:description ?description . FILTER(LANG(?description) = "en") }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
        }
        ORDER BY DESC(?birthDate)
        LIMIT 20
        """

        results = self.execute_sparql_query(query)

        for result in results:
            scientist_label = result.get("scientistLabel", {}).get(
                "value", "Unknown Scientist"
            )
            birth_date = result.get("birthDate", {}).get("value", "")
            death_date = result.get("deathDate", {}).get("value", "")
            image = result.get("image", {}).get("value", "")
            description = result.get("description", {}).get("value", "")

            # Create birth event
            if birth_date:
                birth_datetime = self.parse_wikidata_date(birth_date)
                if birth_datetime:
                    event = Event(
                        title=f"Birth of {scientist_label}",
                        description=(
                            f"Birth of {scientist_label}, {description}"
                            if description
                            else f"Birth of {scientist_label}"
                        ),
                        start_date=birth_datetime,
                        media_url=self.get_image_url(image),
                        media_caption=scientist_label,
                        media_credit="Wikimedia Commons",
                        group="Scientists",
                        background_color="#2e8b57",
                        text_color="#ffffff",
                    )
                    events.append(event)

            # Create death event
            if death_date:
                death_datetime = self.parse_wikidata_date(death_date)
                if death_datetime:
                    event = Event(
                        title=f"Death of {scientist_label}",
                        description=(
                            f"Death of {scientist_label}, {description}"
                            if description
                            else f"Death of {scientist_label}"
                        ),
                        start_date=death_datetime,
                        media_url=self.get_image_url(image),
                        media_caption=scientist_label,
                        media_credit="Wikimedia Commons",
                        group="Scientists",
                        background_color="#8b0000",
                        text_color="#ffffff",
                    )
                    events.append(event)

        return events

    def import_major_wars(self) -> List[Event]:
        """Import major wars using SPARQL"""
        print("Importing major wars...")
        events = []

        query = """
        SELECT ?war ?warLabel ?startDate ?endDate ?image ?description
        WHERE {
          ?war wdt:P31 wd:Q198 .  # Instance of: war
          ?war wdt:P580 ?startDate .
          OPTIONAL { ?war wdt:P582 ?endDate . }
          OPTIONAL { ?war wdt:P18 ?image . }
          OPTIONAL { ?war schema:description ?description . FILTER(LANG(?description) = "en") }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
        }
        ORDER BY ?startDate
        LIMIT 15
        """

        results = self.execute_sparql_query(query)

        for result in results:
            war_label = result.get("warLabel", {}).get("value", "Unknown War")
            start_date = result.get("startDate", {}).get("value", "")
            end_date = result.get("endDate", {}).get("value", "")
            image = result.get("image", {}).get("value", "")
            description = result.get("description", {}).get("value", "")

            if start_date:
                start_datetime = self.parse_wikidata_date(start_date)
                if start_datetime:
                    event = Event(
                        title=f"Start of {war_label}",
                        description=(
                            f"Start of {war_label}, {description}"
                            if description
                            else f"Start of {war_label}"
                        ),
                        start_date=start_datetime,
                        end_date=(
                            self.parse_wikidata_date(end_date) if end_date else None
                        ),
                        media_url=self.get_image_url(image),
                        media_caption=war_label,
                        media_credit="Wikimedia Commons",
                        group="Wars",
                        background_color="#dc143c",
                        text_color="#ffffff",
                    )
                    events.append(event)

        return events

    def import_technological_inventions(self) -> List[Event]:
        """Import technological inventions using SPARQL"""
        print("Importing technological inventions...")
        events = []

        query = """
        SELECT ?invention ?inventionLabel ?inventionDate ?image ?description
        WHERE {
          ?invention wdt:P31 wd:Q11028 .  # Instance of: invention
          ?invention wdt:P585 ?inventionDate .
          OPTIONAL { ?invention wdt:P18 ?image . }
          OPTIONAL { ?invention schema:description ?description . FILTER(LANG(?description) = "en") }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
        }
        ORDER BY ?inventionDate
        LIMIT 20
        """

        results = self.execute_sparql_query(query)

        for result in results:
            invention_label = result.get("inventionLabel", {}).get(
                "value", "Unknown Invention"
            )
            invention_date = result.get("inventionDate", {}).get("value", "")
            image = result.get("image", {}).get("value", "")
            description = result.get("description", {}).get("value", "")

            if invention_date:
                invention_datetime = self.parse_wikidata_date(invention_date)
                if invention_datetime:
                    event = Event(
                        title=f"Invention of {invention_label}",
                        description=(
                            f"Invention of {invention_label}, {description}"
                            if description
                            else f"Invention of {invention_label}"
                        ),
                        start_date=invention_datetime,
                        media_url=self.get_image_url(image),
                        media_caption=invention_label,
                        media_credit="Wikimedia Commons",
                        group="Technology",
                        background_color="#4169e1",
                        text_color="#ffffff",
                    )
                    events.append(event)

        return events

    def import_space_events(self) -> List[Event]:
        """Import space exploration events using SPARQL"""
        print("Importing space events...")
        events = []

        query = """
        SELECT ?event ?eventLabel ?eventDate ?image ?description
        WHERE {
          ?event wdt:P31 wd:Q40218 .  # Instance of: spaceflight
          ?event wdt:P585 ?eventDate .
          OPTIONAL { ?event wdt:P18 ?image . }
          OPTIONAL { ?event schema:description ?description . FILTER(LANG(?description) = "en") }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }
        }
        ORDER BY ?eventDate
        LIMIT 15
        """

        results = self.execute_sparql_query(query)

        for result in results:
            event_label = result.get("eventLabel", {}).get(
                "value", "Unknown Space Event"
            )
            event_date = result.get("eventDate", {}).get("value", "")
            image = result.get("image", {}).get("value", "")
            description = result.get("description", {}).get("value", "")

            if event_date:
                event_datetime = self.parse_wikidata_date(event_date)
                if event_datetime:
                    event = Event(
                        title=event_label,
                        description=(
                            f"{event_label}, {description}"
                            if description
                            else event_label
                        ),
                        start_date=event_datetime,
                        media_url=self.get_image_url(image),
                        media_caption=event_label,
                        media_credit="Wikimedia Commons",
                        group="Space",
                        background_color="#2c3e50",
                        text_color="#ffffff",
                    )
                    events.append(event)

        return events


def main():
    """Main function to import Wikidata events using SPARQL"""
    print("Starting advanced Wikidata import using SPARQL...")

    with app.app_context():
        # Create importer
        importer = WikidataSPARQLImporter()

        # Import different types of events
        all_events = []

        # Import US Presidents
        presidents = importer.import_us_presidents()
        all_events.extend(presidents)
        print(f"Imported {len(presidents)} president events")

        # Import famous scientists
        scientists = importer.import_famous_scientists()
        all_events.extend(scientists)
        print(f"Imported {len(scientists)} scientist events")

        # Import major wars
        wars = importer.import_major_wars()
        all_events.extend(wars)
        print(f"Imported {len(wars)} war events")

        # Import technological inventions
        inventions = importer.import_technological_inventions()
        all_events.extend(inventions)
        print(f"Imported {len(inventions)} invention events")

        # Import space events
        space_events = importer.import_space_events()
        all_events.extend(space_events)
        print(f"Imported {len(space_events)} space events")

        # Add events to database
        print(f"Adding {len(all_events)} events to database...")
        for event in all_events:
            db.session.add(event)

        db.session.commit()

        print(
            f"Successfully imported {len(all_events)} events from Wikidata using SPARQL!"
        )
        print("You can now view the timeline at http://localhost:5000")


if __name__ == "__main__":
    main()
