"""Registry of source adapters, keyed by slug.

Python adapters live in this package; declarative CSV sources are TOML
specs under ``scripts/ingest/specs/``. The CLI, status listing and tests
pick both kinds up automatically.
"""

from __future__ import annotations

from ingest.core import Source
from ingest.csvsource import load_specs
from ingest.sources.imdb import ImdbSource
from ingest.sources.lahman import LahmanSource
from ingest.sources.olympics import OlympicsSource
from ingest.sources.wikidata import WikidataSource
from ingest.sources.wikidata_age import WikidataAgeSource
from ingest.sources.wikipedia_lists import WikipediaListsSource

SOURCES: dict[str, Source] = {
    s.slug: s
    for s in (
        ImdbSource(),
        LahmanSource(),
        OlympicsSource(),
        WikidataAgeSource(),
        WikidataSource(),
        WikipediaListsSource(),
        *load_specs(),
    )
}

__all__ = ["SOURCES"]
