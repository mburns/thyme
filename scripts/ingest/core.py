"""Sync engine shared by every source adapter.

A :class:`Source` describes where its files live and yields :class:`Entity`,
:class:`Event` and :class:`Participant` rows. :class:`Syncer` fingerprints the
files, skips sources that have not changed, stages the rows, upserts them
into ``entities``, ``events`` and ``event_participants``, removes rows the
source no longer produces, refreshes the per-year density table, and records
the run in ``source_syncs``. :meth:`Syncer.link` resolves the same person
seen by several sources to one canonical entity.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import sqlite3
import time
from abc import ABC
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BATCH_SIZE = 20_000
#: Sources whose entities other sources resolve to, best first. QIDs are the
#: cross-source key, so the Wikidata dump wins over the Kaggle extract.
CANONICAL_SOURCES = ("wikidata", "wikidata_age")


def iso_date(
    year: int, month: int | None = None, day: int | None = None
) -> tuple[str, str]:
    """Format a possibly partial date.

    Args:
        year: Calendar year; negative for BCE.
        month: 1-12 or None when unknown.
        day: 1-31 or None when unknown.

    Returns:
        ``(date, precision)`` where ``date`` is ``YYYY``, ``YYYY-MM`` or
        ``YYYY-MM-DD`` and ``precision`` is ``year``, ``month`` or ``day``.
    """
    sign = "-" if year < 0 else ""
    text = f"{sign}{abs(year):04d}"
    if month is None:
        return text, "year"
    text += f"-{month:02d}"
    if day is None:
        return text, "month"
    return f"{text}-{day:02d}", "day"


@dataclass(frozen=True)
class Entity:
    """Something events belong to: a person, a title, a team."""

    external_id: str
    kind: str
    name: str
    description: str | None = None
    wikidata_id: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class Event:
    """An instant or span in time attached to an entity of the same source."""

    external_id: str
    entity_kind: str
    entity_external_id: str
    kind: str
    label: str
    start_date: str
    precision: str
    start_year: int
    category: str
    end_date: str | None = None
    end_year: int | None = None
    detail: dict[str, Any] | None = None
    #: True for a duration (life, career, run); an open end then means ongoing.
    span: bool = False
    #: 'exact', 'circa' or 'unknown'.
    certainty: str = "exact"


@dataclass(frozen=True)
class Participant:
    """An entity that took part in an event owned by another entity."""

    event_external_id: str
    entity_kind: str
    entity_external_id: str
    role: str


@dataclass(frozen=True)
class Identifier:
    """An external identifier of an entity: ('imdb', 'nm0000008').

    Shared identifiers are how entities from different sources are linked
    exactly; Wikidata carries IMDb, Baseball-Reference and Olympedia ids.
    """

    entity_kind: str
    entity_external_id: str
    scheme: str
    value: str


@dataclass
class SyncContext:
    """What an adapter gets while loading: paths, the connection, limits."""

    data_dir: Path
    conn: sqlite3.Connection
    source_id: int
    limit: int | None
    options: dict[str, Any]


@dataclass
class SyncResult:
    slug: str
    status: str
    message: str
    entities_written: int = 0
    events_written: int = 0
    events_deleted: int = 0
    participants_written: int = 0


@dataclass
class LinkResult:
    by_identifier: int
    by_wikidata: int
    by_name_dates: int


class Source(ABC):
    """A dataset that contributes entities and events.

    Subclasses set the class attributes and implement ``entities``, ``events``
    and optionally ``participants``. Sources that build rows from other
    tables (``kind == 'derived'``) may instead override ``load`` and write
    straight into the ``stage_*`` temp tables.
    """

    slug: str
    name: str
    kind: str = "files"
    homepage: str | None = None
    license: str | None = None
    description: str | None = None
    #: Globs relative to the data directory; used for fingerprinting.
    file_patterns: tuple[str, ...] = ()

    def files(self, data_dir: Path) -> list[Path]:
        found: set[Path] = set()
        for pattern in self.file_patterns:
            found.update(p for p in data_dir.glob(pattern) if p.is_file())
        return sorted(found)

    def fingerprint(self, ctx: SyncContext) -> str:
        """Hash of (path, size, mtime) for every input file.

        Cheap enough to run on every invocation, even for multi-gigabyte
        inputs, which content hashing would not be.
        """
        digest = hashlib.sha256()
        for path in self.files(ctx.data_dir):
            stat = path.stat()
            rel = path.relative_to(ctx.data_dir).as_posix()
            digest.update(f"{rel}\0{stat.st_size}\0{stat.st_mtime_ns}\n".encode())
        return digest.hexdigest()

    def version(self, ctx: SyncContext) -> str | None:
        """Human-readable version label, when the source has one."""
        files = self.files(ctx.data_dir)
        if not files:
            return None
        newest = max(f.stat().st_mtime for f in files)
        return time.strftime("files as of %Y-%m-%d", time.gmtime(newest))

    def entities(self, ctx: SyncContext) -> Iterable[Entity]:
        return ()

    def events(self, ctx: SyncContext) -> Iterable[Event]:
        return ()

    def participants(self, ctx: SyncContext) -> Iterable[Participant]:
        return ()

    def identifiers(self, ctx: SyncContext) -> Iterable[Identifier]:
        return ()

    def load(self, ctx: SyncContext) -> None:
        """Write this source's rows into the staging tables."""
        _stage_entities(ctx.conn, self.entities(ctx))
        _stage_events(ctx.conn, self.events(ctx))
        _stage_participants(ctx.conn, self.participants(ctx))
        _stage_identifiers(ctx.conn, self.identifiers(ctx))


