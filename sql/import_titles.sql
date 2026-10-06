-- Import titles from temp table to final table
INSERT INTO titles (tconst, titleType, primaryTitle, originalTitle, isAdult, startYear, endYear, runtimeMinutes, genres)
SELECT 
    tconst,
    NULLIF(titleType, '\N'),
    NULLIF(primaryTitle, '\N'),
    NULLIF(originalTitle, '\N'),
    CASE WHEN isAdult = '1' THEN 1 WHEN isAdult = '0' THEN 0 ELSE NULL END,
    CASE WHEN startYear = '\N' THEN NULL ELSE CAST(startYear AS INTEGER) END,
    CASE WHEN endYear = '\N' THEN NULL ELSE CAST(endYear AS INTEGER) END,
    CASE WHEN runtimeMinutes = '\N' THEN NULL ELSE CAST(runtimeMinutes AS INTEGER) END,
    NULLIF(genres, '\N')
FROM t_title_basics; 