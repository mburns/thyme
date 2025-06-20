#!/usr/bin/env python3
"""
TrailBase client for the timeline application.
Uses direct HTTP requests to avoid typing compatibility issues.
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


class TimelineTrailBaseSync:
    """Synchronous client for interacting with TrailBase backend for timeline data."""

    def __init__(self, base_url: str = "http://localhost:8090", auth_token: Optional[str] = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.client = httpx.Client(base_url=base_url, timeout=30.0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to TrailBase."""
        try:
            headers = {"Content-Type": "application/json"}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            if method.upper() == "GET":
                response = self.client.get(endpoint, headers=headers)
            elif method.upper() == "POST":
                response = self.client.post(endpoint, json=data, headers=headers)
            elif method.upper() == "PUT":
                response = self.client.put(endpoint, json=data, headers=headers)
            elif method.upper() == "DELETE":
                response = self.client.delete(endpoint, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"Request error: {e}")
            raise

    # People operations
    def create_person(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new person."""
        return self._make_request("POST", "/api/records/v1/people", data)

    def get_people(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get all people with optional filters."""
        endpoint = "/api/records/v1/people"
        if filters:
            # Add filters as query parameters
            params = "&".join([f"{k}={v}" for k, v in filters.items()])
            endpoint += f"?{params}"
        return self._make_request("GET", endpoint)

    def get_person(self, person_id: int) -> Optional[Dict[str, Any]]:
        """Get a person by ID."""
        try:
            return self._make_request("GET", f"/api/records/v1/people/{person_id}")
        except Exception:
            return None

    def update_person(self, person_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a person."""
        return self._make_request("PUT", f"/api/records/v1/people/{person_id}", data)

    def delete_person(self, person_id: int) -> bool:
        """Delete a person."""
        try:
            self._make_request("DELETE", f"/api/records/v1/people/{person_id}")
            return True
        except Exception:
            return False

    # Awards operations
    def create_award(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new award."""
        return self._make_request("POST", "/api/records/v1/awards", data)

    def get_awards(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get all awards with optional filters."""
        endpoint = "/api/records/v1/awards"
        if filters:
            params = "&".join([f"{k}={v}" for k, v in filters.items()])
            endpoint += f"?{params}"
        return self._make_request("GET", endpoint)

    def get_award(self, award_id: int) -> Optional[Dict[str, Any]]:
        """Get an award by ID."""
        try:
            return self._make_request("GET", f"/api/records/v1/awards/{award_id}")
        except Exception:
            return None

    # Wars operations
    def create_war(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new war."""
        return self._make_request("POST", "/api/records/v1/wars", data)

    def get_wars(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get all wars with optional filters."""
        endpoint = "/api/records/v1/wars"
        if filters:
            params = "&".join([f"{k}={v}" for k, v in filters.items()])
            endpoint += f"?{params}"
        return self._make_request("GET", endpoint)

    def get_war(self, war_id: int) -> Optional[Dict[str, Any]]:
        """Get a war by ID."""
        try:
            return self._make_request("GET", f"/api/records/v1/wars/{war_id}")
        except Exception:
            return None

    # Inventions operations
    def create_invention(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new invention."""
        return self._make_request("POST", "/api/records/v1/inventions", data)

    def get_inventions(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get all inventions with optional filters."""
        endpoint = "/api/records/v1/inventions"
        if filters:
            params = "&".join([f"{k}={v}" for k, v in filters.items()])
            endpoint += f"?{params}"
        return self._make_request("GET", endpoint)

    def get_invention(self, invention_id: int) -> Optional[Dict[str, Any]]:
        """Get an invention by ID."""
        try:
            return self._make_request("GET", f"/api/records/v1/inventions/{invention_id}")
        except Exception:
            return None

    # Space events operations
    def create_space_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new space event."""
        return self._make_request("POST", "/api/records/v1/space_events", data)

    def get_space_events(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get all space events with optional filters."""
        endpoint = "/api/records/v1/space_events"
        if filters:
            params = "&".join([f"{k}={v}" for k, v in filters.items()])
            endpoint += f"?{params}"
        return self._make_request("GET", endpoint)

    def get_space_event(self, space_event_id: int) -> Optional[Dict[str, Any]]:
        """Get a space event by ID."""
        try:
            return self._make_request("GET", f"/api/records/v1/space_events/{space_event_id}")
        except Exception:
            return None

    # Events operations (legacy)
    def create_event(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new event."""
        return self._make_request("POST", "/api/records/v1/events", data)

    def get_events(self, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Get all events with optional filters."""
        endpoint = "/api/records/v1/events"
        if filters:
            params = "&".join([f"{k}={v}" for k, v in filters.items()])
            endpoint += f"?{params}"
        return self._make_request("GET", endpoint)

    def get_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        """Get an event by ID."""
        try:
            return self._make_request("GET", f"/api/records/v1/events/{event_id}")
        except Exception:
            return None

    def update_event(self, event_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an event."""
        return self._make_request("PUT", f"/api/records/v1/events/{event_id}", data)

    def delete_event(self, event_id: int) -> bool:
        """Delete an event."""
        try:
            self._make_request("DELETE", f"/api/records/v1/events/{event_id}")
            return True
        except Exception:
            return False

    # Relationship operations
    def link_person_award(self, person_id: int, award_id: int, award_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Link a person to an award."""
        data = {
            "person_id": person_id,
            "award_id": award_id,
        }
        if award_date:
            data["award_date"] = award_date.isoformat()
        return self._make_request("POST", "/api/records/v1/person_awards", data)

    def link_person_war(self, person_id: int, war_id: int, role: Optional[str] = None) -> Dict[str, Any]:
        """Link a person to a war."""
        data = {
            "person_id": person_id,
            "war_id": war_id,
        }
        if role:
            data["role"] = role
        return self._make_request("POST", "/api/records/v1/person_wars", data)

    # Timeline data generation
    def get_timeline_data(self) -> Dict[str, Any]:
        """Get all timeline data in TimelineJS3 format."""
        all_events = []

        # Get people events
        try:
            people = self.get_people()
            for person in people:
                events = self._person_to_timeline_events(person)
                all_events.extend(events)
        except Exception as e:
            print(f"Error getting people: {e}")

        # Get award events
        try:
            awards = self.get_awards()
            for award in awards:
                events = self._award_to_timeline_events(award)
                all_events.extend(events)
        except Exception as e:
            print(f"Error getting awards: {e}")

        # Get war events
        try:
            wars = self.get_wars()
            for war in wars:
                events = self._war_to_timeline_events(war)
                all_events.extend(events)
        except Exception as e:
            print(f"Error getting wars: {e}")

        # Get invention events
        try:
            inventions = self.get_inventions()
            for invention in inventions:
                events = self._invention_to_timeline_events(invention)
                all_events.extend(events)
        except Exception as e:
            print(f"Error getting inventions: {e}")

        # Get space event events
        try:
            space_events = self.get_space_events()
            for space_event in space_events:
                events = self._space_event_to_timeline_events(space_event)
                all_events.extend(events)
        except Exception as e:
            print(f"Error getting space events: {e}")

        # Get legacy events
        try:
            events = self.get_events()
            for event in events:
                timeline_event = self._event_to_timeline_format(event)
                all_events.append(timeline_event)
        except Exception as e:
            print(f"Error getting events: {e}")

        # Sort all events by start date
        all_events.sort(key=lambda x: (
            x["start_date"]["year"],
            x["start_date"]["month"],
            x["start_date"]["day"]
        ))

        return {
            "title": {
                "text": {
                    "headline": "My Timeline",
                    "text": "A timeline of important events",
                }
            },
            "events": all_events,
        }

    def _person_to_timeline_events(self, person: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert person data to timeline events."""
        events = []

        # Birth event
        if person.get("birth_date"):
            try:
                birth_date = datetime.fromisoformat(person["birth_date"].replace("Z", "+00:00"))
                events.append({
                    "start_date": {
                        "year": birth_date.year,
                        "month": birth_date.month,
                        "day": birth_date.day,
                    },
                    "text": {
                        "headline": f"Birth of {person['name']}",
                        "text": f"Birth of {person['name']}" + (f", {person['occupation']}" if person.get('occupation') else ""),
                    },
                    "media": {
                        "url": person.get("image_url", ""),
                        "caption": person["name"],
                        "credit": "Wikimedia Commons",
                    } if person.get("image_url") else None,
                    "group": "People",
                    "background": {"color": "#2e8b57"},
                    "text": {"color": "#ffffff"},
                })
            except Exception as e:
                print(f"Error processing birth date for {person.get('name', 'Unknown')}: {e}")

        # Death event
        if person.get("death_date"):
            try:
                death_date = datetime.fromisoformat(person["death_date"].replace("Z", "+00:00"))
                events.append({
                    "start_date": {
                        "year": death_date.year,
                        "month": death_date.month,
                        "day": death_date.day,
                    },
                    "text": {
                        "headline": f"Death of {person['name']}",
                        "text": f"Death of {person['name']}" + (f", {person['occupation']}" if person.get('occupation') else ""),
                    },
                    "media": {
                        "url": person.get("image_url", ""),
                        "caption": person["name"],
                        "credit": "Wikimedia Commons",
                    } if person.get("image_url") else None,
                    "group": "People",
                    "background": {"color": "#8b0000"},
                    "text": {"color": "#ffffff"},
                })
            except Exception as e:
                print(f"Error processing death date for {person.get('name', 'Unknown')}: {e}")

        return events

    def _award_to_timeline_events(self, award: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert award data to timeline events."""
        events = []

        # Get recipients for this award
        try:
            recipients = self._make_request("GET", f"/api/records/v1/person_awards?award_id={award['id']}")
            
            for recipient in recipients:
                if recipient.get("award_date"):
                    try:
                        award_date = datetime.fromisoformat(recipient["award_date"].replace("Z", "+00:00"))
                        # Get person details
                        person = self.get_person(recipient["person_id"])
                        if person:
                            events.append({
                                "start_date": {
                                    "year": award_date.year,
                                    "month": award_date.month,
                                    "day": award_date.day,
                                },
                                "text": {
                                    "headline": f"{person['name']} received {award['name']}",
                                    "text": f"{person['name']} received {award['name']}" + (f" for {award.get('description', '')}" if award.get('description') else ""),
                                },
                                "media": {
                                    "url": person.get("image_url", award.get("image_url", "")),
                                    "caption": person["name"],
                                    "credit": "Wikimedia Commons",
                                } if (person.get("image_url") or award.get("image_url")) else None,
                                "group": "Awards",
                                "background": {"color": "#FFD700"},
                                "text": {"color": "#000000"},
                            })
                    except Exception as e:
                        print(f"Error processing award date: {e}")
        except Exception as e:
            print(f"Error getting award recipients: {e}")

        return events

    def _war_to_timeline_events(self, war: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert war data to timeline events."""
        events = []

        if war.get("start_date"):
            try:
                start_date = datetime.fromisoformat(war["start_date"].replace("Z", "+00:00"))
                events.append({
                    "start_date": {
                        "year": start_date.year,
                        "month": start_date.month,
                        "day": start_date.day,
                    },
                    "end_date": {
                        "year": end_date.year,
                        "month": end_date.month,
                        "day": end_date.day,
                    } if war.get("end_date") and (end_date := datetime.fromisoformat(war["end_date"].replace("Z", "+00:00"))) else None,
                    "text": {
                        "headline": f"Start of {war['name']}",
                        "text": f"Start of {war['name']}" + (f", {war.get('description', '')}" if war.get('description') else ""),
                    },
                    "media": {
                        "url": war.get("image_url", ""),
                        "caption": war["name"],
                        "credit": "Wikimedia Commons",
                    } if war.get("image_url") else None,
                    "group": "Wars",
                    "background": {"color": "#dc143c"},
                    "text": {"color": "#ffffff"},
                })
            except Exception as e:
                print(f"Error processing war date: {e}")

        return events

    def _invention_to_timeline_events(self, invention: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert invention data to timeline events."""
        events = []

        if invention.get("invention_date"):
            try:
                invention_date = datetime.fromisoformat(invention["invention_date"].replace("Z", "+00:00"))
                
                # Get inventor details
                inventor = None
                if invention.get("inventor_id"):
                    inventor = self.get_person(invention["inventor_id"])

                events.append({
                    "start_date": {
                        "year": invention_date.year,
                        "month": invention_date.month,
                        "day": invention_date.day,
                    },
                    "text": {
                        "headline": f"Invention of {invention['name']}",
                        "text": f"Invention of {invention['name']}" + 
                               (f" by {inventor['name']}" if inventor else "") +
                               (f", {invention.get('description', '')}" if invention.get('description') else ""),
                    },
                    "media": {
                        "url": invention.get("image_url", ""),
                        "caption": invention["name"],
                        "credit": "Wikimedia Commons",
                    } if invention.get("image_url") else None,
                    "group": "Technology",
                    "background": {"color": "#4169e1"},
                    "text": {"color": "#ffffff"},
                })
            except Exception as e:
                print(f"Error processing invention date: {e}")

        return events

    def _space_event_to_timeline_events(self, space_event: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert space event data to timeline events."""
        events = []

        if space_event.get("event_date"):
            try:
                event_date = datetime.fromisoformat(space_event["event_date"].replace("Z", "+00:00"))
                events.append({
                    "start_date": {
                        "year": event_date.year,
                        "month": event_date.month,
                        "day": event_date.day,
                    },
                    "text": {
                        "headline": space_event["name"],
                        "text": f"{space_event['name']}" + (f", {space_event.get('description', '')}" if space_event.get('description') else ""),
                    },
                    "media": {
                        "url": space_event.get("image_url", ""),
                        "caption": space_event["name"],
                        "credit": "Wikimedia Commons",
                    } if space_event.get("image_url") else None,
                    "group": "Space",
                    "background": {"color": "#2c3e50"},
                    "text": {"color": "#ffffff"},
                })
            except Exception as e:
                print(f"Error processing space event date: {e}")

        return events

    def _event_to_timeline_format(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy event to TimelineJS3 format."""
        try:
            start_date = datetime.fromisoformat(event["start_date"].replace("Z", "+00:00"))
            event_data = {
                "start_date": {
                    "year": start_date.year,
                    "month": start_date.month,
                    "day": start_date.day,
                },
                "text": {"headline": event["title"], "text": event.get("description", "")},
            }

            if event.get("end_date"):
                end_date = datetime.fromisoformat(event["end_date"].replace("Z", "+00:00"))
                event_data["end_date"] = {
                    "year": end_date.year,
                    "month": end_date.month,
                    "day": end_date.day,
                }

            if event.get("media_url"):
                event_data["media"] = {
                    "url": event["media_url"],
                    "caption": event.get("media_caption", ""),
                    "credit": event.get("media_credit", ""),
                }

            if event.get("group"):
                event_data["group"] = event["group"]

            if event.get("background_color"):
                event_data["background"] = {"color": event["background_color"]}

            if event.get("text_color"):
                event_data["text"]["color"] = event["text_color"]

            return event_data
        except Exception as e:
            print(f"Error processing event: {e}")
            return {} 