def read_csv(path: Path, limit: int | None = None) -> Iterator[dict[str, str]]:
    """Yield rows of a CSV as dicts, stopping after ``limit`` rows if given."""
    # Store descriptions (Steam) run past the 128 KiB default field limit.
    csv.field_size_limit(16 * 1024 * 1024)
    # utf-8-sig drops the byte-order mark some exports put before the header.
    with path.open(encoding="utf-8-sig", newline="") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if limit is not None and i >= limit:
                return
            yield row


def _batched(items: Iterable[Any], size: int) -> Iterator[list[Any]]:
    batch: list[Any] = []
    for item in items:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def _stage_entities(conn: sqlite3.Connection, rows: Iterable[Entity]) -> None:
    for batch in _batched(rows, BATCH_SIZE):
        conn.executemany(
            "INSERT OR REPLACE INTO stage_entities VALUES (?, ?, ?, ?, ?, ?)",
            [
                (e.external_id, e.kind, e.name, e.description, e.wikidata_id, e.url)
                for e in batch
            ],
        )


def _stage_events(conn: sqlite3.Connection, rows: Iterable[Event]) -> None:
    for batch in _batched(rows, BATCH_SIZE):
        conn.executemany(
            "INSERT OR REPLACE INTO stage_events VALUES "
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    e.external_id,
                    e.entity_kind,
                    e.entity_external_id,
                    e.kind,
                    e.label,
                    e.start_date,
                    e.end_date,
                    e.precision,
                    e.start_year,
                    e.end_year,
                    e.category,
                    json.dumps(e.detail, ensure_ascii=False) if e.detail else None,
                    1 if e.span else 0,
                    e.certainty,
                )
                for e in batch
            ],
        )


def _stage_participants(conn: sqlite3.Connection, rows: Iterable[Participant]) -> None:
    for batch in _batched(rows, BATCH_SIZE):
        conn.executemany(
            "INSERT OR IGNORE INTO stage_participants VALUES (?, ?, ?, ?)",
            [
                (p.event_external_id, p.entity_kind, p.entity_external_id, p.role)
                for p in batch
            ],
        )


def _stage_identifiers(conn: sqlite3.Connection, rows: Iterable[Identifier]) -> None:
    for batch in _batched(rows, BATCH_SIZE):
        conn.executemany(
            "INSERT OR IGNORE INTO stage_identifiers VALUES (?, ?, ?, ?)",
            [(i.entity_kind, i.entity_external_id, i.scheme, i.value) for i in batch],
        )


