"""Wikidata, from the extract that ``scripts/wikidata_extract.py`` writes.

``data/wikidata/items.jsonl.gz`` holds one record per human, conflict,
country and award; ``labels.jsonl.gz`` names everything those records refer
to. This adapter turns them into:

* entities: people, conflicts, countries, awards (with Wikipedia links)
* events: a life span per person, award instants, position-held spans,
  a span per conflict, an existence span per country
* participants: who received an award, who fought in a conflict (people
  via P607 and countries via P710)
* identifiers: IMDb, Baseball-Reference and Olympedia ids, the exact keys
  that link these entities to the IMDB, Lahman and Olympics sources

Dates coarser than a year (decade, century) are kept at year precision
with ``certainty='circa'``. Years before 1 CE are negative.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import IO, Any

from ingest.core import (
    Entity,
    Event,
    Identifier,
    Participant,
    Source,
    SyncContext,
    iso_date,
)

ITEMS = "wikidata/items.jsonl*"
LABELS = "wikidata/labels.jsonl*"
ID_SCHEMES = (
    "imdb",
    "bbref",
    "olympedia",
    "musicbrainz",
    "nba",
    "steam",
    "openlibrary",
)


def _open(path: Path) -> IO[str]:
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return path.open(encoding="utf-8")


def _read_jsonl(path: Path, limit: int | None = None) -> Iterator[dict[str, Any]]:
    with _open(path) as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                return
            if line.strip():
                yield json.loads(line)


def to_date(d: dict[str, Any] | None) -> tuple[str, str, int, bool] | None:
    """Extract date dict -> (iso text, precision, year, circa)."""
    if not d or "year" not in d:
        return None
    text, precision = iso_date(int(d["year"]), d.get("month"), d.get("day"))
    return text, precision, int(d["year"]), bool(d.get("circa"))


def _url(item: dict[str, Any]) -> str:
    title = item.get("enwiki")
    if title:
        return "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")
    return f"https://www.wikidata.org/wiki/{item['id']}"


class WikidataSource(Source):
    slug = "wikidata"
    name = "Wikidata"
    homepage = "https://www.wikidata.org/"
    license = "CC0"
    description = (
        "People, conflicts, countries and awards from the Wikidata dump: life "
        "spans, awards received, positions held, wars with their participants."
    )
    file_patterns = (ITEMS, LABELS)

    def _items_path(self, ctx: SyncContext) -> Path | None:
        found = sorted(ctx.data_dir.glob(ITEMS))
        return found[-1] if found else None

    def _labels_path(self, ctx: SyncContext) -> Path | None:
        found = sorted(ctx.data_dir.glob(LABELS))
        return found[-1] if found else None

    def _items(self, ctx: SyncContext) -> Iterator[dict[str, Any]]:
        path = self._items_path(ctx)
        if path is None:
            return iter(())
        return _read_jsonl(path, ctx.limit)

    def _referenced_labels(self, ctx: SyncContext) -> dict[str, dict[str, Any]]:
        """Labels of items the selected items refer to but are not themselves.

        First pass over items collects the referenced ids; a pass over the
        (large) labels file keeps only those, so memory stays proportional
        to the number of distinct awards, positions and occupations.
        """
        selected: set[str] = set()
        wanted: set[str] = set()
        for item in self._items(ctx):
            selected.add(item["id"])
            for key in (
                "awards",
                "positions",
                "occupations",
                "participants",
                "conflicts",
            ):
                for rel in item.get(key, ()):
                    wanted.add(rel["id"])
        wanted -= selected
        labels: dict[str, dict[str, Any]] = {}
        path = self._labels_path(ctx)
        if path is None or not wanted:
            return labels
        for rec in _read_jsonl(path):
            if rec["id"] in wanted and rec.get("label"):
                labels[rec["id"]] = rec
        return labels

    def load(self, ctx: SyncContext) -> None:
        labels = self._referenced_labels(ctx)
        selected = {item["id"]: item["kind"] for item in self._items(ctx)}
        ctx.options["_wd_labels"] = labels
        ctx.options["_wd_selected"] = selected
        super().load(ctx)

    def entities(self, ctx: SyncContext) -> Iterable[Entity]:
        labels: dict[str, dict[str, Any]] = ctx.options.get("_wd_labels", {})
        emitted_awards: set[str] = set()
        for item in self._items(ctx):
            yield Entity(
                external_id=item["id"],
                kind=item["kind"],
                name=item["label"],
                description=item.get("description"),
                wikidata_id=item["id"],
                url=_url(item),
            )
            # Awards referenced by people but not selected as items still
            # need an entity so the award participation can resolve.
            for rel in item.get("awards", ()):
                aid = rel["id"]
                if aid in labels and aid not in emitted_awards:
                    emitted_awards.add(aid)
                    yield Entity(
                        external_id=aid,
                        kind="award",
                        name=labels[aid]["label"],
                        description=labels[aid].get("description"),
                        wikidata_id=aid,
                        url=f"https://www.wikidata.org/wiki/{aid}",
                    )

    def events(self, ctx: SyncContext) -> Iterable[Event]:
        labels: dict[str, dict[str, Any]] = ctx.options.get("_wd_labels", {})
        for item in self._items(ctx):
            kind = item["kind"]
            if kind == "person":
                yield from self._person_events(item, labels)
            elif kind == "conflict":
                yield from self._conflict_events(item)
            elif kind == "country":
                yield from self._country_events(item)
            elif kind == "award":
                yield from self._award_events(item)

    def _award_events(self, item: dict[str, Any]) -> Iterable[Event]:
        start = to_date(item.get("inception"))
        if start is None:
            return
        yield Event(
            external_id=f"{item['id']}:established",
            entity_kind="award",
            entity_external_id=item["id"],
            kind="established",
            label=f"{item['label']} established",
            start_date=start[0],
            precision=start[1],
            start_year=start[2],
            certainty="circa" if start[3] else "exact",
            category="award",
            detail={"enwiki": item.get("enwiki")},
        )

    def _person_events(
        self, item: dict[str, Any], labels: dict[str, dict[str, Any]]
    ) -> Iterable[Event]:
        qid = item["id"]
        occupations = [
            labels[o["id"]]["label"].lower()
            for o in item.get("occupations", ())
            if o["id"] in labels
        ]
        category = occupations[0] if occupations else "person"
        birth = to_date(item.get("birth"))
        death = to_date(item.get("death"))
        if birth is not None:
            start, precision, year, circa = birth
            yield Event(
                external_id=f"{qid}:life",
                entity_kind="person",
                entity_external_id=qid,
                kind="life",
                label=item["label"],
                start_date=start,
                end_date=death[0] if death else None,
                precision=precision,
                start_year=year,
                end_year=death[2] if death else None,
                span=True,
                certainty="circa" if circa or (death and death[3]) else "exact",
                category=category,
                detail={
                    "occupations": occupations[:5] or None,
                    "enwiki": item.get("enwiki"),
                    "julian": item.get("birth", {}).get("julian") or None,
                },
            )
        for rel in item.get("awards", ()):
            when = to_date(rel.get("point"))
            if when is None or rel["id"] not in labels:
                continue
            start, precision, year, circa = when
            yield Event(
                external_id=f"{qid}:award:{rel['id']}:{year}",
                entity_kind="person",
                entity_external_id=qid,
                kind="award",
                label=labels[rel["id"]]["label"],
                start_date=start,
                precision=precision,
                start_year=year,
                certainty="circa" if circa else "exact",
                category=category,
                detail={"award": rel["id"]},
            )
        for rel in item.get("positions", ()):
            start = to_date(rel.get("start"))
            if start is None or rel["id"] not in labels:
                continue
            end = to_date(rel.get("end"))
            yield Event(
                external_id=f"{qid}:position:{rel['id']}:{start[2]}",
                entity_kind="person",
                entity_external_id=qid,
                kind="position",
                label=labels[rel["id"]]["label"],
                start_date=start[0],
                end_date=end[0] if end else None,
                precision=start[1],
                start_year=start[2],
                end_year=end[2] if end else None,
                span=True,
                certainty="circa" if start[3] else "exact",
                category=category,
                detail={"position": rel["id"]},
            )

    def _conflict_events(self, item: dict[str, Any]) -> Iterable[Event]:
        start = (
            to_date(item.get("start"))
            or to_date(item.get("point"))
            or to_date(item.get("inception"))
        )
        if start is None:
            return
        end = to_date(item.get("end"))
        yield Event(
            external_id=f"{item['id']}:conflict",
            entity_kind="conflict",
            entity_external_id=item["id"],
            kind="conflict",
            label=item["label"],
            start_date=start[0],
            end_date=end[0] if end else None,
            precision=start[1],
            start_year=start[2],
            end_year=end[2] if end else None,
            span=end is not None,
            certainty="circa" if start[3] else "exact",
            category="conflict",
            detail={"classes": item.get("classes"), "enwiki": item.get("enwiki")},
        )

    def _country_events(self, item: dict[str, Any]) -> Iterable[Event]:
        start = to_date(item.get("inception"))
        if start is None:
            return
        end = to_date(item.get("dissolved"))
        yield Event(
            external_id=f"{item['id']}:exists",
            entity_kind="country",
            entity_external_id=item["id"],
            kind="exists",
            label=item["label"],
            start_date=start[0],
            end_date=end[0] if end else None,
            precision=start[1],
            start_year=start[2],
            end_year=end[2] if end else None,
            span=True,
            certainty="circa" if start[3] else "exact",
            category="country",
            detail={"enwiki": item.get("enwiki")},
        )

    def participants(self, ctx: SyncContext) -> Iterable[Participant]:
        labels: dict[str, dict[str, Any]] = ctx.options.get("_wd_labels", {})
        selected: dict[str, str] = ctx.options.get("_wd_selected", {})
        for item in self._items(ctx):
            qid = item["id"]
            if item["kind"] == "person":
                for rel in item.get("awards", ()):
                    when = to_date(rel.get("point"))
                    if when is not None and rel["id"] in labels:
                        yield Participant(
                            event_external_id=f"{qid}:award:{rel['id']}:{when[2]}",
                            entity_kind="award",
                            entity_external_id=rel["id"],
                            role="award",
                        )
                for rel in item.get("conflicts", ()):
                    if selected.get(rel["id"]) == "conflict":
                        yield Participant(
                            event_external_id=f"{rel['id']}:conflict",
                            entity_kind="person",
                            entity_external_id=qid,
                            role="combatant",
                        )
            elif item["kind"] == "conflict":
                for rel in item.get("participants", ()):
                    kind = selected.get(rel["id"])
                    if kind in ("country", "person"):
                        yield Participant(
                            event_external_id=f"{qid}:conflict",
                            entity_kind=kind,
                            entity_external_id=rel["id"],
                            role="participant",
                        )

    def identifiers(self, ctx: SyncContext) -> Iterable[Identifier]:
        for item in self._items(ctx):
            for scheme in ID_SCHEMES:
                value = item.get(scheme)
                if not value:
                    continue
                value = str(value)
                if scheme == "bbref":
                    # Wikidata keeps the site's letter directory ("a/aaronha01");
                    # Lahman's bbrefID is the bare "aaronha01".
                    value = value.rsplit("/", 1)[-1]
                yield Identifier(item["kind"], item["id"], scheme, value)
