import sqlite3
import csv
import gzip
import os

DATA_DIR = "data"
DB_PATH = os.path.join("traildepot", "data", "main.db")
BATCH_SIZE = 50000

# In-memory maps for string IDs to integer PKs
title_id_map = {}
person_id_map = {}


def to_int(value):
    """Safely convert to integer, returning None for '\\N' or errors."""
    if value == "\\N":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def to_float(value):
    """Safely convert to float, returning None for '\\N' or errors."""
    if value == "\\N":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def import_titles(conn):
    """Import titles and populate the title_id_map."""
    print("Importing titles...")
    filepath = os.path.join(DATA_DIR, "title.basics.tsv.gz")
    cursor = conn.cursor()
    sql = "INSERT INTO titles (tconst, titleType, primaryTitle, originalTitle, isAdult, startYear, endYear, runtimeMinutes, genres) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"

    with gzip.open(filepath, "rt", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="	", quoting=csv.QUOTE_NONE)
        next(reader)  # Skip header

        batch = []
        for row in reader:
            try:
                tconst = row[0]
                values = (
                    tconst,
                    row[1] if row[1] != "\\N" else None,  # titleType
                    row[2] if row[2] != "\\N" else None,  # primaryTitle
                    row[3] if row[3] != "\\N" else None,  # originalTitle
                    to_int(row[4]),  # isAdult
                    to_int(row[5]),  # startYear
                    to_int(row[6]),  # endYear
                    to_int(row[7]),  # runtimeMinutes
                    row[8] if row[8] != "\\N" else None,  # genres
                )
                batch.append(values)
                if len(batch) >= BATCH_SIZE:
                    cursor.executemany(sql, batch)
                    batch = []
            except IndexError as e:
                print(f"Skipping row in titles due to error: {e} | Row: {row}")
                continue

        if batch:
            cursor.executemany(sql, batch)

    conn.commit()

    # After inserting all titles, we need to populate the id map
    print("Building title ID map...")
    cursor.execute("SELECT id, tconst FROM titles")
    for row in cursor.fetchall():
        title_id_map[row[1]] = row[0]
    print(f"Finished importing titles. {len(title_id_map)} titles mapped.")


def import_persons(conn):
    """Import persons and populate the person_id_map."""
    print("Importing persons...")
    filepath = os.path.join(DATA_DIR, "name.basics.tsv.gz")
    cursor = conn.cursor()
    sql = "INSERT INTO persons (nconst, primaryName, birthYear, deathYear, primaryProfession) VALUES (?, ?, ?, ?, ?);"

    with gzip.open(filepath, "rt", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="	", quoting=csv.QUOTE_NONE)
        next(reader)  # Skip header

        batch = []
        for row in reader:
            try:
                nconst = row[0]
                values = (
                    nconst,
                    row[1] if row[1] != "\\N" else None,  # primaryName
                    to_int(row[2]),  # birthYear
                    to_int(row[3]),  # deathYear
                    row[4] if row[4] != "\\N" else None,  # primaryProfession
                )
                batch.append(values)

                if len(batch) >= BATCH_SIZE:
                    cursor.executemany(sql, batch)
                    batch = []

            except IndexError as e:
                print(f"Skipping row in persons due to error: {e} | Row: {row}")
                continue
        if batch:
            cursor.executemany(sql, batch)

    conn.commit()

    print("Building person ID map...")
    cursor.execute("SELECT id, nconst FROM persons")
    for row in cursor.fetchall():
        person_id_map[row[1]] = row[0]
    print(f"Finished importing persons. {len(person_id_map)} persons mapped.")


def import_related_data(conn):
    """Import all data that depends on titles and persons."""
    print("Importing related data...")
    cursor = conn.cursor()

    # Import Principals
    print(" - principals")
    with gzip.open(
        os.path.join(DATA_DIR, "title.principals.tsv.gz"), "rt", encoding="utf-8"
    ) as f:
        reader = csv.reader(f, delimiter="	", quoting=csv.QUOTE_NONE)
        next(reader)
        batch = []
        sql = "INSERT INTO principals (title_id, person_id, ordering, category, job, characters) VALUES (?, ?, ?, ?, ?, ?);"
        for row in reader:
            tconst, nconst = row[0], row[2]
            title_id = title_id_map.get(tconst)
            person_id = person_id_map.get(nconst)
            if title_id and person_id:
                characters = row[5] if row[5] != "\\N" else None
                job = row[4] if row[4] != "\\N" else None
                batch.append(
                    (title_id, person_id, to_int(row[1]), row[3], job, characters)
                )
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(sql, batch)
                batch = []
        cursor.executemany(sql, batch)
    conn.commit()

    # Import Crew
    print(" - crew")
    with gzip.open(
        os.path.join(DATA_DIR, "title.crew.tsv.gz"), "rt", encoding="utf-8"
    ) as f:
        reader = csv.reader(f, delimiter="	", quoting=csv.QUOTE_NONE)
        next(reader)
        batch = []
        sql = "INSERT INTO crew (title_id, person_id, role) VALUES (?, ?, ?);"
        for row in reader:
            tconst = row[0]
            title_id = title_id_map.get(tconst)
            if not title_id:
                continue

            for role, nconsts in [("director", row[1]), ("writer", row[2])]:
                if nconsts == "\\N":
                    continue
                for nconst in nconsts.split(","):
                    person_id = person_id_map.get(nconst)
                    if person_id:
                        batch.append((title_id, person_id, role))
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(sql, batch)
                batch = []
        cursor.executemany(sql, batch)
    conn.commit()

    # Import Ratings
    print(" - ratings")
    with gzip.open(
        os.path.join(DATA_DIR, "title.ratings.tsv.gz"), "rt", encoding="utf-8"
    ) as f:
        reader = csv.reader(f, delimiter="	", quoting=csv.QUOTE_NONE)
        next(reader)
        batch = []
        sql = (
            "INSERT INTO ratings (title_id, averageRating, numVotes) VALUES (?, ?, ?);"
        )
        for row in reader:
            tconst = row[0]
            title_id = title_id_map.get(tconst)
            if title_id:
                batch.append((title_id, to_float(row[1]), to_int(row[2])))
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(sql, batch)
                batch = []
        cursor.executemany(sql, batch)
    conn.commit()

    # Import Episodes
    print(" - episodes")
    with gzip.open(
        os.path.join(DATA_DIR, "title.episode.tsv.gz"), "rt", encoding="utf-8"
    ) as f:
        reader = csv.reader(f, delimiter="	", quoting=csv.QUOTE_NONE)
        next(reader)
        batch = []
        sql = "INSERT INTO episodes (title_id, parent_title_id, seasonNumber, episodeNumber) VALUES (?, ?, ?, ?);"
        for row in reader:
            tconst, parent_tconst = row[0], row[1]
            title_id = title_id_map.get(tconst)
            parent_id = title_id_map.get(parent_tconst)
            if title_id and parent_id:
                batch.append((title_id, parent_id, to_int(row[2]), to_int(row[3])))
            if len(batch) >= BATCH_SIZE:
                cursor.executemany(sql, batch)
                batch = []
        cursor.executemany(sql, batch)
    conn.commit()


