#!/usr/bin/env python3
"""
Fetches data from Wikidata and saves it to local JSON files.
"""
import argparse
import json
import os
import time
from datetime import datetime
import sys

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class WikidataFetcher:
    """Fetches data from Wikidata's SPARQL endpoint."""

    def __init__(self):
        self.sparql_url = "https://query.wikidata.org/sparql"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Thyme Timeline App/1.0 (https://github.com/mburns/thyme)",
                "Accept": "application/sparql-results+json",
            }
        )

    def execute_sparql_query(self, query: str) -> list[dict]:
        """Executes a SPARQL query and returns the results."""
        try:
            print("Executing SPARQL query...")
            time.sleep(1)  # Be respectful to the API
            response = self.session.get(
                self.sparql_url, params={"query": query, "format": "json"}
            )
            response.raise_for_status()
            data = response.json()
            print(f"Query returned {len(data.get('results', {}).get('bindings', []))} results.")
            return data.get("results", {}).get("bindings", [])
        except requests.exceptions.RequestException as e:
            print(f"Error executing SPARQL query: {e}")
            return []

    def fetch_random_people(self, limit: int = 20):
        """Fetches random people with rich metadata."""
        query = f"""
        SELECT ?item ?itemLabel ?itemDescription ?birthDate ?deathDate ?image ?wikipediaUrl
        WHERE {{
          ?item wdt:P31 wd:Q5;       # is a human
                wdt:P569 ?birthDate. # has a birth date

          # Use a random binding to get varied results
          BIND(MD5(CONCAT(STR(?item), STR(NOW()))) as ?random).

          OPTIONAL {{ ?item wdt:P570 ?deathDate. }}
          OPTIONAL {{ ?item wdt:P18 ?image. }}
          OPTIONAL {{
            ?sitelink schema:about ?item;
                      schema:isPartOf <https://en.wikipedia.org/>;
                      schema:inLanguage "en".
            BIND(STR(?sitelink) AS ?wikipediaUrl)
          }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
        }}
        ORDER BY ?random
        LIMIT {limit}
        """
        return self.execute_sparql_query(query)

    def fetch_random_events(self, limit: int = 20):
        """Fetches random historical events and occurrences."""
        query = f"""
        SELECT ?item ?itemLabel ?itemDescription ?pointInTime ?image ?wikipediaUrl
        WHERE {{
          VALUES ?eventType {{ wd:Q189560 wd:Q3839081 wd:Q1190554 }} # Military conflict, Disaster, Occurrence
          ?item wdt:P31 ?eventType;
                wdt:P585 ?pointInTime.

          BIND(MD5(CONCAT(STR(?item), STR(NOW()))) as ?random).

          OPTIONAL {{ ?item wdt:P18 ?image. }}
          OPTIONAL {{
            ?sitelink schema:about ?item;
                      schema:isPartOf <https://en.wikipedia.org/>;
                      schema:inLanguage "en".
            BIND(STR(?sitelink) AS ?wikipediaUrl)
          }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }}
        }}
        ORDER BY ?random
        LIMIT {limit}
        """
        return self.execute_sparql_query(query)


def save_to_json(data: list[dict], file_prefix: str):
    """Saves data to a timestamped JSON file."""
    if not data:
        print("No data to save.")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"data/{file_prefix}_{timestamp}.json"
    os.makedirs("data", exist_ok=True)

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Successfully saved data to {filename}")


def main():
    parser = argparse.ArgumentParser(description="Fetch data from Wikidata.")
    parser.add_argument(
        "--type",
        choices=["people", "events"],
        required=True,
        help="The type of data to fetch.",
    )
    parser.add_argument(
        "--limit", type=int, default=20, help="Number of results to fetch."
    )
    args = parser.parse_args()

    fetcher = WikidataFetcher()

    if args.type == "people":
        data = fetcher.fetch_random_people(limit=args.limit)
        save_to_json(data, "people")
    elif args.type == "events":
        data = fetcher.fetch_random_events(limit=args.limit)
        save_to_json(data, "events")


if __name__ == "__main__":
    main() 