STAGE_SCHEMA = """
CREATE TEMP TABLE stage_identifiers (
  entity_kind TEXT NOT NULL,
  entity_external_id TEXT NOT NULL,
  scheme TEXT NOT NULL,
  value TEXT NOT NULL,
  PRIMARY KEY (entity_kind, entity_external_id, scheme, value)
) WITHOUT ROWID;
CREATE TEMP TABLE stage_entities (
  external_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  description TEXT,
  wikidata_id TEXT,
  url TEXT,
  PRIMARY KEY (kind, external_id)
) WITHOUT ROWID;
CREATE TEMP TABLE stage_events (
  external_id TEXT PRIMARY KEY NOT NULL,
  entity_kind TEXT NOT NULL,
  entity_external_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  label TEXT NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT,
  precision TEXT NOT NULL,
  start_year INTEGER NOT NULL,
  end_year INTEGER,
  category TEXT NOT NULL,
  detail TEXT,
  span INTEGER NOT NULL,
  certainty TEXT NOT NULL
) WITHOUT ROWID;
CREATE TEMP TABLE stage_participants (
  event_external_id TEXT NOT NULL,
  entity_kind TEXT NOT NULL,
  entity_external_id TEXT NOT NULL,
  role TEXT NOT NULL,
  PRIMARY KEY (event_external_id, entity_kind, entity_external_id, role)
) WITHOUT ROWID;
"""

DROP_STAGE = """
DROP TABLE IF EXISTS stage_entities;
DROP TABLE IF EXISTS stage_events;
DROP TABLE IF EXISTS stage_participants;
DROP TABLE IF EXISTS stage_identifiers;
"""

# The upserts walk the staging tables and probe the real tables through their
# UNIQUE indexes. CROSS JOIN pins that order: once ANALYZE statistics exist
# for the big tables, the planner would otherwise scan them and probe the
# stat-less temp tables, turning a 30-second load into hours.
UPSERT_ENTITIES = """
INSERT INTO entities (source_id, external_id, kind, name, description, wikidata_id, url)
SELECT ?, external_id, kind, name, description, wikidata_id, url FROM stage_entities
WHERE true
ON CONFLICT (source_id, kind, external_id) DO UPDATE SET
  name = excluded.name,
  description = excluded.description,
  wikidata_id = excluded.wikidata_id,
  url = excluded.url
"""

UPSERT_EVENTS = """
INSERT INTO events (source_id, entity_id, external_id, kind, label, start_date,
                    end_date, precision, start_year, end_year, category, detail,
                    span, certainty)
SELECT ?, n.id, s.external_id, s.kind, s.label, s.start_date, s.end_date,
       s.precision, s.start_year, s.end_year, s.category, s.detail, s.span,
       s.certainty
FROM stage_events s
CROSS JOIN entities n
  ON n.source_id = ? AND n.kind = s.entity_kind AND n.external_id = s.entity_external_id
WHERE true
ON CONFLICT (source_id, external_id) DO UPDATE SET
  entity_id = excluded.entity_id,
  kind = excluded.kind,
  label = excluded.label,
  start_date = excluded.start_date,
  end_date = excluded.end_date,
  precision = excluded.precision,
  start_year = excluded.start_year,
  end_year = excluded.end_year,
  category = excluded.category,
  detail = excluded.detail,
  span = excluded.span,
  certainty = excluded.certainty
"""

DELETE_STALE_EVENTS = """
DELETE FROM events
WHERE source_id = ?
  AND external_id NOT IN (SELECT external_id FROM stage_events)
"""

# An entity stays if it owns an event or took part in one (an award that was
# received, a country that fought).
DELETE_ORPHAN_ENTITIES = """
DELETE FROM entities
WHERE source_id = ?
  AND id NOT IN (SELECT entity_id FROM events WHERE source_id = ?)
  AND id NOT IN (SELECT entity_id FROM event_participants)
"""

# Participants are fully derived from the source, so they are rebuilt rather
# than diffed.
DELETE_PARTICIPANTS = """
DELETE FROM event_participants
WHERE event_id IN (SELECT id FROM events WHERE source_id = ?)
"""

