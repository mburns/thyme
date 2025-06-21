-- Import directors from temp table to final table
WITH RECURSIVE director_split(tconst, nconst, rest) AS (
    SELECT 
        tconst,
        TRIM(SUBSTR(directors, 1, CASE WHEN INSTR(directors, ',') = 0 THEN LENGTH(directors) ELSE INSTR(directors, ',') - 1 END)),
        CASE WHEN INSTR(directors, ',') = 0 THEN '' ELSE TRIM(SUBSTR(directors, INSTR(directors, ',') + 1)) END
    FROM t_title_crew
    WHERE directors != '\N' AND directors != ''
    
    UNION ALL
    
    SELECT 
        tconst,
        TRIM(SUBSTR(rest, 1, CASE WHEN INSTR(rest, ',') = 0 THEN LENGTH(rest) ELSE INSTR(rest, ',') - 1 END)),
        CASE WHEN INSTR(rest, ',') = 0 THEN '' ELSE TRIM(SUBSTR(rest, INSTR(rest, ',') + 1)) END
    FROM director_split
    WHERE rest != ''
)
INSERT INTO crew (title_id, person_id, role)
SELECT DISTINCT t.id, p.id, 'director'
FROM director_split ds
JOIN titles t ON ds.tconst = t.tconst
JOIN persons p ON ds.nconst = p.nconst
WHERE ds.nconst != ''; 