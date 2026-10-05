-- Rebuild the normalised genre and profession tables from the freshly
-- imported titles/persons, splitting IMDB's comma-separated lists with
-- json_each. Run after import_titles and import_persons.
DELETE FROM title_genres;
INSERT OR IGNORE INTO title_genres (title_id, genre)
SELECT titles.id, trim(json_each.value)
FROM titles, json_each('["' || replace(replace(replace(titles.genres, '\', '\\'), '"', '\"'), ',', '","') || '"]')
WHERE titles.genres IS NOT NULL AND trim(json_each.value) <> '';

DELETE FROM person_professions;
INSERT OR IGNORE INTO person_professions (person_id, profession)
SELECT persons.id, trim(json_each.value)
FROM persons, json_each('["' || replace(replace(replace(persons.primaryProfession, '\', '\\'), '"', '\"'), ',', '","') || '"]')
WHERE persons.primaryProfession IS NOT NULL AND trim(json_each.value) <> '';