INSERT_PARTICIPANTS = """
INSERT OR IGNORE INTO event_participants (event_id, entity_id, role)
SELECT e.id, n.id, s.role
FROM stage_participants s
CROSS JOIN events e ON e.source_id = ? AND e.external_id = s.event_external_id
CROSS JOIN entities n
  ON n.source_id = ? AND n.kind = s.entity_kind AND n.external_id = s.entity_external_id
"""

# Identifiers are rebuilt per source like participants.
DELETE_IDENTIFIERS = """
DELETE FROM entity_identifiers
WHERE entity_id IN (SELECT id FROM entities WHERE source_id = ?)
"""

INSERT_IDENTIFIERS = """
INSERT OR IGNORE INTO entity_identifiers (entity_id, scheme, value)
SELECT n.id, s.scheme, s.value
FROM stage_identifiers s
CROSS JOIN entities n
  ON n.source_id = ? AND n.kind = s.entity_kind AND n.external_id = s.entity_external_id
"""

# Two entities from different sources carrying the same (scheme, value)
# are the same thing; the canonical side is the canonical source's.
LINK_BY_IDENTIFIER = """
INSERT OR REPLACE INTO entity_links (entity_id, canonical_id, method, confidence)
SELECT e.id, c.id, 'identifier', 1.0
FROM entity_identifiers ei
JOIN entity_identifiers ci ON ci.scheme = ei.scheme AND ci.value = ei.value
JOIN entities e ON e.id = ei.entity_id
JOIN entities c ON c.id = ci.entity_id AND c.source_id = ?
WHERE e.source_id <> c.source_id
"""

# Importance of an event: audience (votes), cast (participants) and how much
# else is known about its owner, the last capped at 100 events so catalogue
# entities ("Various Artists" with 250k releases) do not outrank everything.
# log10 needs SQLite's math functions, which Python's module has; the
# fallback keeps the ingest working without them.
# The two counts are aggregated once into keyed temp tables rather than
# re-counted per event: a correlated count per row took 40 minutes over
# 6M events, this takes a few.
RANK_PREPARE = """
DROP TABLE IF EXISTS rank_credits;
DROP TABLE IF EXISTS rank_owner;
CREATE TEMP TABLE rank_credits (event_id INTEGER PRIMARY KEY, n INTEGER NOT NULL) WITHOUT ROWID;
CREATE TEMP TABLE rank_owner (entity_id INTEGER PRIMARY KEY, n INTEGER NOT NULL) WITHOUT ROWID;
"""
RANK_CREDITS = """
INSERT INTO rank_credits (event_id, n)
SELECT p.event_id, count(*) FROM events e
CROSS JOIN event_participants p ON p.event_id = e.id
WHERE e.source_id = ? GROUP BY p.event_id
"""
RANK_OWNER = """
INSERT INTO rank_owner (entity_id, n)
SELECT entity_id, count(*) FROM events WHERE source_id = ? GROUP BY entity_id
"""
UPDATE_RANK = """
UPDATE events SET rank =
    coalesce(log10(1 + coalesce(json_extract(detail, '$.votes'), 0)), 0)
  + coalesce((SELECT log10(1 + n) FROM rank_credits WHERE event_id = events.id), 0)
  + coalesce((SELECT min(log10(n), 2.0) FROM rank_owner WHERE entity_id = events.entity_id), 0)
WHERE source_id = ?
"""
UPDATE_RANK_FALLBACK = """
UPDATE events SET rank = coalesce(json_extract(detail, '$.votes'), 0)
WHERE source_id = ?
"""
RANK_CLEANUP = "DROP TABLE IF EXISTS rank_credits; DROP TABLE IF EXISTS rank_owner;"

LOD_SIZES = (1, 10, 100)
SPAN_LOD_SIZES = (10, 100)
LOD_KEEP = 20
#: Open-ended spans (still alive, still running) are treated as ending here.
LOD_OPEN_END = 2030

