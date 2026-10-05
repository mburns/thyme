#!/usr/bin/env python3
"""Smoke test for the FTS5 search index.

Checks that the ``titles_fts`` and ``persons_fts`` tables exist, are in sync
with their content tables, and answer the same kind of queries the ``/search``
handler in ``traildepot/scripts/search.ts`` issues.

Usage:
    python3 scripts/test_search.py [path/to/main.db]
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path("traildepot") / "data" / "main.db"

# (fts table, content table, display column, bm25 weights matching search.ts)
INDEXES: list[tuple[str, str, str, str]] = [
    ("titles_fts", "titles", "primaryTitle", "10.0, 5.0, 1.0, 1.0"),
    ("persons_fts", "persons", "primaryName", "10.0, 1.0"),
]

SAMPLE_QUERIES: list[str] = ['"god"*', '"tom" "han"*', '"drama"', '"1999"']


def check_index(conn: sqlite3.Connection, fts: str, content: str) -> bool:
    """Verify an FTS table exists and has one row per content-table row."""
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (fts,)
    ).fetchone()
    if exists is None:
        print(f"  {fts}: missing (run the TrailBase server to apply migrations)")
        return False

    indexed = conn.execute(f"SELECT COUNT(*) FROM {fts}").fetchone()[0]
    expected = conn.execute(f"SELECT COUNT(*) FROM {content}").fetchone()[0]
    status = "ok" if indexed == expected else "OUT OF SYNC"
    print(f"  {fts}: {indexed:,} indexed / {expected:,} in {content} ({status})")
    return indexed == expected


def run_sample_queries(conn: sqlite3.Connection) -> None:
    """Print the top hits for a few representative MATCH expressions."""
    for match in SAMPLE_QUERIES:
        print(f"\n  MATCH {match}")
        for fts, content, label, weights in INDEXES:
            rows = conn.execute(
                f"""
                SELECT c.{label}, c.id
                  FROM {fts}
                  JOIN {content} c ON c.id = {fts}.rowid
                 WHERE {fts} MATCH ?
                 ORDER BY bm25({fts}, {weights})
                 LIMIT 3
                """,
                (match,),
            ).fetchall()
            total = conn.execute(
                f"SELECT COUNT(*) FROM {fts} WHERE {fts} MATCH ?", (match,)
            ).fetchone()[0]
            print(f"    {content}: {total:,} hits")
            for name, row_id in rows:
                print(f"      - {name} (id {row_id})")


def main() -> int:
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        print("Start the TrailBase server once and run the import first.")
        return 1

    print(f"Checking FTS5 indexes in {db_path}")
    with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
        try:
            in_sync = all(
                check_index(conn, fts, content) for fts, content, _, _ in INDEXES
            )
            run_sample_queries(conn)
        except sqlite3.Error as e:
            print(f"SQLite error: {e}")
            return 1

    if not in_sync:
        print("\nIndexes are out of sync. Rebuild with:")
        for fts, _, _, _ in INDEXES:
            print(f"  INSERT INTO {fts}({fts}) VALUES ('rebuild');")
        return 1

    print("\nFTS5 search index looks healthy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
