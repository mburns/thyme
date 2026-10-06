-- Unified timeline model.
--
-- Every dataset (IMDB, Lahman baseball, Olympics, Wikidata people, ...) is a
-- `source`. A source contributes `entities` (a person, a title, a team) and
-- `events` that belong to them. An event is either an instant (a release, an
-- award) or a span (a life, a career, a TV run), with an explicit date
-- precision so year-only dates are never mistaken for January 1st.
--
-- `source_files` and `source_syncs` track what was imported from where, so a
-- source can be re-synced when its files change and stale rows removed.

CREATE TABLE sources (
  id          INTEGER PRIMARY KEY,
  slug        TEXT UNIQUE NOT NULL,
  name        TEXT NOT NULL,
  -- 'files': read from files under data/; 'derived': built from other tables
  kind        TEXT NOT NULL CHECK (kind IN ('files', 'derived')),
  homepage    TEXT,
  license     TEXT,
  description TEXT,
  created     INTEGER DEFAULT (UNIXEPOCH()) NOT NULL
) STRICT;

-- Fingerprint of each input file as of the last successful sync.
CREATE TABLE source_files (
  id        INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  path      TEXT NOT NULL,
  size      INTEGER NOT NULL,
  modified  INTEGER NOT NULL,
  UNIQUE (source_id, path)
) STRICT;

-- One row per sync attempt; the latest 'ok' row is the current version.
CREATE TABLE source_syncs (
  id               INTEGER PRIMARY KEY,
  source_id        INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  started          INTEGER NOT NULL,
  finished         INTEGER,
  status           TEXT NOT NULL CHECK (status IN ('running', 'ok', 'failed')),
  fingerprint      TEXT NOT NULL,
  version          TEXT,
  entities_written INTEGER,
  events_written   INTEGER,
  events_deleted   INTEGER,
  message          TEXT
) STRICT;

CREATE TABLE entities (
  id          INTEGER PRIMARY KEY,
  source_id   INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  -- The source's own identifier: nconst, playerID, Wikidata QID, ...
  external_id TEXT NOT NULL,
  -- 'person', 'title', 'team', 'games', ...
  kind        TEXT NOT NULL,
  name        TEXT NOT NULL,
  description TEXT,
  -- Wikidata QID when known: the crosswalk between sources.
  wikidata_id TEXT,
  url         TEXT,
  UNIQUE (source_id, kind, external_id)
) STRICT;

CREATE TABLE events (
  id          INTEGER PRIMARY KEY,
  source_id   INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  entity_id   INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  -- Stable per-source key so re-syncs update in place.
  external_id TEXT NOT NULL,
  -- 'life', 'career', 'run', 'release', 'award', 'medal', ...
  kind        TEXT NOT NULL,
  label       TEXT NOT NULL,
  -- ISO-ish: 'YYYY', 'YYYY-MM' or 'YYYY-MM-DD'; negative years allowed.
  start_date  TEXT NOT NULL,
  end_date    TEXT,
  precision   TEXT NOT NULL CHECK (precision IN ('year', 'month', 'day')),
  -- Denormalised for range queries; text dates don't sort across year 0.
  start_year  INTEGER NOT NULL,
  end_year    INTEGER,
  -- Coarse facet for filtering lanes: 'film', 'tv', 'baseball', 'politician'
  category    TEXT NOT NULL,
  -- Source-specific extras as JSON.
  detail      TEXT CHECK (detail IS NULL OR json_valid(detail)),
  UNIQUE (source_id, external_id)
) STRICT;

CREATE INDEX events_by_year ON events (start_year, end_year);
CREATE INDEX events_by_entity ON events (entity_id);
CREATE INDEX events_by_kind ON events (kind, start_year);
CREATE INDEX events_by_category ON events (category, start_year);
CREATE INDEX entities_by_wikidata ON entities (wikidata_id);

-- Flattened read model for the API and the timeline views. TrailBase's view
-- parser does not support table aliases, hence the full table names.
CREATE VIEW v_events AS
  SELECT
    events.id, events.kind, events.label, events.start_date, events.end_date,
    events.precision, events.start_year, events.end_year, events.category,
    events.detail,
    entities.id AS entity_id, entities.kind AS entity_kind,
    entities.name AS entity_name, entities.external_id AS entity_external_id,
    entities.wikidata_id, entities.url,
    sources.slug AS source
  FROM events
  JOIN entities ON entities.id = events.entity_id
  JOIN sources ON sources.id = events.source_id
/* v_events(id,kind,label,start_date,end_date,precision,start_year,end_year,category,detail,entity_id,entity_kind,entity_name,entity_external_id,wikidata_id,url,source) */;

-- Name search over entities. There are no sync triggers on purpose: rows only
-- change through the ingest, which rebuilds this index at the end of a sync.
CREATE VIRTUAL TABLE entities_fts USING fts5(
  name,
  description,
  content='entities',
  content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);
