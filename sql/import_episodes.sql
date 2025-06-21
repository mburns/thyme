-- Import episodes from temp table to final table
INSERT INTO episodes (title_id, parent_title_id, seasonNumber, episodeNumber)
SELECT 
    t.id,
    pt.id,
    CASE WHEN te.seasonNumber = '\N' THEN NULL ELSE CAST(te.seasonNumber AS INTEGER) END,
    CASE WHEN te.episodeNumber = '\N' THEN NULL ELSE CAST(te.episodeNumber AS INTEGER) END
FROM t_title_episode te
JOIN titles t ON te.tconst = t.tconst
JOIN titles pt ON te.parentTconst = pt.tconst; 