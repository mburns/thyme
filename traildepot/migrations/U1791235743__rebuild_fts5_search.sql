-- Rebuild the FTS5 search index.
--
-- The previous search migration (U1750640633) had three problems:
--   * `titles_fts` used the view `v_title_details` as its external content
--     table, so FTS could not reliably read rows back by rowid.
--   * `search_fts` was backed by a view and had no triggers, so it was never
--     populated.
--   * Neither index was ever (re)built from the rows already in the database.
--
-- This migration replaces them with two external-content FTS5 tables backed
-- by the real `titles` and `persons` tables, keeps them in sync with
-- triggers, and builds them from the existing rows. Columns are limited to
-- the ones a search should match on; everything else is fetched by joining
-- back to the content table on rowid.

DROP TRIGGER IF EXISTS titles_ai;
DROP TRIGGER IF EXISTS titles_ad;
DROP TRIGGER IF EXISTS titles_au;
DROP TRIGGER IF EXISTS persons_ai;
DROP TRIGGER IF EXISTS persons_ad;
DROP TRIGGER IF EXISTS persons_au;

DROP TABLE IF EXISTS search_fts;
DROP VIEW IF EXISTS search_view;
DROP TABLE IF EXISTS titles_fts;
DROP TABLE IF EXISTS persons_fts;

-- `genres` is a comma-separated list ("Action,Comedy"); the unicode61
-- tokenizer splits on the comma, so each genre becomes its own token.
CREATE VIRTUAL TABLE titles_fts USING fts5(
  primaryTitle,
  originalTitle,
  genres,
  startYear,
  content='titles',
  content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);

CREATE VIRTUAL TABLE persons_fts USING fts5(
  primaryName,
  primaryProfession,
  content='persons',
  content_rowid='id',
  tokenize='unicode61 remove_diacritics 2'
);

-- External-content tables are not updated automatically; these triggers
-- mirror every change to the content tables into the index. The 'delete'
-- command must be given the exact values that were indexed.
CREATE TRIGGER titles_ai AFTER INSERT ON titles BEGIN
  INSERT INTO titles_fts(rowid, primaryTitle, originalTitle, genres, startYear)
  VALUES (new.id, new.primaryTitle, new.originalTitle, new.genres, new.startYear);
END;

CREATE TRIGGER titles_ad AFTER DELETE ON titles BEGIN
  INSERT INTO titles_fts(titles_fts, rowid, primaryTitle, originalTitle, genres, startYear)
  VALUES ('delete', old.id, old.primaryTitle, old.originalTitle, old.genres, old.startYear);
END;

CREATE TRIGGER titles_au AFTER UPDATE ON titles BEGIN
  INSERT INTO titles_fts(titles_fts, rowid, primaryTitle, originalTitle, genres, startYear)
  VALUES ('delete', old.id, old.primaryTitle, old.originalTitle, old.genres, old.startYear);
  INSERT INTO titles_fts(rowid, primaryTitle, originalTitle, genres, startYear)
  VALUES (new.id, new.primaryTitle, new.originalTitle, new.genres, new.startYear);
END;

CREATE TRIGGER persons_ai AFTER INSERT ON persons BEGIN
  INSERT INTO persons_fts(rowid, primaryName, primaryProfession)
  VALUES (new.id, new.primaryName, new.primaryProfession);
END;

CREATE TRIGGER persons_ad AFTER DELETE ON persons BEGIN
  INSERT INTO persons_fts(persons_fts, rowid, primaryName, primaryProfession)
  VALUES ('delete', old.id, old.primaryName, old.primaryProfession);
END;

CREATE TRIGGER persons_au AFTER UPDATE ON persons BEGIN
  INSERT INTO persons_fts(persons_fts, rowid, primaryName, primaryProfession)
  VALUES ('delete', old.id, old.primaryName, old.primaryProfession);
  INSERT INTO persons_fts(rowid, primaryName, primaryProfession)
  VALUES (new.id, new.primaryName, new.primaryProfession);
END;

-- Index whatever is already in the content tables. On an empty database this
-- is instant; on a fully imported one it runs once at startup.
INSERT INTO titles_fts(titles_fts) VALUES ('rebuild');
INSERT INTO persons_fts(persons_fts) VALUES ('rebuild');