# Top LOD_KEEP events per (bucket, category) for one bucket size and source,
# plus the same across all categories under category '*'. The bucket
# expression floors correctly for negative years.
INSERT_LOD = """
INSERT INTO event_lod (bucket_size, bucket, category, source_id, pos, event_id, rank)
SELECT ?, bucket, category, source_id, pos, id, rank FROM (
  SELECT start_year - (((start_year % ?) + ?) % ?) AS bucket, category, source_id, id, rank,
         row_number() OVER (
           PARTITION BY start_year - (((start_year % ?) + ?) % ?), category
           ORDER BY rank DESC, id) AS pos
  FROM events WHERE source_id = ?)
WHERE pos <= ?
"""
INSERT_LOD_ALL = """
INSERT INTO event_lod (bucket_size, bucket, category, source_id, pos, event_id, rank)
SELECT ?, bucket, '*', source_id, pos, id, rank FROM (
  SELECT start_year - (((start_year % ?) + ?) % ?) AS bucket, source_id, id, rank,
         row_number() OVER (
           PARTITION BY start_year - (((start_year % ?) + ?) % ?)
           ORDER BY rank DESC, id) AS pos
  FROM events WHERE source_id = ?)
WHERE pos <= ?
"""

# Every span contributes to each bucket it overlaps (a 1934-2021 life to the
# 1930s through the 2020s); the recursive CTE does the expansion. Rows are
# ranked per (bucket, category) and per bucket across categories ('*').
INSERT_SPAN_LOD = """
WITH RECURSIVE b(event_id, bucket, last, category, source_id, rank) AS (
  SELECT id,
         start_year - (((start_year % ?) + ?) % ?),
         min(coalesce(end_year, ?), ?) - (((min(coalesce(end_year, ?), ?) % ?) + ?) % ?),
         category, source_id, rank
  FROM events WHERE span = 1 AND source_id = ?
  UNION ALL
  SELECT event_id, bucket + ?, last, category, source_id, rank FROM b WHERE bucket + ? <= last
)
INSERT INTO span_lod (bucket_size, bucket, category, source_id, pos, event_id, rank)
SELECT ?, bucket, category, source_id, pos, event_id, rank FROM (
  SELECT event_id, bucket, category, source_id, rank,
         row_number() OVER (PARTITION BY bucket, category ORDER BY rank DESC, event_id) AS pos
  FROM b)
WHERE pos <= ?
"""
INSERT_SPAN_LOD_ALL = """
WITH RECURSIVE b(event_id, bucket, last, source_id, rank) AS (
  SELECT id,
         start_year - (((start_year % ?) + ?) % ?),
         min(coalesce(end_year, ?), ?) - (((min(coalesce(end_year, ?), ?) % ?) + ?) % ?),
         source_id, rank
  FROM events WHERE span = 1 AND source_id = ?
  UNION ALL
  SELECT event_id, bucket + ?, last, source_id, rank FROM b WHERE bucket + ? <= last
)
INSERT INTO span_lod (bucket_size, bucket, category, source_id, pos, event_id, rank)
SELECT ?, bucket, '*', source_id, pos, event_id, rank FROM (
  SELECT event_id, bucket, source_id, rank,
         row_number() OVER (PARTITION BY bucket ORDER BY rank DESC, event_id) AS pos
  FROM b)
WHERE pos <= ?
"""

INSERT_DENSITY = """
INSERT INTO event_density (source_id, category, year, count)
SELECT source_id, category, start_year, count(*)
FROM events WHERE source_id = ?
GROUP BY source_id, category, start_year
"""

# Entities from any source that carry the same QID as a canonical-source
# entity are that entity.
LINK_BY_WIKIDATA = """
INSERT OR REPLACE INTO entity_links (entity_id, canonical_id, method, confidence)
SELECT e.id, c.id, 'wikidata_id', 1.0
FROM entities e
JOIN entities c ON c.wikidata_id = e.wikidata_id AND c.source_id = ?
WHERE e.wikidata_id IS NOT NULL AND e.source_id <> c.source_id
"""

