-- Level of detail for spans, and an exact-name index.
--
-- A window's "active" spans (the lives, careers and runs open at its start)
-- are inherently a huge set: everyone alive in 1960. The R*Tree finds them
-- in milliseconds, but choosing the notable ones means sorting all of them.
-- span_lod precomputes, per 10- and 100-year bucket and category, the
-- top-ranked spans that overlap the bucket, so the question becomes a
-- primary-key lookup. Category '*' holds the top spans across categories;
-- event_lod gets the same '*' rows from the ingest.
CREATE TABLE span_lod (
  bucket_size INTEGER NOT NULL,
  bucket      INTEGER NOT NULL,
  category    TEXT NOT NULL,
  source_id   INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  pos         INTEGER NOT NULL,
  event_id    INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  PRIMARY KEY (bucket_size, bucket, category, source_id, pos)
) WITHOUT ROWID, STRICT;
CREATE INDEX span_lod_by_event ON span_lod (event_id);

-- Exact-name lookups (linking, "go to entity") scanned 2M rows.
CREATE INDEX entities_by_name ON entities (name);
