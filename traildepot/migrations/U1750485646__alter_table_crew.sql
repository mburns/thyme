PRAGMA foreign_keys = OFF;

CREATE TABLE "__alter_table_crew" (
    'id' INTEGER PRIMARY KEY,
    'title_id' INTEGER NOT NULL REFERENCES 'titles'('id'),
    'person_id' INTEGER NOT NULL REFERENCES 'persons'('id'),
    'role' TEXT DEFAULT '' NOT NULL,
    UNIQUE ('title_id', 'person_id', 'role')
) STRICT;

INSERT INTO
    "__alter_table_crew" (id, title_id, person_id, role)
SELECT
    id,
    title_id,
    person_id,
    role
FROM
    "crew";

DROP TABLE "crew";

ALTER TABLE
    "__alter_table_crew" RENAME TO "crew";

PRAGMA foreign_keys = ON;