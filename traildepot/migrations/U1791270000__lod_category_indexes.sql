-- Domain views ask the level-of-detail tables for a list of categories.
--
-- The primary keys lead with (bucket_size, bucket), which is right for the
-- '*' rows a plain window asks for. A domain view asks for up to fifty
-- categories over a bucket range instead; on that key SQLite scans every
-- category in the range (0.7-1.2 s per tile on 475k LOD rows). With the
-- category ahead of the bucket each category is one seek and a short range.
--
-- The rank is copied onto the LOD rows so the top events of a bucket across
-- several categories can be picked before joining `events`; `make rerank`
-- fills it, rows written before this migration read as rank 0.
ALTER TABLE event_lod ADD COLUMN rank REAL NOT NULL DEFAULT 0;
ALTER TABLE span_lod ADD COLUMN rank REAL NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS event_lod_by_category
  ON event_lod (bucket_size, category, bucket, rank DESC, event_id);
CREATE INDEX IF NOT EXISTS span_lod_by_category
  ON span_lod (bucket_size, category, bucket, rank DESC, event_id);

-- `/timeline/domains` sums event_density per category list; the PK leads
-- with source_id, so without this every domain is a full scan.
CREATE INDEX IF NOT EXISTS event_density_by_category
  ON event_density (category, year);
