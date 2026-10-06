-- Import ratings from temp table to final table
INSERT INTO ratings (title_id, averageRating, numVotes)
SELECT 
    t.id,
    CASE WHEN tr.averageRating = '\N' THEN NULL ELSE CAST(tr.averageRating AS REAL) END,
    CASE WHEN tr.numVotes = '\N' THEN NULL ELSE CAST(tr.numVotes AS INTEGER) END
FROM t_title_ratings tr
JOIN titles t ON tr.tconst = t.tconst; 