"""Registry of source adapters, keyed by slug.

To add a dataset, implement a ``Source`` subclass in this package and add an
instance here. The CLI, status listing and tests pick it up automatically.
"""

from __future__ import annotations

from ingest.core import Source
from ingest.sources.imdb import ImdbSource
from ingest.sources.lahman import LahmanSource
from ingest.sources.olympics import OlympicsSource
from ingest.sources.wikidata_age import WikidataAgeSource

SOURCES: dict[str, Source] = {
    s.slug: s
    for s in (
        ImdbSource(),
        LahmanSource(),
        OlympicsSource(),
        WikidataAgeSource(),
    )
}

__all__ = ["SOURCES"]
