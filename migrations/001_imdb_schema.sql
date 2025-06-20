-- IMDB Database Schema Migration
-- This migration creates tables for IMDB data with strict constraints
-- Persons table (actors, crew, etc.)
CREATE TABLE persons (
    id BLOB PRIMARY KEY NOT NULL CHECK(is_uuid(id)) DEFAULT (uuid_v4()),
    nconst TEXT UNIQUE NOT NULL,
    -- IMDB person identifier
    primary_name TEXT NOT NULL,
    birth_year INTEGER CHECK(
        birth_year >= 1800
        AND birth_year <= 2100
    ),
    death_year INTEGER CHECK(
        death_year >= 1800
        AND death_year <= 2100
    ),
    primary_profession TEXT,
    known_for_titles TEXT,
    -- JSON array of title IDs
    created INTEGER DEFAULT (UNIXEPOCH()) NOT NULL,
    updated INTEGER DEFAULT (UNIXEPOCH()) NOT NULL
) STRICT;
-- Titles table (movies, TV shows, episodes, etc.)
CREATE TABLE titles (
    id BLOB PRIMARY KEY NOT NULL CHECK(is_uuid(id)) DEFAULT (uuid_v4()),
    tconst TEXT UNIQUE NOT NULL,
    -- IMDB title identifier
    title_type TEXT NOT NULL CHECK(
        title_type IN (
            'movie',
            'tvSeries',
            'tvEpisode',
            'tvMiniSeries',
            'short',
            'video',
            'tvMovie',
            'tvSpecial',
            'videoGame',
            'tvShort'
        )
    ),
    primary_title TEXT NOT NULL,
    original_title TEXT,
    is_adult BOOLEAN DEFAULT FALSE NOT NULL,
    start_year INTEGER CHECK(
        start_year >= 1800
        AND start_year <= 2100
    ),
    end_year INTEGER CHECK(
        end_year >= 1800
        AND end_year <= 2100
    ),
    runtime_minutes INTEGER CHECK(runtime_minutes > 0),
    genres TEXT,
    -- JSON array of genres
    -- Episode-specific fields (NULL for non-episodes)
    parent_tconst TEXT,
    -- For episodes, references parent series
    season_number INTEGER CHECK(season_number > 0),
    episode_number INTEGER CHECK(episode_number > 0),
    created INTEGER DEFAULT (UNIXEPOCH()) NOT NULL,
    updated INTEGER DEFAULT (UNIXEPOCH()) NOT NULL
) STRICT;
-- Ratings table
CREATE TABLE ratings (
    id BLOB PRIMARY KEY NOT NULL CHECK(is_uuid(id)) DEFAULT (uuid_v4()),
    title_id BLOB NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
    average_rating DECIMAL(3, 1) NOT NULL CHECK(
        average_rating >= 0.0
        AND average_rating <= 10.0
    ),
    num_votes INTEGER NOT NULL CHECK(num_votes >= 0),
    created INTEGER DEFAULT (UNIXEPOCH()) NOT NULL,
    updated INTEGER DEFAULT (UNIXEPOCH()) NOT NULL,
    UNIQUE(title_id)
) STRICT;
-- Alternative titles (AKAs)
CREATE TABLE title_akas (
    id BLOB PRIMARY KEY NOT NULL CHECK(is_uuid(id)) DEFAULT (uuid_v4()),
    title_id BLOB NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
    ordering INTEGER NOT NULL CHECK(ordering > 0),
    title TEXT NOT NULL,
    region TEXT,
    language TEXT,
    types TEXT,
    -- JSON array of types
    attributes TEXT,
    -- JSON array of attributes
    is_original_title BOOLEAN DEFAULT FALSE NOT NULL,
    created INTEGER DEFAULT (UNIXEPOCH()) NOT NULL,
    updated INTEGER DEFAULT (UNIXEPOCH()) NOT NULL
) STRICT;
-- Crew information (directors, writers)
CREATE TABLE title_crew (
    id BLOB PRIMARY KEY NOT NULL CHECK(is_uuid(id)) DEFAULT (uuid_v4()),
    title_id BLOB NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
    directors TEXT,
    -- JSON array of person nconsts
    writers TEXT,
    -- JSON array of person nconsts
    created INTEGER DEFAULT (UNIXEPOCH()) NOT NULL,
    updated INTEGER DEFAULT (UNIXEPOCH()) NOT NULL,
    UNIQUE(title_id)
) STRICT;
-- Principal cast and crew (detailed roles)
CREATE TABLE title_principals (
    id BLOB PRIMARY KEY NOT NULL CHECK(is_uuid(id)) DEFAULT (uuid_v4()),
    title_id BLOB NOT NULL REFERENCES titles(id) ON DELETE CASCADE,
    person_id BLOB NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    ordering INTEGER NOT NULL CHECK(ordering > 0),
    category TEXT NOT NULL CHECK(
        category IN (
            'actor',
            'actress',
            'director',
            'writer',
            'producer',
            'composer',
            'cinematographer',
            'editor',
            'production_designer',
            'costume_designer',
            'make_up_department',
            'sound_department',
            'visual_effects',
            'stunts',
            'art_department',
            'camera_department',
            'animation_department',
            'casting_department',
            'costume_department',
            'editorial_department',
            'location_management',
            'music_department',
            'script_department',
            'transportation_department',
            'miscellaneous'
        )
    ),
    job TEXT,
    characters TEXT,
    -- JSON array of character names
    created INTEGER DEFAULT (UNIXEPOCH()) NOT NULL,
    updated INTEGER DEFAULT (UNIXEPOCH()) NOT NULL
) STRICT;
-- Indexes for performance
CREATE INDEX idx_persons_nconst ON persons(nconst);
CREATE INDEX idx_titles_tconst ON titles(tconst);
CREATE INDEX idx_titles_parent_tconst ON titles(parent_tconst);
CREATE INDEX idx_titles_title_type ON titles(title_type);
CREATE INDEX idx_titles_start_year ON titles(start_year);
CREATE INDEX idx_ratings_average_rating ON ratings(average_rating);
CREATE INDEX idx_ratings_num_votes ON ratings(num_votes);
CREATE INDEX idx_title_akas_title_id ON title_akas(title_id);
CREATE INDEX idx_title_crew_title_id ON title_crew(title_id);
CREATE INDEX idx_title_principals_title_id ON title_principals(title_id);
CREATE INDEX idx_title_principals_person_id ON title_principals(person_id);
CREATE INDEX idx_title_principals_category ON title_principals(category);
-- Triggers for updated timestamps
CREATE TRIGGER persons_updated_trigger
AFTER
UPDATE ON persons FOR EACH ROW BEGIN
UPDATE persons
SET updated = UNIXEPOCH()
WHERE id = OLD.id;
END;
CREATE TRIGGER titles_updated_trigger
AFTER
UPDATE ON titles FOR EACH ROW BEGIN
UPDATE titles
SET updated = UNIXEPOCH()
WHERE id = OLD.id;
END;
CREATE TRIGGER ratings_updated_trigger
AFTER
UPDATE ON ratings FOR EACH ROW BEGIN
UPDATE ratings
SET updated = UNIXEPOCH()
WHERE id = OLD.id;
END;
CREATE TRIGGER title_akas_updated_trigger
AFTER
UPDATE ON title_akas FOR EACH ROW BEGIN
UPDATE title_akas
SET updated = UNIXEPOCH()
WHERE id = OLD.id;
END;
CREATE TRIGGER title_crew_updated_trigger
AFTER
UPDATE ON title_crew FOR EACH ROW BEGIN
UPDATE title_crew
SET updated = UNIXEPOCH()
WHERE id = OLD.id;
END;
CREATE TRIGGER title_principals_updated_trigger
AFTER
UPDATE ON title_principals FOR EACH ROW BEGIN
UPDATE title_principals
SET updated = UNIXEPOCH()
WHERE id = OLD.id;
END;