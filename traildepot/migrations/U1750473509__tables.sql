-- migrations/20250621021500_create_imdb_tables.sql

-- Creates the main tables with integer primary keys and strict typing

CREATE TABLE titles (
  id INTEGER PRIMARY KEY,
  tconst TEXT UNIQUE NOT NULL,
  titleType TEXT,
  primaryTitle TEXT,
  originalTitle TEXT,
  isAdult INTEGER,
  startYear INTEGER,
  endYear INTEGER,
  runtimeMinutes INTEGER,
  genres TEXT
) STRICT;

CREATE TABLE persons (
  id INTEGER PRIMARY KEY,
  nconst TEXT UNIQUE NOT NULL,
  primaryName TEXT,
  birthYear INTEGER,
  deathYear INTEGER,
  primaryProfession TEXT
) STRICT;

CREATE TABLE principals (
  id INTEGER PRIMARY KEY,
  title_id INTEGER NOT NULL REFERENCES titles(id),
  person_id INTEGER NOT NULL REFERENCES persons(id),
  ordering INTEGER,
  category TEXT,
  job TEXT,
  characters TEXT
) STRICT;

CREATE TABLE ratings (
  title_id INTEGER PRIMARY KEY REFERENCES titles(id),
  averageRating REAL,
  numVotes INTEGER
) STRICT;

CREATE TABLE episodes (
  title_id INTEGER PRIMARY KEY REFERENCES titles(id),
  parent_title_id INTEGER REFERENCES titles(id),
  seasonNumber INTEGER,
  episodeNumber INTEGER
) STRICT;

CREATE TABLE crew (
  id INTEGER PRIMARY KEY,
  title_id INTEGER NOT NULL REFERENCES titles(id),
  person_id INTEGER NOT NULL REFERENCES persons(id),
  role TEXT NOT NULL,
  UNIQUE(title_id, person_id, role)
) STRICT; 