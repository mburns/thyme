"""Sync engine shared by every source adapter.

A :class:`Source` describes where its files live and yields :class:`Entity`
and :class:`Event` rows. :class:`Syncer` fingerprints the files, skips sources
that have not changed, stages the rows, upserts them into ``entities`` and
``events``, removes rows the source no longer produces, and records the run
in ``source_syncs``.
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


class Source(ABC):
    """A dataset that contributes entities and events.

    Subclasses set the class attributes and implement ``entities`` and
    ``events``. Sources that build rows from other tables (``kind ==
    'derived'``) may instead override ``load`` and write straight into the
    ``stage_entities`` and ``stage_events`` temp tables.
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

    def load(self, ctx: SyncContext) -> None:
        """Write this source's rows into the staging tables."""
        _stage_entities(ctx.conn, self.entities(ctx))
        _stage_events(ctx.conn, self.events(ctx))


def read_csv(path: Path, limit: int | None = None) -> Iterator[dict[str, str]]:
    """Yield rows of a CSV as dicts, stopping after ``limit`` rows if given."""
    with path.open(encoding="utf-8", newline="") as f:
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
            "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                )
                for e in batch
            ],
        )


STAGE_SCHEMA = """
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
  span INTEGER NOT NULL
) WITHOUT ROWID;
"""

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
                    end_date, precision, start_year, end_year, category, detail, span)
SELECT ?, n.id, s.external_id, s.kind, s.label, s.start_date, s.end_date,
       s.precision, s.start_year, s.end_year, s.category, s.detail, s.span
FROM stage_events s
JOIN entities n
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
  span = excluded.span
"""

DELETE_STALE_EVENTS = """
DELETE FROM events
WHERE source_id = ?
  AND external_id NOT IN (SELECT external_id FROM stage_events)
"""

DELETE_ORPHAN_ENTITIES = """
DELETE FROM entities
WHERE source_id = ?
  AND id NOT IN (SELECT entity_id FROM events WHERE source_id = ?)
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
        conn.executescript(
            "DROP TABLE IF EXISTS stage_entities; DROP TABLE IF EXISTS stage_events;"
        )
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
        entities_written = conn.execute(UPSERT_ENTITIES, (ctx.source_id,)).rowcount
        events_written = conn.execute(
            UPSERT_EVENTS, (ctx.source_id, ctx.source_id)
        ).rowcount
        events_deleted = conn.execute(DELETE_STALE_EVENTS, (ctx.source_id,)).rowcount
        conn.execute(DELETE_ORPHAN_ENTITIES, (ctx.source_id, ctx.source_id))
        conn.execute("INSERT INTO entities_fts(entities_fts) VALUES ('rebuild')")
        conn.commit()
        conn.executescript("DROP TABLE stage_entities; DROP TABLE stage_events;")
        # Refresh planner statistics (STAT4 histograms) for the tables that
        # just changed, then let SQLite decide whether anything else is stale.
        conn.executescript("ANALYZE events; ANALYZE entities; PRAGMA optimize;")

        unresolved = staged_events - events_written
        message = f"{events_written:,} events upserted, {events_deleted:,} removed"
        if unresolved > 0:
            message += f", {unresolved:,} skipped (unknown entity)"
        logger.info("%s: %s in %.1fs", source.slug, message, time.time() - t0)
        return SyncResult(
            source.slug, "ok", message, entities_written, events_written, events_deleted
        )

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
