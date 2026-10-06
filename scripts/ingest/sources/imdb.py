"""IMDB: derived from the ``titles``/``persons``/``ratings`` tables.

``scripts/import_imdb_sqlite.py`` loads the raw IMDB exports; this adapter
turns them into events, so it must run after that import. The fingerprint
covers both the export files and the imported row counts.
"""

from __future__ import annotations

import hashlib

from ingest.core import Source, SyncContext

DEFAULT_MIN_VOTES = 1000

# titleType -> coarse category
CATEGORY_SQL = """
CASE t.titleType
  WHEN 'movie' THEN 'film' WHEN 'short' THEN 'film'
  WHEN 'video' THEN 'film' WHEN 'tvMovie' THEN 'film'
  WHEN 'tvSeries' THEN 'tv' WHEN 'tvMiniSeries' THEN 'tv'
  WHEN 'tvEpisode' THEN 'tv' WHEN 'tvSpecial' THEN 'tv' WHEN 'tvShort' THEN 'tv'
  WHEN 'videoGame' THEN 'videogame'
  ELSE COALESCE(t.titleType, 'title')
END
"""

PERSON_ENTITIES = """
INSERT OR REPLACE INTO stage_entities
SELECT nconst, 'person', primaryName, primaryProfession, NULL,
       'https://www.imdb.com/name/' || nconst || '/'
FROM persons
WHERE birthYear IS NOT NULL AND primaryName IS NOT NULL
{limit}
"""

PERSON_EVENTS = """
INSERT OR REPLACE INTO stage_events
SELECT nconst || ':life', 'person', nconst, 'life', primaryName,
       printf('%04d', birthYear),
       CASE WHEN deathYear IS NULL THEN NULL ELSE printf('%04d', deathYear) END,
       'year', birthYear, deathYear,
       COALESCE(NULLIF(substr(primaryProfession, 1,
                 instr(primaryProfession || ',', ',') - 1), ''), 'person'),
       NULL, 1, 'exact'
FROM persons
WHERE birthYear IS NOT NULL AND primaryName IS NOT NULL
{limit}
"""

TITLE_ENTITIES = """
INSERT OR REPLACE INTO stage_entities
SELECT t.tconst, 'title', t.primaryTitle, t.titleType, NULL,
       'https://www.imdb.com/title/' || t.tconst || '/'
FROM titles t
JOIN ratings r ON r.title_id = t.id
WHERE r.numVotes >= ? AND t.startYear IS NOT NULL AND t.primaryTitle IS NOT NULL
{limit}
"""

TITLE_EVENTS = f"""
INSERT OR REPLACE INTO stage_events
SELECT t.tconst || ':' || k.kind, 'title', t.tconst, k.kind, t.primaryTitle,
       printf('%04d', t.startYear),
       CASE WHEN k.kind = 'run' AND t.endYear IS NOT NULL
            THEN printf('%04d', t.endYear) END,
       'year', t.startYear,
       CASE WHEN k.kind = 'run' THEN t.endYear END,
       {CATEGORY_SQL},
       json_object('titleType', t.titleType, 'genres', t.genres,
                   'rating', r.averageRating, 'votes', r.numVotes),
       CASE WHEN k.kind = 'run' THEN 1 ELSE 0 END,
       'exact'
FROM titles t
JOIN ratings r ON r.title_id = t.id
JOIN (SELECT CASE WHEN t2.titleType IN ('tvSeries', 'tvMiniSeries')
                  THEN 'run' ELSE 'release' END AS kind, t2.id
      FROM titles t2) k ON k.id = t.id
WHERE r.numVotes >= ? AND t.startYear IS NOT NULL AND t.primaryTitle IS NOT NULL
{{limit}}
"""

# Cast and crew of every staged title become participants of its release or
# run event. CROSS JOIN pins the join order: start from the (small) staged
# titles and walk principals through its (title_id, ordering) index rather
# than scanning all ~90M principals.
TITLE_PARTICIPANTS = """
INSERT OR IGNORE INTO stage_participants
SELECT se.external_id, 'person', p.nconst, pr.category
FROM stage_events se
CROSS JOIN titles t ON t.tconst = se.entity_external_id
CROSS JOIN principals pr ON pr.title_id = t.id
CROSS JOIN persons p ON p.id = pr.person_id
CROSS JOIN stage_entities sn ON sn.kind = 'person' AND sn.external_id = p.nconst
WHERE se.entity_kind = 'title' AND pr.category IS NOT NULL
"""


class ImdbSource(Source):
    slug = "imdb"
    name = "IMDB non-commercial datasets"
    kind = "derived"
    homepage = "https://developer.imdb.com/non-commercial-datasets/"
    license = "IMDB non-commercial licence; attribution required"
    description = (
        "Titles with at least `imdb_min_votes` votes (release or series run) "
        "with their cast and crew as participants, and people with a known "
        "birth year (life span)."
    )
    file_patterns = ("imdb/*.tsv.gz",)

    def fingerprint(self, ctx: SyncContext) -> str:
        # Export files plus the imported row counts, so re-running the IMDB
        # import triggers a re-sync. Changing `imdb_min_votes` does not; use
        # `sync --force imdb` for that.
        counts = ctx.conn.execute(
            "SELECT (SELECT COUNT(*) FROM titles), (SELECT COUNT(*) FROM persons), "
            "(SELECT COUNT(*) FROM ratings)"
        ).fetchone()
        digest = hashlib.sha256(super().fingerprint(ctx).encode())
        digest.update(repr(tuple(counts)).encode())
        return digest.hexdigest()

    def version(self, ctx: SyncContext) -> str | None:
        base = super().version(ctx) or "imported tables"
        return f"{base}, min votes {self._min_votes(ctx)}"

    def load(self, ctx: SyncContext) -> None:
        limit = "" if ctx.limit is None else f"LIMIT {int(ctx.limit)}"
        min_votes = self._min_votes(ctx)
        ctx.conn.execute(PERSON_ENTITIES.format(limit=limit))
        ctx.conn.execute(PERSON_EVENTS.format(limit=limit))
        ctx.conn.execute(TITLE_ENTITIES.format(limit=limit), (min_votes,))
        ctx.conn.execute(TITLE_EVENTS.format(limit=limit), (min_votes,))
        ctx.conn.execute(TITLE_PARTICIPANTS)

    @staticmethod
    def _min_votes(ctx: SyncContext) -> int:
        return int(ctx.options.get("imdb_min_votes", DEFAULT_MIN_VOTES))
