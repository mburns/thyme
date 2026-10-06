-- Create temporary tables with original TSV structure
-- Using TEXT for all columns to be flexible with data types

CREATE TABLE t_title_basics (
    tconst TEXT,
    titleType TEXT,
    primaryTitle TEXT,
    originalTitle TEXT,
    isAdult TEXT,
    startYear TEXT,
    endYear TEXT,
    runtimeMinutes TEXT,
    genres TEXT
);

CREATE TABLE t_name_basics (
    nconst TEXT,
    primaryName TEXT,
    birthYear TEXT,
    deathYear TEXT,
    primaryProfession TEXT,
    knownForTitles TEXT
);

CREATE TABLE t_title_ratings (
    tconst TEXT,
    averageRating TEXT,
    numVotes TEXT
);

CREATE TABLE t_title_episode (
    tconst TEXT,
    parentTconst TEXT,
    seasonNumber TEXT,
    episodeNumber TEXT
);

CREATE TABLE t_title_principals (
    tconst TEXT,
    ordering TEXT,
    nconst TEXT,
    category TEXT,
    job TEXT,
    characters TEXT
);

CREATE TABLE t_title_crew (
    tconst TEXT,
    directors TEXT,
    writers TEXT
); 