def create_views(conn):
    """Create all necessary views, bypassing the TrailBase migrator."""
    print("Creating views...")
    cursor = conn.cursor()

    views = {
        "v_title_details": """
            CREATE VIEW v_title_details AS
            SELECT
              t.id, t.tconst, t.titleType, t.primaryTitle, t.originalTitle,
              t.isAdult, t.startYear, t.endYear, t.runtimeMinutes, t.genres,
              r.averageRating, r.numVotes
            FROM titles t
            LEFT JOIN ratings r ON t.id = r.title_id
        """,
        "v_title_principals": """
            CREATE VIEW v_title_principals AS
            SELECT
              p.title_id, p.ordering, p.category, p.job, p.characters,
              pers.id as person_id, pers.nconst, pers.primaryName,
              pers.birthYear, pers.deathYear
            FROM principals p
            JOIN persons pers ON p.person_id = pers.id
        """,
        "v_person_titles": """
            CREATE VIEW v_person_titles AS
            SELECT
              p.person_id, p.category, p.job, p.characters,
              t.id as title_id, t.tconst, t.primaryTitle, t.titleType, t.startYear
            FROM principals p
            JOIN titles t ON p.title_id = t.id
        """,
        "v_title_episodes": """
            CREATE VIEW v_title_episodes AS
            SELECT
              e.parent_title_id, e.seasonNumber, e.episodeNumber,
              t.id as episode_title_id, t.tconst as episode_tconst,
              t.primaryTitle as episode_title, t.startYear as episode_year,
              t.runtimeMinutes as episode_runtime
            FROM episodes e
            JOIN titles t ON e.title_id = t.id
            ORDER BY e.seasonNumber, e.episodeNumber
        """,
        "v_genre_summary": """
            CREATE VIEW v_genre_summary AS
            WITH RECURSIVE split(title_id, genre, rest) AS (
              SELECT
                id,
                TRIM(SUBSTR(genres, 1, INSTR(genres || ',', ',') - 1)),
                SUBSTR(genres, INSTR(genres || ',', ',') + 1)
              FROM titles
              WHERE genres IS NOT NULL AND genres != ''
              UNION ALL
              SELECT
                title_id,
                TRIM(SUBSTR(rest, 1, INSTR(rest || ',', ',') - 1)),
                SUBSTR(rest, INSTR(rest || ',', ',') + 1)
              FROM split
              WHERE rest != ''
            )
            SELECT genre, COUNT(*) as title_count
            FROM split
            WHERE genre != ''
            GROUP BY genre
            ORDER BY title_count DESC
        """,
    }

    for name, sql in views.items():
        try:
            print(f" - Creating view: {name}")
            cursor.execute(f"DROP VIEW IF EXISTS {name};")
            cursor.execute(sql)
        except sqlite3.Error as e:
            print(f"Could not create view {name}: {e}")

    conn.commit()
    print("Finished creating views.")


def main():
    # if os.path.exists(DB_PATH):
    #     os.remove(DB_PATH)
    #     print(f"Removed existing database: {DB_PATH}")

    # We must connect to a DB file that does not exist, so TrailBase can init it.
    # But we can't do that, so we have to run TrailBase first to create it.
    # The user must ensure the DB is created by TrailBase but empty.
    # if not os.path.exists(os.path.dirname(DB_PATH)):
    #     os.makedirs(os.path.dirname(DB_PATH))

    # Hack: create a dummy file so TrailBase can find and open it.
    # The server will initialize it. Let's not do that. The user must create it.

    if not os.path.exists(DB_PATH):
        print(f"Error: Database file not found at {DB_PATH}")
        print(
            "Please run the TrailBase server once to create the database, then stop it and run this script."
        )
        return

    with sqlite3.connect(DB_PATH) as conn:
        print(f"Successfully connected to database: {DB_PATH}")
        import_titles(conn)
        import_persons(conn)
        import_related_data(conn)
        # create_views(conn)

    print("\nDatabase import complete!")


if __name__ == "__main__":
    main()
