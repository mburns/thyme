"""Dated entries of Wikipedia list pages, ``data/wikipedia/lists/*.json``.

``scripts/wikipedia_lists_fetch.py`` saves the wikitext of bibliographies
and "List of ..." pages. This adapter reads every entry that carries a
year:

* ``{{cite book}}`` / ``{{cite journal}}`` / ``{{citation}}`` templates and
  bullet lines with an italic title (``* Author, ''Title'' (1998)``) become
  works (kind ``book`` or ``article``) with a ``publication`` instant and
  their authors as participants;
* any other bullet line that mentions a year becomes a ``listed`` instant
  on an ``entry`` entity, so a "List of earthquakes" or "List of treaties"
  is represented, if only as a stub to refine per list later.

Each list page is also an entity (kind ``list``) that takes part in every
event it contributed, which is how "everything from the Montana
bibliography" can be asked for.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ingest.core import Entity, Event, Participant, Source, SyncContext, iso_date

FILES = "wikipedia/lists/*.json"
MIN_YEAR = 1400
MAX_YEAR = 2030

_CITE = re.compile(
    r"\{\{\s*(cite\s+(?:book|journal|news|web|magazine|encyclopedia)|citation)\s*\|",
    re.I,
)
_YEAR = re.compile(r"(?<!\d)(1[4-9]\d\d|20[0-2]\d)(?!\d)")
_ITALIC_TITLE = re.compile(r"''([^']{3,200}?)''")
_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S)
_LINK = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]")
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_HTML = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


@dataclass
class Entry:
    page: str
    kind: str  # book, article, entry
    title: str
    year: int
    authors: list[str] = field(default_factory=list)
    publisher: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def external_id(self) -> str:
        key = f"{self.page}|{self.title.lower()}|{self.year}"
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def subject_of(page_title: str) -> str:
    """ "Bibliography of Montana history" -> "Montana history"."""
    for prefix in ("Bibliography of ", "List of ", "Lists of "):
        if page_title.startswith(prefix):
            return page_title[len(prefix) :]
    return page_title


def strip_markup(text: str) -> str:
    text = _REF.sub("", text)
    text = _LINK.sub(r"\1", text)
    for _ in range(3):
        text = _TEMPLATE.sub("", text)
    text = _HTML.sub("", text)
    text = text.replace("'''", "").replace("''", "")
    return _SPACE.sub(" ", text).strip(" *:;#\t")


def _template_bodies(wikitext: str) -> Iterator[tuple[str, str]]:
    """Yield (template name, body) for citation templates, braces balanced."""
    for m in _CITE.finditer(wikitext):
        depth = 2
        i = m.end()
        while i < len(wikitext) and depth > 0:
            if wikitext.startswith("{{", i):
                depth += 2
                i += 2
            elif wikitext.startswith("}}", i):
                depth -= 2
                i += 2
            else:
                i += 1
        yield m.group(1).lower(), wikitext[m.end() : i - 2]


def template_params(body: str) -> dict[str, str]:
    """Split ``|key=value`` pairs, ignoring pipes inside links or templates."""
    params: dict[str, str] = {}
    depth = 0
    part: list[str] = []
    parts: list[str] = []
    i = 0
    while i < len(body):
        two = body[i : i + 2]
        if two in ("[[", "{{"):
            depth += 1
            part.append(two)
            i += 2
        elif two in ("]]", "}}"):
            depth = max(0, depth - 1)
            part.append(two)
            i += 2
        elif body[i] == "|" and depth == 0:
            parts.append("".join(part))
            part = []
            i += 1
        else:
            part.append(body[i])
            i += 1
    parts.append("".join(part))
    for p in parts:
        key, sep, value = p.partition("=")
        if sep:
            params[key.strip().lower()] = strip_markup(value)
    return params


def _authors(params: dict[str, str]) -> list[str]:
    out: list[str] = []
    for n in ("", "1", "2", "3", "4"):
        last = params.get(f"last{n}") or params.get(f"surname{n}")
        first = params.get(f"first{n}") or params.get(f"given{n}")
        if last:
            out.append(f"{first} {last}".strip())
        elif params.get(f"author{n}"):
            out.append(params[f"author{n}"])
    if not out and params.get("authors"):
        out = [a.strip() for a in re.split(r";|, and | and ", params["authors"])]
    return [a for a in out if a]


def _year(text: str) -> int | None:
    m = _YEAR.search(text)
    return int(m.group(1)) if m else None


def parse_page(page_title: str, wikitext: str) -> list[Entry]:
    """Every dated entry of a list page, citations first, then plain lines."""
    entries: list[Entry] = []
    seen: set[str] = set()
    for name, body in _template_bodies(wikitext):
        params = template_params(body)
        title = params.get("title")
        year = _year(params.get("year") or params.get("date") or "")
        if not title or year is None or not MIN_YEAR <= year <= MAX_YEAR:
            continue
        kind = "article" if "journal" in name or params.get("journal") else "book"
        entry = Entry(
            page=page_title,
            kind=kind,
            title=title,
            year=year,
            authors=_authors(params),
            publisher=params.get("publisher") or params.get("journal"),
            detail={
                k: params[k] for k in ("isbn", "location", "volume") if params.get(k)
            },
        )
        if entry.external_id not in seen:
            seen.add(entry.external_id)
            entries.append(entry)

    # Lines that are not citation templates: an italic title with a year is
    # a book; any other line with a year is a generic list entry.
    without_templates = wikitext
    for _, body in _template_bodies(wikitext):
        without_templates = without_templates.replace(body, "")
    for raw in without_templates.splitlines():
        if not raw.startswith("*"):
            continue
        year = _year(raw)
        if year is None or not MIN_YEAR <= year <= MAX_YEAR:
            continue
        italic = _ITALIC_TITLE.search(raw)
        if italic:
            title = strip_markup(italic.group(1))
            before = strip_markup(raw[: italic.start()]).strip(" ,.")
            entry = Entry(
                page=page_title,
                kind="book",
                title=title,
                year=year,
                authors=[before] if 0 < len(before) <= 80 else [],
            )
        else:
            text = strip_markup(raw)
            if len(text) < 8:
                continue
            entry = Entry(page=page_title, kind="entry", title=text[:140], year=year)
        if entry.external_id not in seen:
            seen.add(entry.external_id)
            entries.append(entry)
    return entries


def _person_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


class WikipediaListsSource(Source):
    slug = "wikipedia_lists"
    name = "Wikipedia lists and bibliographies"
    homepage = "https://en.wikipedia.org/wiki/Lists_of_books"
    license = "CC BY-SA 4.0"
    description = (
        "Dated entries of Wikipedia bibliographies and lists: publications with "
        "their authors, and a stub event for every other listed item with a year."
    )
    file_patterns = (FILES,)

    def _pages(self, ctx: SyncContext) -> Iterator[dict[str, Any]]:
        for path in sorted(ctx.data_dir.glob(FILES)):
            with Path(path).open(encoding="utf-8") as f:
                yield json.load(f)

    def _entries(self, ctx: SyncContext) -> Iterator[tuple[dict[str, Any], Entry]]:
        n = 0
        for page in self._pages(ctx):
            for entry in parse_page(page["title"], page.get("wikitext", "")):
                if ctx.limit is not None and n >= ctx.limit:
                    return
                n += 1
                yield page, entry

    def entities(self, ctx: SyncContext) -> Iterable[Entity]:
        seen_people: set[str] = set()
        for page in self._pages(ctx):
            yield Entity(
                external_id=f"page:{page['pageid']}",
                kind="list",
                name=page["title"],
                description=f"Wikipedia list, revision {page.get('revid')}",
                url=page.get("url"),
            )
        for _, entry in self._entries(ctx):
            yield Entity(
                external_id=entry.external_id,
                kind=entry.kind,
                name=entry.title,
                description=", ".join(entry.authors) or None,
            )
            for author in entry.authors:
                pid = _person_id(author)
                if pid and pid not in seen_people:
                    seen_people.add(pid)
                    yield Entity(external_id=pid, kind="person", name=author)

    def events(self, ctx: SyncContext) -> Iterable[Event]:
        for page, entry in self._entries(ctx):
            date, precision = iso_date(entry.year)
            publication = entry.kind in ("book", "article")
            yield Event(
                external_id=entry.external_id,
                entity_kind=entry.kind,
                entity_external_id=entry.external_id,
                kind="publication" if publication else "listed",
                label=entry.title,
                start_date=date,
                precision=precision,
                start_year=entry.year,
                category=entry.kind if publication else "list entry",
                detail={
                    "authors": entry.authors or None,
                    "publisher": entry.publisher,
                    "list": page["title"],
                    "subject": subject_of(page["title"]),
                    **entry.detail,
                },
            )

    def participants(self, ctx: SyncContext) -> Iterable[Participant]:
        for page, entry in self._entries(ctx):
            yield Participant(
                event_external_id=entry.external_id,
                entity_kind="list",
                entity_external_id=f"page:{page['pageid']}",
                role="list",
            )
            for author in entry.authors:
                pid = _person_id(author)
                if pid:
                    yield Participant(
                        event_external_id=entry.external_id,
                        entity_kind="person",
                        entity_external_id=pid,
                        role="author",
                    )
