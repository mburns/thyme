-- IMDB Schema Optimizations Migration
-- This migration adds additional constraints, indexes, and optimizations
-- Note: The following ALTER TABLE ... ADD CONSTRAINT statements are not
-- compatible with SQLite and have been removed. These constraints should be
-- added to the original CREATE TABLE statements in 001_imdb_schema.sql if desired.
-- 1. Add check constraints for better data integrity
-- 2. Add composite indexes for common query patterns
CREATE INDEX idx_titles_type_year ON titles(title_type, start_year);
CREATE INDEX idx_titles_genres ON titles(genres)
WHERE genres IS NOT NULL;
CREATE INDEX idx_ratings_rating_votes ON ratings(average_rating, num_votes);
CREATE INDEX idx_persons_profession ON persons(primary_profession)
WHERE primary_profession IS NOT NULL;
-- 3. Add indexes for JSON queries (if supported)
CREATE INDEX idx_titles_genres_json ON titles(genres)
WHERE json_valid(genres);
CREATE INDEX idx_persons_known_for_json ON persons(known_for_titles)
WHERE json_valid(known_for_titles);
-- 4. Add partial indexes for better performance
CREATE INDEX idx_titles_movies ON titles(tconst, primary_title, start_year)
WHERE title_type = 'movie'
    AND start_year IS NOT NULL;
CREATE INDEX idx_titles_tv_series ON titles(tconst, primary_title, start_year)
WHERE title_type = 'tvSeries'
    AND start_year IS NOT NULL;
CREATE INDEX idx_ratings_high_rated ON ratings(title_id, average_rating)
WHERE average_rating >= 8.0
    AND num_votes >= 1000;
-- 5. Add indexes for foreign key relationships
CREATE INDEX idx_title_principals_title_person ON title_principals(title_id, person_id);
CREATE INDEX idx_title_akas_title_region ON title_akas(title_id, region)
WHERE region IS NOT NULL;
-- 6. Add covering indexes for common queries
CREATE INDEX idx_titles_covering ON titles(
    tconst,
    title_type,
    primary_title,
    start_year,
    genres
);
-- 7. Add statistics table for metadata
CREATE TABLE imdb_stats (
    id BLOB PRIMARY KEY NOT NULL CHECK(is_uuid(id)) DEFAULT (uuid_v4()),
    stat_name TEXT UNIQUE NOT NULL,
    stat_value TEXT NOT NULL,
    stat_type TEXT NOT NULL CHECK(
        stat_type IN ('integer', 'float', 'text', 'json')
    ),
    description TEXT,
    last_updated INTEGER DEFAULT (UNIXEPOCH()) NOT NULL
) STRICT;
-- 8. Add views for common queries
CREATE VIEW top_rated_movies AS
SELECT t.tconst,
    t.primary_title,
    t.start_year,
    t.genres,
    r.average_rating,
    r.num_votes
FROM titles t
    JOIN ratings r ON t.id = r.title_id
WHERE t.title_type = 'movie'
    AND r.num_votes >= 1000
    AND t.start_year IS NOT NULL
ORDER BY r.average_rating DESC,
    r.num_votes DESC;
CREATE VIEW top_rated_tv_series AS
SELECT t.tconst,
    t.primary_title,
    t.start_year,
    t.genres,
    r.average_rating,
    r.num_votes
FROM titles t
    JOIN ratings r ON t.id = r.title_id
WHERE t.title_type = 'tvSeries'
    AND r.num_votes >= 1000
    AND t.start_year IS NOT NULL
ORDER BY r.average_rating DESC,
    r.num_votes DESC;
CREATE VIEW most_prolific_actors AS
SELECT p.nconst,
    p.primary_name,
    p.primary_profession,
    COUNT(DISTINCT tp.title_id) as title_count,
    COUNT(
        DISTINCT CASE
            WHEN tp.category IN ('actor', 'actress') THEN tp.title_id
        END
    ) as acting_roles
FROM persons p
    JOIN title_principals tp ON p.id = tp.person_id
WHERE tp.category IN ('actor', 'actress')
GROUP BY p.id,
    p.nconst,
    p.primary_name,
    p.primary_profession
ORDER BY acting_roles DESC;
-- 9. Add triggers for maintaining statistics
CREATE TRIGGER update_stats_after_person_insert
AFTER
INSERT ON persons BEGIN
UPDATE imdb_stats
SET stat_value = (
        SELECT COUNT(*)
        FROM persons
    ),
    last_updated = UNIXEPOCH()
WHERE stat_name = 'total_persons';
END;
CREATE TRIGGER update_stats_after_title_insert
AFTER
INSERT ON titles BEGIN
UPDATE imdb_stats
SET stat_value = (
        SELECT COUNT(*)
        FROM titles
    ),
    last_updated = UNIXEPOCH()
WHERE stat_name = 'total_titles';
END;
CREATE TRIGGER update_stats_after_rating_insert
AFTER
INSERT ON ratings BEGIN
UPDATE imdb_stats
SET stat_value = (
        SELECT COUNT(*)
        FROM ratings
    ),
    last_updated = UNIXEPOCH()
WHERE stat_name = 'total_ratings';
END;
-- 10. Insert initial statistics
INSERT INTO imdb_stats (stat_name, stat_value, stat_type, description)
VALUES (
        'total_persons',
        '0',
        'integer',
        'Total number of persons in the database'
    ),
    (
        'total_titles',
        '0',
        'integer',
        'Total number of titles in the database'
    ),
    (
        'total_ratings',
        '0',
        'integer',
        'Total number of ratings in the database'
    ),
    (
        'import_date',
        '',
        'text',
        'Date when the data was imported'
    ),
    (
        'data_version',
        '',
        'text',
        'Version of the IMDB dataset'
    );
-- 11. Add function to update all statistics
-- Note: The following CREATE OR REPLACE FUNCTION statements are not compatible
-- with SQLite and have been removed. This logic should be handled in the
-- application layer.
-- 12. Add additional constraints for data quality
-- Note: The following ALTER TABLE ... ADD CONSTRAINT statements are not
-- compatible with SQLite and have been removed. These constraints are
-- already present in the 001_imdb_schema.sql file.
-- 13. Add indexes for text search (if full-text search is available)
-- Note: SQLite doesn't support full-text search, so this section is not applicable
-- 14. Add materialized view for frequently accessed data
-- Note: SQLite doesn't support materialized views, but we can create regular views
CREATE VIEW movie_details AS
SELECT t.id,
    t.tconst,
    t.primary_title,
    t.original_title,
    t.start_year,
    t.runtime_minutes,
    t.genres,
    r.average_rating,
    r.num_votes,
    tc.directors,
    tc.writers
FROM titles t
    LEFT JOIN ratings r ON t.id = r.title_id
    LEFT JOIN title_crew tc ON t.id = tc.title_id
WHERE t.title_type = 'movie';
-- 15. Add function to get person filmography
-- Note: The following CREATE OR REPLACE FUNCTION statement is not compatible
-- with SQLite and has been removed. This logic should be handled in the
-- application layer.