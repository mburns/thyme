-- A minimal view to test the TrailBase SQL parseratings.
-- This view contains no JOINs or aliases.
CREATE VIEW v_simple_titles AS SELECT id, primaryTitle, genres FROM titles; 
/* v_simple_titles(id,primaryTitle,genres) */;
CREATE VIEW v_title_details AS
            SELECT
              titles.id, titles.tconst, titles.titleType, titles.primaryTitle, titles.originalTitle,
              titles.isAdult, titles.startYear, titles.endYear, titles.runtimeMinutes, titles.genres,
              ratings.averageRating, ratings.numVotes
            FROM titles
            LEFT JOIN ratings ON titles.id = ratings.title_id
/* v_title_details(id,tconst,titleType,primaryTitle,originalTitle,isAdult,startYear,endYear,runtimeMinutes,genres,averageRating,numVotes) */;
CREATE VIEW v_title_principals AS
            SELECT
              principals.title_id, principals.ordering, principals.category, principals.job, principals.characters,
              persons.id as person_id, persons.nconst, persons.primaryName,
              persons.birthYear, persons.deathYear
            FROM principals
            JOIN persons ON principals.person_id = persons.id
/* v_title_principals(title_id,ordering,category,job,characters,person_id,nconst,primaryName,birthYear,deathYear) */;
CREATE VIEW v_person_titles AS
            SELECT
              principals.person_id, principals.category, principals.job, principals.characters,
              titles.id as title_id, titles.tconst, titles.primaryTitle, titles.titleType, titles.startYear
            FROM principals
            JOIN titles ON principals.title_id = titles.id
/* v_person_titles(person_id,category,job,characters,title_id,tconst,primaryTitle,titleType,startYear) */;
CREATE VIEW v_title_episodes AS
            SELECT
              episodes.parent_title_id, episodes.seasonNumber, episodes.episodeNumber,
              titles.id as episode_title_id, titles.tconst as episode_tconst,
              titles.primaryTitle as episode_title, titles.startYear as episode_year,
              titles.runtimeMinutes as episode_runtime
            FROM episodes
            JOIN titles ON episodes.title_id = titles.id
            ORDER BY episodes.seasonNumber, episodes.episodeNumber
/* v_title_episodes(parent_title_id,seasonNumber,episodeNumber,episode_title_id,episode_tconst,episode_title,episode_year,episode_runtime) */;
CREATE VIEW v_genre_summary AS
            SELECT
              genres as genre,
              COUNT(*) as title_count
            FROM titles
            WHERE genres IS NOT NULL
            GROUP BY genres
/* v_genre_summary(genre,title_count) */;
