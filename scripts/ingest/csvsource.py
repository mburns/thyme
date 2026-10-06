"""Declarative CSV sources: a TOML spec instead of a Python adapter.

Most datasets are CSV files with an id, a name, a date and a few related
ids. A spec under ``scripts/ingest/specs/`` describes how such files map
onto entities, events, participants and identifiers, and :class:`CsvSource`
does the rest. Templates are ``{column}`` substitutions; ``{column|int}``
turns ``"1990.0"`` into ``1990``.

Spec shape (see ``specs/nba.toml`` for a complete example)::

    slug = "nba"                 # also name, homepage, license, description
    files = ["sports/nba/csv/*.csv"]   # globs under data/, fingerprinted
    category = "basketball"      # default event category
    min_year = 1800              # rows dated outside [min_year, max_year]
    max_year = 2030              # are skipped as bad data

    [[entities]]
    file = "sports/nba/csv/common_player_info.csv"
    kind = "person"
    id = "{person_id}"
    name = "{display_first_last}"
    identifiers = { nba = "{person_id}" }   # scheme -> template

    [[events]]
    file = "..."
    id = "{person_id}:life"
    entity = "person:{person_id}"         # kind:id of the owner
    kind = "life"
    label = "{display_first_last}"
    start = "{birthdate}"                 # a date template, or a table
    end = "{deathdate}"                   #   { year = "...", month = "...", day = "..." }
    span = true
    require = ["birthdate"]               # columns that must be non-empty
    when = { draft_type = "Draft" }       # column == value filters
    detail = { school = "{school}" }      # extra columns kept as JSON

    [[participants]]
    file = "..."
    event = "game:{game_id}"
    entity = "team:{team_id_away}"
    role = "away"

Dates accept ``YYYY``, ``YYYY-MM``, ``YYYY-MM-DD`` (optionally followed by a
time), ``1990.0``, ``M/D/YYYY``, or a table of year/month/day templates.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from ingest.core import (
    Entity,
    Event,
    Identifier,
    Participant,
    Source,
    SyncContext,
    iso_date,
    read_csv,
)

SPEC_DIR = Path(__file__).parent / "specs"

_TEMPLATE = re.compile(r"\{([^{}|]+)(?:\|(int))?\}")
_ISO = re.compile(r"^(-?\d{1,4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?(?:[ T.].*)?$")
_FLOAT_YEAR = re.compile(r"^(-?\d{1,4})\.0+$")
_US = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def render(template: str, row: dict[str, str]) -> str:
    """Substitute ``{column}`` and ``{column|int}`` from a CSV row."""

    def sub(m: re.Match[str]) -> str:
        value = row.get(m.group(1), "").strip()
        if m.group(2) == "int":
            try:
                return str(int(float(value)))
            except ValueError:
                return value
        return value

    return _TEMPLATE.sub(sub, template)


def parse_date(text: str) -> tuple[str, str, int] | None:
    """Parse the date formats CSV exports use into (iso, precision, year)."""
    s = text.strip()
    if not s:
        return None
    m = _FLOAT_YEAR.match(s)
    if m:
        return iso_date(int(m.group(1))) + (int(m.group(1)),)
    m = _US.match(s)
    if m:
        month, day, year = (int(g) for g in m.groups())
        return iso_date(year, month, day) + (year,)
    m = _ISO.match(s)
    if m:
        year = int(m.group(1))
        month = int(m.group(2)) if m.group(2) else None
        day = int(m.group(3)) if m.group(3) else None
        if month == 0:
            month, day = None, None
        if day == 0:
            day = None
        return iso_date(year, month, day) + (year,)
    return None


def _date_from_spec(
    spec: str | dict[str, str], row: dict[str, str]
) -> tuple[str, str, int] | None:
    if isinstance(spec, str):
        return parse_date(render(spec, row))
    year = render(spec.get("year", ""), row)
    if not year.strip():
        return None
    try:
        y = int(float(year))
        month_text = render(spec.get("month", ""), row)
        day_text = render(spec.get("day", ""), row)
        month = int(float(month_text)) if month_text.strip() else None
        day = int(float(day_text)) if day_text.strip() and month else None
    except ValueError:
        return None
    if month is not None and not 1 <= month <= 12:
        month, day = None, None
    if day is not None and not 1 <= day <= 31:
        day = None
    return iso_date(y, month, day) + (y,)


def _passes(block: dict[str, Any], row: dict[str, str]) -> bool:
    for column in block.get("require", ()):
        if not row.get(column, "").strip():
            return False
    for column, value in block.get("when", {}).items():
        if row.get(column, "").strip() != value:
            return False
    return True


def _typed(value: str, template: str) -> int | str | None:
    """Detail values rendered through ``|int`` are stored as JSON numbers."""
    if not value:
        return None
    if "|int}" in template and re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def _split_ref(ref: str) -> tuple[str, str]:
    kind, _, external_id = ref.partition(":")
    return kind, external_id


class CsvSource(Source):
    """A source whose behaviour comes entirely from a spec dict."""

    def __init__(self, spec: dict[str, Any]) -> None:
        self.spec = spec
        self.slug = spec["slug"]
        self.name = spec.get("name", self.slug)
        self.homepage = spec.get("homepage")
        self.license = spec.get("license")
        self.description = spec.get("description")
        self.file_patterns = tuple(spec.get("files", ()))
        self.min_year = int(spec.get("min_year", -10000))
        self.max_year = int(spec.get("max_year", 9999))
        self.default_category = spec.get("category", self.slug)

    def _rows(self, ctx: SyncContext, file: str) -> Iterator[dict[str, str]]:
        path = ctx.data_dir / file
        if not path.exists():
            return iter(())
        return read_csv(path, ctx.limit)

    def entities(self, ctx: SyncContext) -> Iterable[Entity]:
        for block in self.spec.get("entities", ()):
            for row in self._rows(ctx, block["file"]):
                if not _passes(block, row):
                    continue
                external_id = render(block["id"], row)
                name = render(block["name"], row)
                if not external_id or not name:
                    continue
                yield Entity(
                    external_id=external_id,
                    kind=block["kind"],
                    name=name,
                    description=render(block["description"], row) or None
                    if "description" in block
                    else None,
                    wikidata_id=render(block["wikidata_id"], row) or None
                    if "wikidata_id" in block
                    else None,
                    url=render(block["url"], row) or None if "url" in block else None,
                )

    def identifiers(self, ctx: SyncContext) -> Iterable[Identifier]:
        for block in self.spec.get("entities", ()):
            schemes: dict[str, str] = block.get("identifiers", {})
            if not schemes:
                continue
            for row in self._rows(ctx, block["file"]):
                if not _passes(block, row):
                    continue
                external_id = render(block["id"], row)
                if not external_id:
                    continue
                for scheme, template in schemes.items():
                    value = render(template, row)
                    if value:
                        yield Identifier(block["kind"], external_id, scheme, value)

    def events(self, ctx: SyncContext) -> Iterable[Event]:
        for block in self.spec.get("events", ()):
            entity_ref = block["entity"]
            kind = block["kind"]
            span = bool(block.get("span", False))
            category_template = block.get("category", self.default_category)
            detail_spec: dict[str, str] = block.get("detail", {})
            for row in self._rows(ctx, block["file"]):
                if not _passes(block, row):
                    continue
                start = _date_from_spec(block["start"], row)
                if start is None or not self.min_year <= start[2] <= self.max_year:
                    continue
                end = _date_from_spec(block["end"], row) if "end" in block else None
                if end is not None and not self.min_year <= end[2] <= self.max_year:
                    end = None
                external_id = render(block["id"], row)
                label = render(block["label"], row)
                if not external_id or not label:
                    continue
                entity_kind, entity_id = _split_ref(render(entity_ref, row))
                detail = {
                    key: _typed(render(template, row), template)
                    for key, template in detail_spec.items()
                }
                yield Event(
                    external_id=external_id,
                    entity_kind=entity_kind,
                    entity_external_id=entity_id,
                    kind=kind,
                    label=label,
                    start_date=start[0],
                    end_date=end[0] if end else None,
                    precision=start[1],
                    start_year=start[2],
                    end_year=end[2] if end else None,
                    span=span,
                    certainty=block.get("certainty", "exact"),
                    category=render(category_template, row) or self.default_category,
                    detail={k: v for k, v in detail.items() if v is not None} or None,
                )

    def participants(self, ctx: SyncContext) -> Iterable[Participant]:
        for block in self.spec.get("participants", ()):
            for row in self._rows(ctx, block["file"]):
                if not _passes(block, row):
                    continue
                event_id = render(block["event"], row)
                entity_kind, entity_id = _split_ref(render(block["entity"], row))
                role = render(block.get("role", "participant"), row)
                if event_id and entity_id and role:
                    yield Participant(event_id, entity_kind, entity_id, role)


def load_spec(path: Path) -> CsvSource:
    with path.open("rb") as f:
        return CsvSource(tomllib.load(f))


def load_specs(directory: Path = SPEC_DIR) -> list[CsvSource]:
    return [load_spec(p) for p in sorted(directory.glob("*.toml"))]
