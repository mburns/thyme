"""Timeline ingest: load dated events from registered sources into SQLite.

See ``scripts/ingest_events.py`` for the command line and ``core`` for the
sync engine and the ``Source`` interface adapters implement.
"""

from __future__ import annotations

from ingest.core import Entity, Event, Source, Syncer, SyncResult, iso_date
from ingest.sources import SOURCES

__all__ = [
    "SOURCES",
    "Entity",
    "Event",
    "Source",
    "SyncResult",
    "Syncer",
    "iso_date",
]