# People with the same name, birth year and death year, when that
# combination is unique within both sources, are the same person.
LINK_BY_NAME_DATES = """
WITH lives AS (
  SELECT entities.id AS entity_id, entities.source_id,
         lower(trim(entities.name)) AS name,
         events.start_year AS born, events.end_year AS died
  FROM events
  JOIN entities ON entities.id = events.entity_id
  WHERE events.kind = 'life' AND entities.kind = 'person'
),
unique_keys AS (
  SELECT source_id, name, born, died, min(entity_id) AS entity_id
  FROM lives
  GROUP BY source_id, name, born, died
  HAVING count(*) = 1
),
canon AS (SELECT * FROM unique_keys WHERE source_id = ?)
INSERT OR IGNORE INTO entity_links (entity_id, canonical_id, method, confidence)
SELECT other.entity_id, canon.entity_id, 'name_dates',
       CASE WHEN canon.died IS NOT NULL THEN 0.9 ELSE 0.7 END
FROM unique_keys other
JOIN canon ON canon.name = other.name
          AND canon.born = other.born
          AND canon.died IS other.died
WHERE other.source_id <> canon.source_id
"""


class Syncer:
    """Runs sources against one database."""

    def __init__(self, conn: sqlite3.Connection, data_dir: Path) -> None:
        self.conn = conn
        self.data_dir = data_dir
        conn.execute("PRAGMA foreign_keys = ON")
        # Bulk-load settings: WAL keeps TrailBase readable during a sync,
        # NORMAL sync is safe under WAL, and a big cache plus in-memory temp
        # tables keep the staging and upsert passes off disk.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        conn.execute("PRAGMA cache_size = -262144")
        # A sync that was killed mid-way left its row as 'running'; its data
        # was rolled back with the transaction.
        conn.execute(
            "UPDATE source_syncs SET status = 'failed', finished = ?, "
            "message = 'interrupted' WHERE status = 'running'",
            (int(time.time()),),
        )
        conn.commit()

    def register(self, source: Source) -> int:
        """Ensure the source row exists and return its id."""
        self.conn.execute(
            """
            INSERT INTO sources (slug, name, kind, homepage, license, description)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (slug) DO UPDATE SET
              name = excluded.name, kind = excluded.kind,
              homepage = excluded.homepage, license = excluded.license,
              description = excluded.description
            """,
            (
                source.slug,
                source.name,
                source.kind,
                source.homepage,
                source.license,
                source.description,
            ),
        )
        self.conn.commit()
        row = self.conn.execute(
            "SELECT id FROM sources WHERE slug = ?", (source.slug,)
        ).fetchone()
        return int(row[0])

    def last_ok_fingerprint(self, source_id: int) -> str | None:
        row = self.conn.execute(
            """
            SELECT fingerprint FROM source_syncs
            WHERE source_id = ? AND status = 'ok'
            ORDER BY id DESC LIMIT 1
            """,
            (source_id,),
        ).fetchone()
        return None if row is None else str(row[0])

    def status(self, source: Source) -> dict[str, Any]:
        """Describe a source's last sync and whether its files changed."""
        source_id = self.register(source)
        ctx = SyncContext(self.data_dir, self.conn, source_id, None, {})
        current = source.fingerprint(ctx)
        last = self.conn.execute(
            """
            SELECT status, finished, version, events_written, message
            FROM source_syncs WHERE source_id = ?
            ORDER BY started DESC LIMIT 1
            """,
            (source_id,),
        ).fetchone()
        events = self.conn.execute(
            "SELECT COUNT(*) FROM events WHERE source_id = ?", (source_id,)
        ).fetchone()[0]
        return {
            "slug": source.slug,
            "name": source.name,
            "files": len(source.files(self.data_dir)),
            "events": int(events),
            "last_status": None if last is None else last[0],
            "last_finished": None if last is None else last[1],
            "version": None if last is None else last[2],
            "changed": current != self.last_ok_fingerprint(source_id),
        }

    def sync(
        self,
        source: Source,
        *,
        force: bool = False,
        limit: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> SyncResult:
        """Import a source if its files changed since the last successful run.

        Args:
            source: The adapter to run.
            force: Re-import even when the fingerprint is unchanged.
            limit: Cap rows read per input file (for development and tests).
            options: Adapter-specific settings, e.g. ``imdb_min_votes``.

        Returns:
            What happened, including row counts for a completed sync.
        """
        source_id = self.register(source)
        ctx = SyncContext(self.data_dir, self.conn, source_id, limit, options or {})

        if source.kind == "files" and not source.files(self.data_dir):
            return SyncResult(source.slug, "missing", "no input files found")

        fingerprint = source.fingerprint(ctx)
        if not force and fingerprint == self.last_ok_fingerprint(source_id):
            return SyncResult(
                source.slug, "unchanged", "files unchanged since last sync"
            )

        started = int(time.time())
        cur = self.conn.execute(
            """
            INSERT INTO source_syncs (source_id, started, status, fingerprint, version)
            VALUES (?, ?, 'running', ?, ?)
            """,
            (source_id, started, fingerprint, source.version(ctx)),
        )
        sync_id = cur.lastrowid
        self.conn.commit()

        try:
            result = self._run(source, ctx)
        except Exception as e:  # noqa: BLE001 - any failure must be recorded
            self.conn.rollback()
            self.conn.execute(
                """
                UPDATE source_syncs SET status = 'failed', finished = ?, message = ?
                WHERE id = ?
                """,
                (int(time.time()), f"{type(e).__name__}: {e}", sync_id),
            )
            self.conn.commit()
            logger.exception("sync of %s failed", source.slug)
            return SyncResult(source.slug, "failed", f"{type(e).__name__}: {e}")

        self._record_files(source, source_id)
        self.conn.execute(
            """
            UPDATE source_syncs
            SET status = 'ok', finished = ?, entities_written = ?,
                events_written = ?, events_deleted = ?, message = ?
            WHERE id = ?
            """,
            (
                int(time.time()),
                result.entities_written,
                result.events_written,
                result.events_deleted,
                result.message,
                sync_id,
            ),
        )
        self.conn.commit()
        return result

    def _run(self, source: Source, ctx: SyncContext) -> SyncResult:
        conn = self.conn
        conn.executescript(DROP_STAGE)
        conn.executescript(STAGE_SCHEMA)

        t0 = time.time()
        source.load(ctx)
        staged_entities = conn.execute(
            "SELECT COUNT(*) FROM stage_entities"
        ).fetchone()[0]
        staged_events = conn.execute("SELECT COUNT(*) FROM stage_events").fetchone()[0]
        logger.info(
            "%s: staged %s entities and %s events in %.1fs",
            source.slug,
            f"{staged_entities:,}",
            f"{staged_events:,}",
            time.time() - t0,
        )

        # The staging inserts above opened an implicit transaction; the upserts
        # join it so a failure anywhere rolls back everything.
        sid = ctx.source_id
        entities_written = conn.execute(UPSERT_ENTITIES, (sid,)).rowcount
        events_written = conn.execute(UPSERT_EVENTS, (sid, sid)).rowcount
        events_deleted = conn.execute(DELETE_STALE_EVENTS, (sid,)).rowcount
        conn.execute(DELETE_PARTICIPANTS, (sid,))
        participants_written = conn.execute(INSERT_PARTICIPANTS, (sid, sid)).rowcount
        conn.execute(DELETE_ORPHAN_ENTITIES, (sid, sid))
        conn.execute(DELETE_IDENTIFIERS, (sid,))
        conn.execute(INSERT_IDENTIFIERS, (sid,))
        conn.execute("DELETE FROM event_density WHERE source_id = ?", (sid,))
        conn.execute(INSERT_DENSITY, (sid,))
        self._rank_and_lod(sid)
        # entities_fts follows entities through triggers (see the
        # entities_fts_triggers migration), so no rebuild is needed here.
        conn.commit()
        conn.executescript(DROP_STAGE)
        # Refresh planner statistics (STAT4 histograms) for the tables that
        # just changed, then let SQLite decide whether anything else is stale.
        conn.executescript(
            "ANALYZE events; ANALYZE entities; ANALYZE event_participants; "
            "PRAGMA optimize;"
        )

        unresolved = staged_events - events_written
        message = f"{events_written:,} events upserted, {events_deleted:,} removed"
        if participants_written:
            message += f", {participants_written:,} participants"
        if unresolved > 0:
            message += f", {unresolved:,} skipped (unknown entity)"
        logger.info("%s: %s in %.1fs", source.slug, message, time.time() - t0)
        return SyncResult(
            source.slug,
            "ok",
            message,
            entities_written,
            events_written,
            events_deleted,
            participants_written,
        )

    def _rank_and_lod(self, source_id: int) -> None:
        """Recompute `events.rank` and the level-of-detail table for a source."""
        self.conn.executescript(RANK_PREPARE)
        self.conn.execute(RANK_CREDITS, (source_id,))
        self.conn.execute(RANK_OWNER, (source_id,))
        try:
            self.conn.execute(UPDATE_RANK, (source_id,))
        except sqlite3.OperationalError as e:
            if "no such function" not in str(e):
                raise
            logger.warning("SQLite math functions unavailable; using vote-count rank")
            self.conn.execute(UPDATE_RANK_FALLBACK, (source_id,))
        self.conn.executescript(RANK_CLEANUP)
        self.conn.execute("DELETE FROM event_lod WHERE source_id = ?", (source_id,))
        for size in LOD_SIZES:
            args = (size, size, size, size, size, size, size, source_id, LOD_KEEP)
            self.conn.execute(INSERT_LOD, args)
            self.conn.execute(INSERT_LOD_ALL, args)
        self.conn.execute("DELETE FROM span_lod WHERE source_id = ?", (source_id,))
        end = LOD_OPEN_END
        for size in SPAN_LOD_SIZES:
            args = (
                *(size, size, size),  # start bucket
                *(end, end, end, end, size, size, size),  # last bucket
                source_id,
                *(size, size),  # recursion step and bound
                *(size, LOD_KEEP),
            )
            self.conn.execute(INSERT_SPAN_LOD, args)
            self.conn.execute(INSERT_SPAN_LOD_ALL, args)

    def rerank(self) -> int:
        """Recompute rank and LOD for every source (after the scale migration)."""
        rows = self.conn.execute("SELECT id FROM sources").fetchall()
        for (source_id,) in rows:
            self._rank_and_lod(int(source_id))
        self.conn.commit()
        return len(rows)

    def link(self) -> LinkResult:
        """Rebuild ``entity_links``: resolve duplicates to canonical entities.

        The canonical source is Wikidata (QIDs are the cross-source key): the
        dump when loaded, else the Kaggle age extract. Shared external
        identifiers (IMDb, Baseball-Reference) and shared QIDs link with
        certainty; otherwise a person links when name, birth year and death
        year match and that combination is unique in both sources, so common
        names never link by accident.
        """
        canonical: int | None = None
        for slug in CANONICAL_SOURCES:
            row = self.conn.execute(
                "SELECT id FROM sources WHERE slug = ? "
                "AND EXISTS (SELECT 1 FROM entities WHERE source_id = sources.id)",
                (slug,),
            ).fetchone()
            if row is not None:
                canonical = int(row[0])
                break
        if canonical is None:
            return LinkResult(0, 0, 0)
        self.conn.execute("DELETE FROM entity_links")
        # cursor.rowcount is -1 for statements that start with WITH, so ask
        # SQLite directly.
        self.conn.execute(LINK_BY_IDENTIFIER, (canonical,))
        by_identifier = int(self.conn.execute("SELECT changes()").fetchone()[0])
        self.conn.execute(LINK_BY_WIKIDATA, (canonical,))
        by_wikidata = int(self.conn.execute("SELECT changes()").fetchone()[0])
        self.conn.execute(LINK_BY_NAME_DATES, (canonical,))
        by_name = int(self.conn.execute("SELECT changes()").fetchone()[0])
        self.conn.commit()
        logger.info(
            "linked %s entities by identifier, %s by QID and %s by name and dates",
            f"{by_identifier:,}",
            f"{by_wikidata:,}",
            f"{by_name:,}",
        )
        return LinkResult(by_identifier, by_wikidata, by_name)

    def _record_files(self, source: Source, source_id: int) -> None:
        self.conn.execute("DELETE FROM source_files WHERE source_id = ?", (source_id,))
        self.conn.executemany(
            "INSERT INTO source_files (source_id, path, size, modified) VALUES (?, ?, ?, ?)",
            [
                (
                    source_id,
                    p.relative_to(self.data_dir).as_posix(),
                    p.stat().st_size,
                    int(p.stat().st_mtime),
                )
                for p in source.files(self.data_dir)
            ],
        )
