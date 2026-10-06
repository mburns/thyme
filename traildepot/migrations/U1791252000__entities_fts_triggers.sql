-- Keep entities_fts in sync with triggers instead of a full rebuild.
--
-- The ingest used to rebuild the trigram index at the end of every sync,
-- which costs the same (tens of seconds over a million names) whether the
-- sync touched ten entities or a million. Triggers make the cost
-- proportional to the rows the sync actually changed. External-content
-- FTS5 'delete' commands must repeat the indexed values.
CREATE TRIGGER entities_ai AFTER INSERT ON entities BEGIN
  INSERT INTO entities_fts(rowid, name, description)
  VALUES (new.id, new.name, new.description);
END;

CREATE TRIGGER entities_ad AFTER DELETE ON entities BEGIN
  INSERT INTO entities_fts(entities_fts, rowid, name, description)
  VALUES ('delete', old.id, old.name, old.description);
END;

CREATE TRIGGER entities_au AFTER UPDATE OF name, description ON entities BEGIN
  INSERT INTO entities_fts(entities_fts, rowid, name, description)
  VALUES ('delete', old.id, old.name, old.description);
  INSERT INTO entities_fts(rowid, name, description)
  VALUES (new.id, new.name, new.description);
END;

-- One last full rebuild so the index matches the table before the triggers
-- take over.
INSERT INTO entities_fts(entities_fts) VALUES ('rebuild');
