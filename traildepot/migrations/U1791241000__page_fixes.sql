-- Give every page a working backend and index the queries the pages make.
--
-- TrailBase only exposes tables and views that carry an INTEGER (or UUID)
-- primary key column, which is why the genres page never worked: its view
-- had none. The list pages filter and sort on columns that had no index at
-- all, so each page load scanned millions of rows.

-- Genre summary as a real table. The IMDB import refreshes it
-- (sql/import_genres.sql) after every load.
CREATE TABLE genres (
  id          INTEGER PRIMARY KEY,
  genre       TEXT UNIQUE NOT NULL,
  title_count INTEGER NOT NULL
) STRICT;

INSERT INTO genres (genre, title_count)
SELECT genre, count(*) FROM title_genres GROUP BY genre;

DROP VIEW v_genre_summary;

-- Titles of a genre, keyed by titles.id so it can be a record API and
-- served from the (genre, title_id) index instead of LIKE '%Drama%'.
CREATE VIEW v_genre_titles AS
  SELECT
    titles.id, title_genres.genre, titles.tconst, titles.titleType,
    titles.primaryTitle, titles.startYear, titles.endYear, titles.runtimeMinutes,
    ratings.averageRating, ratings.numVotes
  FROM title_genres
  JOIN titles ON titles.id = title_genres.title_id
  LEFT JOIN ratings ON ratings.title_id = titles.id
/* v_genre_titles(id,genre,tconst,titleType,primaryTitle,startYear,endYear,runtimeMinutes,averageRating,numVotes) */;

-- The auto-named indexes from the admin UI duplicate existing constraints:
-- tconst and nconst are UNIQUE already, and ratings.title_id is the key.
DROP INDEX IF EXISTS "_titles__hasty_ant_index";
DROP INDEX IF EXISTS "_ratings__gnarly_ant_index";
DROP INDEX IF EXISTS "_persons__fresh_badger_index";

-- movies/tv/short/video/videogame pages: filter[titleType]=... order=-startYear
CREATE INDEX titles_by_type_year ON titles (titleType, startYear DESC);
-- movies and genres pages: order=-numVotes; top-rated: order=-averageRating,-numVotes
CREATE INDEX ratings_by_votes ON ratings (numVotes DESC);
CREATE INDEX ratings_by_rating ON ratings (averageRating DESC, numVotes DESC);
-- title page cast list and person page filmography (principals is ~90M rows)
CREATE INDEX principals_by_title ON principals (title_id, ordering);
CREATE INDEX principals_by_person ON principals (person_id);
CREATE INDEX crew_by_person ON crew (person_id);
-- title page episode list
CREATE INDEX episodes_by_parent ON episodes (parent_title_id, seasonNumber, episodeNumber);
