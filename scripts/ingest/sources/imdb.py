"""IMDB: derived from the imported ``titles``/``persons``/``ratings``/
``episodes``/``principals``/``crew`` tables.

``scripts/import_imdb_sqlite.py`` loads the raw IMDB exports; this adapter
turns them into events, so it must run after that import. The fingerprint
covers both the export files and the imported row counts.

What it yields, for titles with at least ``imdb_min_votes`` votes:

* a ``release`` instant per film, or a ``run`` span per series
* an ``episode`` instant per episode of an included series, on the
  series' lane (``imdb_episodes``, on by default)
* participants: every cast and crew member of those titles and episodes,
  in their credited role; people are entities even without a birth year
* a ``life`` span per person with a known birth year
* IMDb ids as identifiers, the exact link to Wikidata's P345

Everything is plain SQL over the imported tables. CROSS JOIN pins the join
order so each query walks the (small) staged titles and probes the big
tables through their indexes, never the other way round.
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

PERSON_ENTITY_COLUMNS = """
nconst, 'person', primaryName, primaryProfession, NULL,
'https://www.imdb.com/name/' || nconst || '/'
"""

PERSON_ENTITIES = f"""
INSERT OR REPLACE INTO stage_entities
SELECT {PERSON_ENTITY_COLUMNS}
FROM persons
WHERE birthYear IS NOT NULL AND primaryName IS NOT NULL
{{limit}}
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
  AND t.titleType <> 'tvEpisode'
{limit}
"""

# Episodes are never stand-alone titles: they sit on their series' lane.
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
  AND t.titleType <> 'tvEpisode'
{{limit}}
"""

# Every episode of a staged series, as an instant on the series' lane.
EPISODE_EVENTS = """
INSERT OR REPLACE INTO stage_events
SELECT ep.tconst || ':episode', 'title', se.entity_external_id, 'episode',
       ep.primaryTitle,
       printf('%04d', ep.startYear), NULL, 'year', ep.startYear, NULL, 'tv',
       json_object('tconst', ep.tconst, 'season', e.seasonNumber,
                   'episode', e.episodeNumber,
                   'rating', r.averageRating, 'votes', r.numVotes),
       0, 'exact'
FROM stage_events se
CROSS JOIN titles s ON s.tconst = se.entity_external_id
CROSS JOIN episodes e ON e.parent_title_id = s.id
CROSS JOIN titles ep ON ep.id = e.title_id
LEFT JOIN ratings r ON r.title_id = ep.id
WHERE se.kind = 'run' AND ep.startYear IS NOT NULL AND ep.primaryTitle IS NOT NULL
"""

# The tconst a staged event is credited under: the title itself for a
# release or run, the episode for an episode.
EVENT_TITLE_SQL = """
CASE WHEN se.kind = 'episode' THEN se.detail ->> 'tconst' ELSE se.entity_external_id END
"""

# People credited on any staged title or episode become entities even
# without a birth year; they survive as participants.
CAST_ENTITIES = f"""
INSERT OR IGNORE INTO stage_entities
SELECT {PERSON_ENTITY_COLUMNS}
FROM (
  SELECT DISTINCT pr.person_id AS person_id
  FROM stage_events se
  CROSS JOIN titles t ON t.tconst = {EVENT_TITLE_SQL}
  CROSS JOIN principals pr ON pr.title_id = t.id
  WHERE se.entity_kind = 'title'
  UNION
  SELECT DISTINCT c.person_id
  FROM stage_events se
  CROSS JOIN titles t ON t.tconst = {EVENT_TITLE_SQL}
  CROSS JOIN crew c ON c.title_id = t.id
  WHERE se.entity_kind = 'title'
) credited
CROSS JOIN persons ON persons.id = credited.person_id
WHERE persons.primaryName IS NOT NULL
"""

# Cast and crew of every staged title and episode, in their credited role.
PARTICIPANTS = f"""
INSERT OR IGNORE INTO stage_participants
SELECT se.external_id, 'person', p.nconst, pr.category
FROM stage_events se
CROSS JOIN titles t ON t.tconst = {EVENT_TITLE_SQL}
CROSS JOIN principals pr ON pr.title_id = t.id
CROSS JOIN persons p ON p.id = pr.person_id
WHERE se.entity_kind = 'title' AND pr.category IS NOT NULL
  AND p.primaryName IS NOT NULL
"""

CREW_PARTICIPANTS = f"""
INSERT OR IGNORE INTO stage_participants
SELECT se.external_id, 'person', p.nconst, c.role
FROM stage_events se
CROSS JOIN titles t ON t.tconst = {EVENT_TITLE_SQL}
CROSS JOIN crew c ON c.title_id = t.id
CROSS JOIN persons p ON p.id = c.person_id
WHERE se.entity_kind = 'title' AND c.role <> '' AND p.primaryName IS NOT NULL
"""

# The IMDB ids themselves are the identifiers Wikidata carries as P345.
IDENTIFIERS = """
INSERT OR IGNORE INTO stage_identifiers
SELECT kind, external_id, 'imdb', external_id FROM stage_entities
"""


class ImdbSource(Source):
    slug = "imdb"
    name = "IMDB non-commercial datasets"
    kind = "derived"
    homepage = "https://developer.imdb.com/non-commercial-datasets/"
    license = "IMDB non-commercial licence; attribution required"
    description = (
        "Titles with at least `imdb_min_votes` votes (release or series run), "
        "their episodes, their full cast and crew as participants, and people "
        "with a known birth year (life span)."
    )
    file_patterns = ("imdb/*.tsv.gz",)

    def fingerprint(self, ctx: SyncContext) -> str:
        # Export files plus the imported row counts, so re-running the IMDB
        # import triggers a re-sync. Changing the options does not; use
        # `sync --force imdb` for that.
        counts = ctx.conn.execute(
            "SELECT (SELECT COUNT(*) FROM titles), (SELECT COUNT(*) FROM persons), "
            "(SELECT COUNT(*) FROM ratings), (SELECT COUNT(*) FROM episodes), "
            "(SELECT COUNT(*) FROM principals)"
        ).fetchone()
        digest = hashlib.sha256(super().fingerprint(ctx).encode())
        digest.update(repr(tuple(counts)).encode())
        return digest.hexdigest()

    def version(self, ctx: SyncContext) -> str | None:
        base = super().version(ctx) or "imported tables"
        episodes = "with episodes" if self._episodes(ctx) else "without episodes"
        return f"{base}, min votes {self._min_votes(ctx)}, {episodes}"

    def load(self, ctx: SyncContext) -> None:
        limit = "" if ctx.limit is None else f"LIMIT {int(ctx.limit)}"
        min_votes = self._min_votes(ctx)
        conn = ctx.conn
        conn.execute(PERSON_ENTITIES.format(limit=limit))
        conn.execute(PERSON_EVENTS.format(limit=limit))
        conn.execute(TITLE_ENTITIES.format(limit=limit), (min_votes,))
        conn.execute(TITLE_EVENTS.format(limit=limit), (min_votes,))
        if self._episodes(ctx):
            conn.execute(EPISODE_EVENTS)
        conn.execute(CAST_ENTITIES)
        conn.execute(PARTICIPANTS)
        conn.execute(CREW_PARTICIPANTS)
        conn.execute(IDENTIFIERS)

    @staticmethod
    def _min_votes(ctx: SyncContext) -> int:
        return int(ctx.options.get("imdb_min_votes", DEFAULT_MIN_VOTES))

    @staticmethod
    def _episodes(ctx: SyncContext) -> bool:
        return bool(ctx.options.get("imdb_episodes", True))
