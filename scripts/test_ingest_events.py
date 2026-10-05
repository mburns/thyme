#!/usr/bin/env python3
"""Tests for the timeline ingest: schema, adapters and re-sync behaviour.

Run from the repository root:
    python3 scripts/test_ingest_events.py
"""

from __future__ import annotations

import logging
import os
import sqlite3
import tempfile
import textwrap
import unittest
from pathlib import Path

from ingest import SOURCES, Source, Syncer

# The failure test deliberately triggers an exception log.
logging.disable(logging.CRITICAL)

REPO = Path(__file__).resolve().parent.parent
MIGRATIONS = sorted((REPO / "traildepot" / "migrations").glob("U*.sql"))

PEOPLE = """\
ID,playerID,birthYear,birthMonth,birthDay,birthCity,birthCountry,birthState,deathYear,deathMonth,deathDay,deathCountry,deathState,deathCity,nameFirst,nameLast,nameGiven,weight,height,bats,throws,debut,bbrefID,finalGame,retroID
1,aaronha01,1934,2,5,Mobile,USA,AL,2021,1,22,USA,GA,Atlanta,Hank,Aaron,Henry Louis,180,72,R,R,1954-04-13,aaronha01,1976-10-03,aaroh101
2,ohtansh01,1994,7,5,Oshu,Japan,,,,,,,,Shohei,Ohtani,Shohei,210,76,L,R,2018-03-29,ohtansh01,,ohtas001
"""
AWARDS = """\
playerID,awardID,yearID,lgID,tie,notes
aaronha01,Gold Glove,1958,NL,,RF
nobody01,Gold Glove,1999,AL,,
"""
HOF = """\
playerID,yearid,votedBy,ballots,needed,votes,inducted,category,needed_note
aaronha01,1982,BBWAA,415,312,406,Y,Player,
ohtansh01,2040,BBWAA,,,,N,Player,
"""
ALLSTAR = """\
playerID,yearID,gameNum,gameID,teamID,lgID,GP,startingPos
aaronha01,1955,0,NLS195507120,ML1,NL,1,
"""
TEAMS = """\
yearID,lgID,teamID,franchID,divID,Rank,G,Ghome,W,L,DivWin,WCWin,LgWin,WSWin,R,AB,H,2B,3B,HR,BB,SO,SB,CS,HBP,SF,RA,ER,ERA,CG,SHO,SV,IPouts,HA,HRA,BBA,SOA,E,DP,FP,name,park,attendance,BPF,PPF,teamIDBR,teamIDlahman45,teamIDretro
1957,NL,ML1,ATL,,1,155,,95,59,,,Y,Y,,,,,,,,,,,,,,,,,,,,,,,,,,Milwaukee Braves,County Stadium,,,,,,
2024,NL,ATL,ATL,E,2,162,,89,73,N,Y,N,N,,,,,,,,,,,,,,,,,,,,,,,,,,Atlanta Braves,Truist Park,,,,,,
"""
FRANCHISES = """\
franchID,franchName,active,NAassoc
ATL,Atlanta Braves,Y,
"""
OLYMPICS = """\
"ID","Name","Sex","Age","Height","Weight","Team","NOC","Games","Year","Season","City","Sport","Event","Medal"
"1","A Dijiang","M",24,180,80,"China","CHN","1992 Summer",1992,"Summer","Barcelona","Basketball","Basketball Men's Basketball",NA
"2","Carl Lewis","M",23,188,80,"United States","USA","1984 Summer",1984,"Summer","Los Angeles","Athletics","Athletics Men's 100 metres","Gold"
"2","Carl Lewis","M",23,188,80,"United States","USA","1984 Summer",1984,"Summer","Los Angeles","Athletics","Athletics Men's Long Jump","Gold"
"""
WIKI = """\
Id,Name,Short description,Gender,Country,Occupation,Birth year,Death year,Manner of death,Age of death
Q23,George Washington,1st president of the United States,Male,United States of America,Politician,1732,1799,natural causes,67
Q868,Aristotle,Greek philosopher,Male,Greece,Philosopher,-384,-322,,62
Q42,Douglas Adams,English writer,Male,United Kingdom,Artist,1952,2001,natural causes,49
"""


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


