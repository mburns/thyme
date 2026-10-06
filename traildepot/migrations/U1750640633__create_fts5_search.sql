-- Create FTS5 virtual tables for full-text search
-- This migration adds search capabilities for titles, persons, and combined search

-- FTS5 virtual table for title search
CREATE VIRTUAL TABLE titles_fts USING fts5(
    id UNINDEXED,
    tconst UNINDEXED,
    titleType,
    primaryTitle,
    originalTitle,
    startYear,
    endYear,
    genres,
    averageRating UNINDEXED,
    numVotes UNINDEXED,
    content='v_title_details',
    content_rowid='id'
);

-- FTS5 virtual table for person search
CREATE VIRTUAL TABLE persons_fts USING fts5(
    id UNINDEXED,
    nconst UNINDEXED,
    primaryName,
    birthYear,
    deathYear,
    primaryProfession,
    content='persons',
    content_rowid='id'
);

-- FTS5 virtual table for combined search (titles + persons)
CREATE VIRTUAL TABLE search_fts USING fts5(
    id UNINDEXED,
    type UNINDEXED, -- 'title' or 'person'
    tconst UNINDEXED,
    nconst UNINDEXED,
    titleType,
    primaryTitle,
    originalTitle,
    startYear,
    endYear,
    genres,
    averageRating UNINDEXED,
    numVotes UNINDEXED,
    primaryName,
    birthYear,
    deathYear,
    primaryProfession,
    content='search_view',
    content_rowid='id'
);

-- Create a view that combines titles and persons for the search_fts table
CREATE VIEW search_view AS
SELECT 
    id,
    'title' as type,
    tconst,
    NULL as nconst,
    titleType,
    primaryTitle,
    originalTitle,
    startYear,
    endYear,
    genres,
    averageRating,
    numVotes,
    NULL as primaryName,
    NULL as birthYear,
    NULL as deathYear,
    NULL as primaryProfession
FROM v_title_details
UNION ALL
SELECT 
    id,
    'person' as type,
    NULL as tconst,
    nconst,
    NULL as titleType,
    primaryName as primaryTitle,
    NULL as originalTitle,
    birthYear as startYear,
    deathYear as endYear,
    primaryProfession as genres,
    NULL as averageRating,
    NULL as numVotes,
    primaryName,
    birthYear,
    deathYear,
    primaryProfession
FROM persons;

-- Create triggers to keep FTS5 tables in sync with main tables
-- For titles
CREATE TRIGGER titles_ai AFTER INSERT ON titles BEGIN
    INSERT INTO titles_fts(rowid, titleType, primaryTitle, originalTitle, startYear, endYear, genres)
    VALUES (new.id, new.titleType, new.primaryTitle, new.originalTitle, new.startYear, new.endYear, new.genres);
END;

CREATE TRIGGER titles_ad AFTER DELETE ON titles BEGIN
    INSERT INTO titles_fts(titles_fts, rowid, titleType, primaryTitle, originalTitle, startYear, endYear, genres)
    VALUES('delete', old.id, old.titleType, old.primaryTitle, old.originalTitle, old.startYear, old.endYear, old.genres);
END;

CREATE TRIGGER titles_au AFTER UPDATE ON titles BEGIN
    INSERT INTO titles_fts(titles_fts, rowid, titleType, primaryTitle, originalTitle, startYear, endYear, genres)
    VALUES('delete', old.id, old.titleType, old.primaryTitle, old.originalTitle, old.startYear, old.endYear, old.genres);
    INSERT INTO titles_fts(rowid, titleType, primaryTitle, originalTitle, startYear, endYear, genres)
    VALUES (new.id, new.titleType, new.primaryTitle, new.originalTitle, new.startYear, new.endYear, new.genres);
END;

-- For persons
CREATE TRIGGER persons_ai AFTER INSERT ON persons BEGIN
    INSERT INTO persons_fts(rowid, primaryName, birthYear, deathYear, primaryProfession)
    VALUES (new.id, new.primaryName, new.birthYear, new.deathYear, new.primaryProfession);
END;

CREATE TRIGGER persons_ad AFTER DELETE ON persons BEGIN
    INSERT INTO persons_fts(persons_fts, rowid, primaryName, birthYear, deathYear, primaryProfession)
    VALUES('delete', old.id, old.primaryName, old.birthYear, old.deathYear, old.primaryProfession);
END;

CREATE TRIGGER persons_au AFTER UPDATE ON persons BEGIN
    INSERT INTO persons_fts(persons_fts, rowid, primaryName, birthYear, deathYear, primaryProfession)
    VALUES('delete', old.id, old.primaryName, old.birthYear, old.deathYear, old.primaryProfession);
    INSERT INTO persons_fts(rowid, primaryName, birthYear, deathYear, primaryProfession)
    VALUES (new.id, new.primaryName, new.birthYear, new.deathYear, new.primaryProfession);
END; 