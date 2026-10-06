-- Scale: rank, level-of-detail, and indexes for scanning tens of millions
-- of events interactively.
--
-- Scanning a timeline means two kinds of query: "what happens in this
-- window" at a zoom where every event fits, and "what matters in this
-- window" when millions do not. The first wants ordered index scans that
-- stop at the page size; the second wants a precomputed answer.
--
-- 1. `rank`: a per-event importance score (log of votes, participants and
--    the owner's event count), computed by the ingest.
-- 2. `event_lod`: the top-ranked events per (bucket size, bucket, category,
--    source), for 1-, 10- and 100-year buckets. A zoomed-out view reads a
--    few hundred rows from here instead of sorting the raw table.
-- 3. Indexes whose leading columns are the filters and whose order is
--    (start_year, id), so a window query with a filter walks one index in
--    output order and stops at the page size; keyset pagination
--    continues from (start_year, id) without OFFSET.

ALTER TABLE events ADD COLUMN rank REAL NOT NULL DEFAULT 0;

CREATE TABLE event_lod (
  bucket_size INTEGER NOT NULL,
  bucket      INTEGER NOT NULL,
  category    TEXT NOT NULL,
  source_id   INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  -- 1 = highest rank in the cell
  pos         INTEGER NOT NULL,
  event_id    INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  PRIMARY KEY (bucket_size, bucket, category, source_id, pos)
) WITHOUT ROWID, STRICT;
CREATE INDEX event_lod_by_event ON event_lod (event_id);

-- Ordered by (start_year, rowid): keyset scans without a filter.
CREATE INDEX events_by_start ON events (start_year);
-- Per-source windows.
CREATE INDEX events_by_source_year ON events (source_id, start_year);
-- Per-entity timelines in order, replacing the unordered entity index.
DROP INDEX events_by_entity;
CREATE INDEX events_by_entity ON events (entity_id, start_year);
-- Highest-ranked events of a category, for ad-hoc "top N" without the LOD.
CREATE INDEX events_by_rank ON events (category, rank DESC);
