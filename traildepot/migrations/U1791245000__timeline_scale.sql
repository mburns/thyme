-- Scale and model additions for complicated timelines.
--
-- 1. Date certainty, so sources can mark "circa" and unknown dates.
-- 2. A precomputed density table: counts per source, category and year,
--    refreshed by the ingest, so histogram strips never scan `events`.
-- 3. Entity links: the same real-world person seen by several sources
--    (IMDB, Lahman, Wikidata) resolves to one canonical entity.
-- 4. Event participants: who took part in an event beyond its owner
--    (a film's cast, a championship roster).

ALTER TABLE events ADD COLUMN certainty TEXT NOT NULL DEFAULT 'exact'
  CHECK (certainty IN ('exact', 'circa', 'unknown'));

CREATE TABLE event_density (
  source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  category  TEXT NOT NULL,
  year      INTEGER NOT NULL,
  count     INTEGER NOT NULL,
  PRIMARY KEY (source_id, category, year)
) WITHOUT ROWID, STRICT;
CREATE INDEX event_density_by_year ON event_density (year);

INSERT INTO event_density (source_id, category, year, count)
SELECT source_id, category, start_year, count(*) FROM events GROUP BY 1, 2, 3;

-- entity_id is the duplicate, canonical_id the entity it resolves to (the
-- Wikidata one when known, since QIDs are the cross-source key). A canonical
-- entity never appears as entity_id.
CREATE TABLE entity_links (
  entity_id    INTEGER PRIMARY KEY REFERENCES entities(id) ON DELETE CASCADE,
  canonical_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  -- 'wikidata_id' (shared QID) or 'name_dates' (same name, birth, death)
  method       TEXT NOT NULL,
  confidence   REAL NOT NULL CHECK (confidence > 0 AND confidence <= 1),
  CHECK (entity_id <> canonical_id)
) STRICT;
CREATE INDEX entity_links_by_canonical ON entity_links (canonical_id);

CREATE TABLE event_participants (
  event_id  INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  -- 'actor', 'director', 'player', ...
  role      TEXT NOT NULL,
  PRIMARY KEY (event_id, entity_id, role)
) WITHOUT ROWID, STRICT;
CREATE INDEX event_participants_by_entity ON event_participants (entity_id, event_id);
