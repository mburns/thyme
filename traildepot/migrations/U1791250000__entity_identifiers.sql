-- External identifiers of entities, the exact cross-source key.
--
-- IMDB entities carry their nconst/tconst, Lahman players their
-- Baseball-Reference id, and Wikidata items carry the same ids as properties
-- (P345, P1825, P3171). Two entities with the same (scheme, value) are the
-- same thing, which the linker records in entity_links with certainty.
CREATE TABLE entity_identifiers (
  entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
  -- 'imdb', 'bbref', 'olympedia', 'wikidata', ...
  scheme    TEXT NOT NULL,
  value     TEXT NOT NULL,
  PRIMARY KEY (entity_id, scheme, value)
) WITHOUT ROWID, STRICT;
CREATE INDEX entity_identifiers_by_value ON entity_identifiers (scheme, value, entity_id);

-- The read model gains the columns added since it was created.
DROP VIEW v_events;
CREATE VIEW v_events AS
  SELECT
    events.id, events.kind, events.label, events.start_date, events.end_date,
    events.precision, events.start_year, events.end_year, events.category,
    events.detail, events.span, events.certainty,
    entities.id AS entity_id, entities.kind AS entity_kind,
    entities.name AS entity_name, entities.external_id AS entity_external_id,
    entities.wikidata_id, entities.url,
    sources.slug AS source
  FROM events
  JOIN entities ON entities.id = events.entity_id
  JOIN sources ON sources.id = events.source_id
/* v_events(id,kind,label,start_date,end_date,precision,start_year,end_year,category,detail,span,certainty,entity_id,entity_kind,entity_name,entity_external_id,wikidata_id,url,source) */;
