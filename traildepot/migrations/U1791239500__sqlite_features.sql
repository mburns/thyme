-- Lean on SQLite features that fit a timeline database.
--
-- Everything here is supported by every SQLite build that touches main.db:
-- TrailBase's bundled 3.49 (FTS5, R*Tree, STAT4, JSON, generated columns,
-- window functions), the Python module used by the ingest, and the sqlite3
-- CLI used by the IMDB import (3.43+). Math functions and geopoly are NOT
-- available in TrailBase and are deliberately avoided.

-- 1. Spans versus instants. An instant has no end date, but so does an
--    ongoing span (a living person, a running series). The `span` flag makes
--    the distinction explicit instead of relying on `kind`.
ALTER TABLE events ADD COLUMN span INTEGER NOT NULL DEFAULT 0 CHECK (span IN (0, 1));
UPDATE events SET span = 1 WHERE kind IN ('life', 'career', 'run');

-- 2. Julian day numbers for day-precision dates, as VIRTUAL generated
--    columns: computed on read, nothing stored, so day-level offsets between
--    events ("released 412 days after her debut") are a subtraction.
ALTER TABLE events ADD COLUMN start_julian REAL
  GENERATED ALWAYS AS (CASE WHEN precision = 'day' THEN julianday(start_date) END) VIRTUAL;
ALTER TABLE events ADD COLUMN end_julian REAL
  GENERATED ALWAYS AS (CASE WHEN length(end_date) = 10 THEN julianday(end_date) END) VIRTUAL;

-- 3. R*Tree over [start_year, end_year]. "What overlaps 1960-1975" is a 2-D
--    range query that a B-tree on (start_year, end_year) answers badly; the
--    R*Tree prunes on both bounds. Ongoing spans extend to OPEN_END (9999).
--    rtree_i32 stores exact 32-bit integers rather than floats.
CREATE VIRTUAL TABLE events_span USING rtree_i32(id, start_year, end_year);

INSERT INTO events_span
SELECT id, start_year,
       max(start_year, CASE WHEN span = 1 AND end_year IS NULL THEN 9999
                            ELSE coalesce(end_year, start_year) END)
FROM events;

CREATE TRIGGER events_span_ai AFTER INSERT ON events BEGIN
  INSERT INTO events_span
  VALUES (new.id, new.start_year,
          max(new.start_year, CASE WHEN new.span = 1 AND new.end_year IS NULL THEN 9999
                                   ELSE coalesce(new.end_year, new.start_year) END));
END;

CREATE TRIGGER events_span_au AFTER UPDATE OF start_year, end_year, span ON events BEGIN
  UPDATE events_span
     SET start_year = new.start_year,
         end_year = max(new.start_year, CASE WHEN new.span = 1 AND new.end_year IS NULL THEN 9999
                                             ELSE coalesce(new.end_year, new.start_year) END)
   WHERE id = new.id;
END;

CREATE TRIGGER events_span_ad AFTER DELETE ON events BEGIN
  DELETE FROM events_span WHERE id = old.id;
END;

-- 4. Partial index: most entities have no QID, so index only the ones that do.
DROP INDEX entities_by_wikidata;
CREATE INDEX entities_by_wikidata ON entities (wikidata_id) WHERE wikidata_id IS NOT NULL;

-- 5. Trigram tokenizer for entity names: substring and case-insensitive
--    matching ("odfath" finds "The Godfather"), and indexed LIKE/GLOB, at the
--    cost of a larger index and a three-character minimum query. The
--    title/person search indexes keep unicode61 for prefix-as-you-type.
DROP TABLE entities_fts;
CREATE VIRTUAL TABLE entities_fts USING fts5(
  name,
  description,
  content='entities',
  content_rowid='id',
  tokenize='trigram'
);
INSERT INTO entities_fts(entities_fts) VALUES ('rebuild');

-- 6. Normalise IMDB's comma-separated lists with json_each so genres and
--    professions are queryable rows instead of LIKE '%Drama%' scans. The
--    import repopulates these after each load (sql/import_genres.sql).
CREATE TABLE title_genres (
  title_id INTEGER NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
  genre    TEXT NOT NULL,
  PRIMARY KEY (title_id, genre)
) WITHOUT ROWID, STRICT;
CREATE INDEX title_genres_by_genre ON title_genres (genre, title_id);

CREATE TABLE person_professions (
  person_id  INTEGER NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
  profession TEXT NOT NULL,
  PRIMARY KEY (person_id, profession)
) WITHOUT ROWID, STRICT;
CREATE INDEX person_professions_by_profession ON person_professions (profession, person_id);

INSERT OR IGNORE INTO title_genres (title_id, genre)
SELECT titles.id, trim(json_each.value)
FROM titles, json_each('["' || replace(replace(replace(titles.genres, '\', '\\'), '"', '\"'), ',', '","') || '"]')
WHERE titles.genres IS NOT NULL AND trim(json_each.value) <> '';

INSERT OR IGNORE INTO person_professions (person_id, profession)
SELECT persons.id, trim(json_each.value)
FROM persons, json_each('["' || replace(replace(replace(persons.primaryProfession, '\', '\\'), '"', '\"'), ',', '","') || '"]')
WHERE persons.primaryProfession IS NOT NULL AND trim(json_each.value) <> '';

-- The old view grouped on the raw comma-separated string, so "Action,Comedy"
-- counted as its own genre.
DROP VIEW v_genre_summary;
CREATE VIEW v_genre_summary AS
  SELECT genre, count(*) AS title_count
  FROM title_genres
  GROUP BY genre
/* v_genre_summary(genre,title_count) */;
