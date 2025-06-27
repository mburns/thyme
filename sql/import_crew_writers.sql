-- Import writers from temp table to final table
WITH RECURSIVE writer_split(tconst, nconst, rest) AS (
    SELECT 
        tconst,
        TRIM(SUBSTR(writers, 1, CASE WHEN INSTR(writers, ',') = 0 THEN LENGTH(writers) ELSE INSTR(writers, ',') - 1 END)),
        CASE WHEN INSTR(writers, ',') = 0 THEN '' ELSE TRIM(SUBSTR(writers, INSTR(writers, ',') + 1)) END
    FROM t_title_crew
    WHERE writers != '\N' AND writers != ''
    
    UNION ALL
    
    SELECT 
        tconst,
        TRIM(SUBSTR(rest, 1, CASE WHEN INSTR(rest, ',') = 0 THEN LENGTH(rest) ELSE INSTR(rest, ',') - 1 END)),
        CASE WHEN INSTR(rest, ',') = 0 THEN '' ELSE TRIM(SUBSTR(rest, INSTR(rest, ',') + 1)) END
    FROM writer_split
    WHERE rest != ''
)
INSERT INTO crew (title_id, person_id, role)
SELECT DISTINCT t.id, p.id, 'writer'
FROM writer_split ws
JOIN titles t ON ws.tconst = t.tconst
JOIN persons p ON ws.nconst = p.nconst
WHERE ws.nconst != ''; 