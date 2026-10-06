-- Import principals from temp table to final table
INSERT INTO principals (title_id, person_id, ordering, category, job, characters)
SELECT 
    t.id,
    p.id,
    CASE WHEN tp.ordering = '\N' THEN NULL ELSE CAST(tp.ordering AS INTEGER) END,
    tp.category,
    NULLIF(tp.job, '\N'),
    NULLIF(tp.characters, '\N')
FROM t_title_principals tp
JOIN titles t ON tp.tconst = t.tconst
JOIN persons p ON tp.nconst = p.nconst; 