def make_db(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    for migration in MIGRATIONS:
        conn.executescript(migration.read_text(encoding="utf-8"))
    conn.commit()
    return conn


class IngestTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.data = root / "data"
        base = self.data / "sports" / "baseball"
        write(base / "People.csv", PEOPLE)
        write(base / "AwardsPlayers.csv", AWARDS)
        write(base / "HallOfFame.csv", HOF)
        write(base / "AllstarFull.csv", ALLSTAR)
        write(base / "Teams.csv", TEAMS)
        write(base / "TeamsFranchises.csv", FRANCHISES)
        write(
            base / "readme2024u.txt",
            "The SABR Lahman Baseball Database 1871-2024\nRelease Date: Oct 30, 2025\n",
        )
        write(self.data / "sports" / "olympic_events" / "athlete_events.csv", OLYMPICS)
        write(self.data / "wiki" / "AgeDataset-V1.csv", WIKI)
        self.conn = make_db(root / "main.db")
        self.conn.executescript(
            """
            INSERT INTO titles (id, tconst, titleType, primaryTitle, startYear, endYear, genres)
            VALUES (1, 'tt0068646', 'movie', 'The Godfather', 1972, NULL, 'Crime,Drama'),
                   (2, 'tt0098904', 'tvSeries', 'Seinfeld', 1989, 1998, 'Comedy'),
                   (3, 'tt9999999', 'movie', 'Obscure', 2001, NULL, NULL);
            INSERT INTO ratings VALUES (1, 9.2, 2000000), (2, 8.9, 350000), (3, 5.0, 12);
            INSERT INTO persons (id, nconst, primaryName, birthYear, deathYear, primaryProfession)
            VALUES (1, 'nm0000008', 'Marlon Brando', 1924, 2004, 'actor,director'),
                   (2, 'nm0000001', 'Nameless', NULL, NULL, 'actor');
            """
        )
        self.conn.commit()
        self.syncer = Syncer(self.conn, self.data)

    def tearDown(self) -> None:
        self.conn.close()
        self.tmp.cleanup()

    def count(self, sql: str, *params: object) -> int:
        return int(self.conn.execute(sql, params).fetchone()[0])

    def events_for(self, slug: str) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT kind, COUNT(*) FROM v_events WHERE source = ? GROUP BY kind",
            (slug,),
        ).fetchall()
        return {k: n for k, n in rows}

    def sync_all(self) -> dict[str, str]:
        return {slug: self.syncer.sync(src).status for slug, src in SOURCES.items()}

    def test_initial_sync_loads_every_source(self) -> None:
        self.assertEqual(self.sync_all(), {s: "ok" for s in SOURCES})

        self.assertEqual(
            self.events_for("lahman"),
            {
                "life": 2,
                "career": 2,
                "award": 1,
                "hall_of_fame": 1,
                "all_star": 1,
                "championship": 1,
                "run": 1,
            },
        )
        self.assertEqual(
            self.events_for("olympics"), {"games": 2, "competed": 2, "medal": 2}
        )
        self.assertEqual(self.events_for("wikidata_age"), {"life": 3})
        # Titles under the vote threshold and people without a birth year are left out.
        self.assertEqual(self.events_for("imdb"), {"release": 1, "run": 1, "life": 1})

    def test_dates_and_precision(self) -> None:
        self.sync_all()
        row = self.conn.execute(
            "SELECT start_date, end_date, precision, start_year, end_year "
            "FROM v_events WHERE source = 'lahman' AND kind = 'life' AND entity_name = 'Hank Aaron'"
        ).fetchone()
        self.assertEqual(row, ("1934-02-05", "2021-01-22", "day", 1934, 2021))
        row = self.conn.execute(
            "SELECT start_date, end_date, start_year FROM v_events WHERE entity_name = 'Aristotle'"
        ).fetchone()
        self.assertEqual(row, ("-0384", "-0322", -384))
        row = self.conn.execute(
            "SELECT end_date, end_year FROM v_events WHERE kind = 'career' AND entity_name = 'Shohei Ohtani'"
        ).fetchone()
        self.assertEqual(row, (None, None))

    def test_events_for_unknown_entities_are_skipped(self) -> None:
        result = self.syncer.sync(SOURCES["lahman"])
        self.assertIn("1 skipped (unknown entity)", result.message)
        self.assertEqual(
            self.count(
                "SELECT COUNT(*) FROM events WHERE external_id LIKE 'nobody01%'"
            ),
            0,
        )

    def test_entities_are_searchable_and_linked(self) -> None:
        self.sync_all()
        hit = self.conn.execute(
            "SELECT e.wikidata_id, e.url FROM entities_fts f JOIN entities e ON e.id = f.rowid "
            "WHERE entities_fts MATCH '\"washing\"*'"
        ).fetchone()
        self.assertEqual(hit, ("Q23", "https://www.wikidata.org/wiki/Q23"))

    def test_unchanged_source_is_skipped(self) -> None:
        self.assertEqual(self.syncer.sync(SOURCES["olympics"]).status, "ok")
        self.assertEqual(self.syncer.sync(SOURCES["olympics"]).status, "unchanged")
        self.assertEqual(self.syncer.sync(SOURCES["olympics"], force=True).status, "ok")
        self.assertEqual(
            self.count("SELECT COUNT(*) FROM source_syncs WHERE status = 'ok'"), 2
        )

    def test_changed_file_updates_and_removes_rows(self) -> None:
        self.syncer.sync(SOURCES["wikidata_age"])
        path = self.data / "wiki" / "AgeDataset-V1.csv"
        lines = path.read_text(encoding="utf-8").splitlines()
        lines = [
            ln.replace("Douglas Adams", "Douglas N. Adams")
            for ln in lines
            if "Q868" not in ln
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.utime(path, (path.stat().st_atime, path.stat().st_mtime + 10))

        self.assertTrue(self.syncer.status(SOURCES["wikidata_age"])["changed"])
        result = self.syncer.sync(SOURCES["wikidata_age"])
        self.assertEqual((result.status, result.events_deleted), ("ok", 1))
        self.assertEqual(
            self.count("SELECT COUNT(*) FROM entities WHERE name = 'Aristotle'"), 0
        )
        self.assertEqual(
            self.count("SELECT COUNT(*) FROM entities WHERE name = 'Douglas N. Adams'"),
            1,
        )
        self.assertEqual(
            self.count(
                "SELECT COUNT(*) FROM events WHERE source_id = (SELECT id FROM sources WHERE slug = 'wikidata_age')"
            ),
            2,
        )
        self.assertFalse(self.syncer.status(SOURCES["wikidata_age"])["changed"])

    def test_failure_is_recorded_and_leaves_no_rows(self) -> None:
        class Broken(Source):
            slug = "broken"
            name = "Broken"
            kind = "derived"

            def load(self, ctx: object) -> None:
                ctx.conn.execute(
                    "INSERT INTO stage_entities VALUES ('x', 'person', 'X', NULL, NULL, NULL)"
                )
                raise RuntimeError("boom")

        result = self.syncer.sync(Broken())
        self.assertEqual(result.status, "failed")
        self.assertEqual(
            self.conn.execute("SELECT status, message FROM source_syncs").fetchone(),
            ("failed", "RuntimeError: boom"),
        )
        self.assertEqual(self.count("SELECT COUNT(*) FROM entities"), 0)

    def test_missing_files_are_reported(self) -> None:
        empty = Syncer(self.conn, Path(self.tmp.name) / "nowhere")
        self.assertEqual(empty.sync(SOURCES["lahman"]).status, "missing")

    def test_version_labels(self) -> None:
        self.syncer.sync(SOURCES["lahman"])
        version = self.conn.execute(
            "SELECT version FROM source_syncs WHERE status = 'ok'"
        ).fetchone()[0]
        self.assertEqual(version, "Lahman 1871-2024, Oct 30, 2025")


if __name__ == "__main__":
    unittest.main()
