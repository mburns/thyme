#!/usr/bin/env python3
"""Load timeline events from the registered data sources.

Usage:
    python3 scripts/ingest_events.py list                # sources and sync state
    python3 scripts/ingest_events.py check               # which sources changed
    python3 scripts/ingest_events.py sync [SLUG ...]     # import changed sources
    python3 scripts/ingest_events.py sync --force imdb   # re-import regardless
    python3 scripts/ingest_events.py link                # rebuild entity_links

Sources are skipped when their input files are unchanged since the last
successful sync. The IMDB source reads the already-imported ``titles`` and
``persons`` tables, so run ``import_imdb_sqlite.py`` first. After any source
changes, entity links (the same person across sources) are rebuilt.
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
import time
from pathlib import Path

from ingest import SOURCES, Syncer

DEFAULT_DB = Path("traildepot") / "data" / "main.db"
DEFAULT_DATA_DIR = Path("data")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="show every source and its last sync")
    sub.add_parser("check", help="exit 1 if any source has changed files")
    sub.add_parser("link", help="resolve the same person across sources (entity_links)")
    sub.add_parser("rerank", help="recompute event rank and the level-of-detail table")

    sync = sub.add_parser("sync", help="import sources whose files changed")
    sync.add_argument("slugs", nargs="*", help="sources to sync (default: all)")
    sync.add_argument("--force", action="store_true", help="ignore fingerprints")
    sync.add_argument("--limit", type=int, help="rows per input file (dev only)")
    sync.add_argument(
        "--imdb-min-votes",
        type=int,
        help="only titles with at least this many votes (default 1000)",
    )
    sync.add_argument(
        "--no-imdb-episodes",
        action="store_true",
        help="skip the episodes of included series (on by default)",
    )
    return parser.parse_args(argv)


def fmt_time(ts: int | None) -> str:
    return (
        "never" if ts is None else time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
    )


def cmd_list(syncer: Syncer) -> int:
    print(
        f"{'source':<14}{'files':>6}{'events':>12}  {'last sync':<18}{'status':<10}version"
    )
    for source in SOURCES.values():
        s = syncer.status(source)
        status = s["last_status"] or "-"
        if s["changed"]:
            status += "*"
        print(
            f"{s['slug']:<14}{s['files']:>6}{s['events']:>12,}  "
            f"{fmt_time(s['last_finished']):<18}{status:<10}{s['version'] or ''}"
        )
    print("\n* = input files changed since the last successful sync")
    return 0


def cmd_check(syncer: Syncer) -> int:
    changed = [s.slug for s in SOURCES.values() if syncer.status(s)["changed"]]
    if changed:
        print("changed: " + ", ".join(changed))
        return 1
    print("all sources up to date")
    return 0


def cmd_sync(syncer: Syncer, args: argparse.Namespace) -> int:
    slugs = args.slugs or list(SOURCES)
    unknown = [s for s in slugs if s not in SOURCES]
    if unknown:
        print(f"unknown source(s): {', '.join(unknown)}; known: {', '.join(SOURCES)}")
        return 2

    options: dict[str, object] = {}
    if args.imdb_min_votes is not None:
        options["imdb_min_votes"] = args.imdb_min_votes
    if args.no_imdb_episodes:
        options["imdb_episodes"] = False

    failed = False
    synced = False
    for slug in slugs:
        result = syncer.sync(
            SOURCES[slug], force=args.force, limit=args.limit, options=options
        )
        print(f"{slug:<14}{result.status:<10}{result.message}")
        failed |= result.status == "failed"
        synced |= result.status == "ok"
    if synced:
        cmd_link(syncer)
    return 1 if failed else 0


def cmd_link(syncer: Syncer) -> int:
    links = syncer.link()
    print(
        f"{'links':<14}{'ok':<10}{links.by_identifier:,} by identifier, "
        f"{links.by_wikidata:,} by QID, {links.by_name_dates:,} by name and dates"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    if not args.db_path.exists():
        print(f"database not found: {args.db_path} (start TrailBase once to create it)")
        return 1

    # A running TrailBase keeps readers on the database; a long busy timeout
    # lets the rerank's big write transactions wait them out instead of
    # failing with "database is locked".
    conn = sqlite3.connect(args.db_path, timeout=300)
    try:
        syncer = Syncer(conn, args.data_dir)
        if args.command == "list":
            return cmd_list(syncer)
        if args.command == "check":
            return cmd_check(syncer)
        if args.command == "link":
            return cmd_link(syncer)
        if args.command == "rerank":
            print(f"{'rerank':<14}{'ok':<10}{syncer.rerank()} sources")
            return 0
        return cmd_sync(syncer, args)
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
