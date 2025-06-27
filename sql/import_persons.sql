-- Import persons from temp table to final table
INSERT INTO persons (nconst, primaryName, birthYear, deathYear, primaryProfession)
SELECT 
    nconst,
    NULLIF(primaryName, '\N'),
    CASE WHEN birthYear = '\N' THEN NULL ELSE CAST(birthYear AS INTEGER) END,
    CASE WHEN deathYear = '\N' THEN NULL ELSE CAST(deathYear AS INTEGER) END,
    NULLIF(primaryProfession, '\N')
FROM t_name_basics; 