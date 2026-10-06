#!/usr/bin/env python3
"""Tests for the timeline ingest: schema, adapters, re-sync behaviour,
SQLite features, density, participants and entity linking.

Run from the repository root:
    python3 scripts/test_ingest_events.py
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import sqlite3
import tempfile
import textwrap
import unittest
from pathlib import Path

import wikidata_extract
from ingest import SOURCES, Source, Syncer

# The failure test deliberately triggers an exception log.
logging.disable(logging.CRITICAL)

REPO = Path(__file__).resolve().parent.parent
MIGRATIONS = sorted((REPO / "traildepot" / "migrations").glob("U*.sql"))
# Eleven real entities in dump format: Brando, Aaron, Washington, Aristotle,
# World War II, the Nobel Prize in Literature, the Academy Award for Best
# Actor, the United States, and three items only referred to.
WIKIDATA_DUMP = REPO / "scripts" / "fixtures" / "wikidata-mini-dump.json"

PEOPLE = """\
ID,playerID,birthYear,birthMonth,birthDay,birthCity,birthCountry,birthState,deathYear,deathMonth,deathDay,deathCountry,deathState,deathCity,nameFirst,nameLast,nameGiven,weight,height,bats,throws,debut,bbrefID,finalGame,retroID
1,aaronha01,1934,2,5,Mobile,USA,AL,2021,1,22,USA,GA,Atlanta,Hank,Aaron,Henry Louis,180,72,R,R,1954-04-13,aaronha01,1976-10-03,aaroh101
2,ohtansh01,1994,7,5,Oshu,Japan,,,,,,,,Shohei,Ohtani,Shohei,210,76,L,R,2018-03-29,ohtansh01,,ohtas001
3,mathed01,1931,10,13,Texarkana,USA,TX,2001,2,18,USA,CA,La Jolla,Eddie,Mathews,Edwin Lee,190,73,L,R,1952-04-15,mathed01,1968-10-10,mathe101
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
APPEARANCES = """\
yearID,teamID,lgID,playerID,G_all,GS,G_batting,G_defense,G_p,G_c,G_1b,G_2b,G_3b,G_ss,G_lf,G_cf,G_rf,G_of,G_dh,G_ph,G_pr
1957,ML1,NL,aaronha01,151,,151,151,0,0,0,0,0,0,0,0,0,151,0,0,0
1957,ML1,NL,mathed01,148,,148,148,0,0,0,0,148,0,0,0,0,0,0,0,0
2024,ATL,NL,ohtansh01,1,,1,1,0,0,0,0,0,0,0,0,0,0,1,0,0
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
Q215777,Hank Aaron,American baseball player,Male,United States of America,Athlete,1934,2021,natural causes,86
Q34012,Marlon Brando,American actor,Male,United States of America,Artist,1924,2004,natural causes,80
Q1,John Smith,English soldier,Male,England,Explorer,1580,1631,,51
Q2,John Smith,Another John Smith,Male,England,Explorer,1580,1631,,51
"""
NBA_PLAYERS = """\
person_id,first_name,last_name,display_first_last,birthdate,school,country,position,season_exp,team_name,from_year,to_year,draft_year,draft_round,draft_number
76001,Alaa,Abdelnaby,Alaa Abdelnaby,1968-06-24 00:00:00,Duke,USA,Forward,5.0,Trail Blazers,1990.0,1994.0,1990,1,25
893,Michael,Jordan,Michael Jordan,1963-02-17 00:00:00,North Carolina,USA,Guard,15.0,Wizards,1984.0,2002.0,1984,1,3
999,Nobody,Undated,Nobody Undated,,,,Center,,,,,,,
"""
NBA_DRAFT = """\
person_id,player_name,season,round_number,round_pick,overall_pick,draft_type,team_id,team_city,team_name,team_abbreviation,organization,organization_type,player_profile_flag
893,Michael Jordan,1984,1,3,3,Draft,1610612741,Chicago,Bulls,CHI,North Carolina,College/University,1
893,Michael Jordan,1984,1,3,3,Expansion Draft,1610612741,Chicago,Bulls,CHI,North Carolina,College/University,1
"""
NBA_GAMES = """\
season_id,team_id_home,team_abbreviation_home,team_name_home,game_id,game_date,matchup_home,wl_home,pts_home,team_id_away,team_abbreviation_away,team_name_away,pts_away,season_type
21946,1610610035,HUS,Toronto Huskies,0024600001,1946-11-01 00:00:00,HUS vs. NYK,L,66.0,1610612752,NYK,New York Knicks,68.0,Regular Season
41997,1610612741,CHI,Chicago Bulls,0049700086,1998-06-14 00:00:00,CHI @ UTA,W,87.0,1610612762,UTA,Utah Jazz,86.0,Playoffs
"""
NBA_TEAM_HISTORY = """\
team_id,city,nickname,year_founded,year_active_till
1610612741,Chicago,Bulls,1966,2019
1610610035,Toronto,Huskies,1946,1946
"""
MUSICBRAINZ = """\
artist_mbid,artist_name,release_mbid,release_title,date_year,date_month,date_day,release_group_type,country_code
c0b2500e-0cef-4130-869d-732b23ed9df5,Tori Amos,425cf29a-1490-43ab-abfa-7b17a2cec351,A Sorta Fairytale,2002,10,14,Single,DE
c0b2500e-0cef-4130-869d-732b23ed9df5,Tori Amos,b1b1b1b1-0000-0000-0000-000000000001,Little Earthquakes,1992,,,Album,GB
b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d,The Beatles,c2c2c2c2-0000-0000-0000-000000000002,Abbey Road,1969,9,26,Album,GB
b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d,The Beatles,d3d3d3d3-0000-0000-0000-000000000003,Undated,,,,Album,
b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d,The Beatles,e4e4e4e4-0000-0000-0000-000000000004,From the Future,3036,1,1,Album,
89ad4ac3-39f7-470e-963a-56509c546377,Various Artists,f5f5f5f5-0000-0000-0000-000000000005,Now That's What I Call Music,1983,11,28,Album,GB
"""
BX_BOOKS = """\
ISBN,Book-Title,Book-Author,Year-Of-Publication,Publisher,Image-URL-S,Image-URL-M,Image-URL-L
0195153448,Classical Mythology,Mark P. O. Morford,2002,Oxford University Press,,,
0002005018,Clara Callan,Richard Bruce Wright,2001,HarperFlamingo Canada,,,
0000000000,Undated Book,Nobody,0,Nowhere Press,,,
"""
STEAM = """\
appid,name,release_date,short_description,developers,publishers,genres,metacritic_score,estimated_owners,positive,negative
730,Counter-Strike 2,2012-08-21,A free upgrade to CS:GO.,Valve,Valve,"Action,Free To Play",83,100000000 - 200000000,7000000,1000000
999999,Unreleased,,Nothing yet.,Nobody,Nobody,,0,0 - 0,0,0
"""
PAINTERS = """\
artist_id,full_name,first_name,middle_names,last_name,nationality,style,birth,death
500,Pierre-Auguste Renoir,Pierre,Auguste,Renoir,French,Impressionist,1841,1919
"""
CRICKET_TESTS = """\
date,type,team1,team2
1877-03-15,Test,Australia,England
"""
CRICKET_ODIS = """\
date,type,team1,team2
2006-01-03,ODI,New Zealand,Sri Lanka
"""
CRICKET_T20I = """\
date,type,team1,team2
2007-09-11,T20I,South Africa,West Indies
"""
MLS = """\
﻿id,home,away,date,year,time (utc),attendance,venue,league,part_of_competition,game_status,shootout,home_score,away_score
,New England,San Jose,7/31/1996,1996,,"12,871",Foxboro Stadium,1996 MLS,Regular Season,FT,,2,0
"""
WIKIPEDIA_LIST = {
    "title": "Bibliography of Montana history",
    "pageid": 123,
    "revid": 456,
    "url": "https://en.wikipedia.org/wiki/Bibliography_of_Montana_history",
    "wikitext": (
        "* {{cite book |last=Malone |first=Michael P. |title=Montana: A History of Two "
        "Centuries |publisher=University of Washington Press |year=1991}}\n"
        "* Toole, K. Ross. ''Montana: An Uncommon Land''. Norman, 1959.\n"
        "* [[Lewis and Clark Expedition|The expedition]] reaches the Three Forks, 1805.\n"
    ),
}


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
        write(base / "Appearances.csv", APPEARANCES)
        write(
            base / "readme2024u.txt",
            "The SABR Lahman Baseball Database 1871-2024\nRelease Date: Oct 30, 2025\n",
        )
        write(self.data / "sports" / "olympic_events" / "athlete_events.csv", OLYMPICS)
        write(self.data / "wiki" / "AgeDataset-V1.csv", WIKI)
        nba = self.data / "sports" / "nba" / "csv"
        write(nba / "common_player_info.csv", NBA_PLAYERS)
        write(nba / "draft_history.csv", NBA_DRAFT)
        write(nba / "game.csv", NBA_GAMES)
        write(nba / "team_history.csv", NBA_TEAM_HISTORY)
        write(self.data / "music" / "official_releases.csv", MUSICBRAINZ)
        write(self.data / "books" / "BX-Books.csv", BX_BOOKS)
        write(self.data / "steam" / "games_march2025_cleaned.csv", STEAM)
        write(self.data / "art" / "artist.csv", PAINTERS)
        cricket = self.data / "sports" / "cricket"
        write(cricket / "tests.csv", CRICKET_TESTS)
        write(cricket / "odis.csv", CRICKET_ODIS)
        write(cricket / "t20i.csv", CRICKET_T20I)
        write(self.data / "sports" / "mls" / "matches.csv", MLS)
        lists = self.data / "wikipedia" / "lists"
        lists.mkdir(parents=True)
        (lists / "bibliography_of_montana_history.json").write_text(
            json.dumps(WIKIPEDIA_LIST), encoding="utf-8"
        )
        wikidata_extract.run(str(WIKIDATA_DUMP), self.data / "wikidata", None, 10**6)
        self.conn = make_db(root / "main.db")
        self.conn.executescript(
            """
            INSERT INTO titles (id, tconst, titleType, primaryTitle, startYear, endYear, genres)
            VALUES (1, 'tt0068646', 'movie', 'The Godfather', 1972, NULL, 'Crime,Drama'),
                   (2, 'tt0098904', 'tvSeries', 'Seinfeld', 1989, 1998, 'Comedy'),
                   (3, 'tt9999999', 'movie', 'Obscure', 2001, NULL, NULL),
                   (4, 'tt0697784', 'tvEpisode', 'The Contest', 1992, NULL, 'Comedy'),
                   (5, 'tt0098286', 'tvEpisode', 'The Seinfeld Chronicles', 1989, NULL, 'Comedy'),
                   (6, 'tt0000006', 'tvEpisode', 'Orphan Episode', 1995, NULL, NULL);
            INSERT INTO ratings VALUES (1, 9.2, 2000000), (2, 8.9, 350000), (3, 5.0, 12), (4, 9.4, 8000);
            INSERT INTO episodes (title_id, parent_title_id, seasonNumber, episodeNumber)
            VALUES (4, 2, 4, 11), (5, 2, 1, 1), (6, 3, 1, 1);
            INSERT INTO persons (id, nconst, primaryName, birthYear, deathYear, primaryProfession)
            VALUES (1, 'nm0000008', 'Marlon Brando', 1924, 2004, 'actor,director'),
                   (2, 'nm0000001', 'Nameless', NULL, NULL, 'actor'),
                   (3, 'nm0000338', 'Francis Ford Coppola', 1939, NULL, 'director'),
                   (4, 'nm0000002', 'Larry David', NULL, NULL, 'writer');
            INSERT INTO principals (title_id, person_id, ordering, category)
            VALUES (1, 1, 1, 'actor'), (1, 2, 2, 'actor'), (1, 3, 3, 'director'),
                   (4, 2, 1, 'actor');
            INSERT INTO crew (title_id, person_id, role)
            VALUES (4, 4, 'writer'), (1, 3, 'director');
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
                "life": 3,
                "career": 3,
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
        self.assertEqual(self.events_for("wikidata_age"), {"life": 7})
        # Titles under the vote threshold are left out, and with them their
        # episodes; people without a birth year have no life span.
        self.assertEqual(
            self.events_for("imdb"), {"release": 1, "run": 1, "life": 2, "episode": 2}
        )
        wikidata = self.events_for("wikidata")
        self.assertEqual(
            {k: v for k, v in wikidata.items() if k != "award"},
            {"life": 4, "conflict": 1, "exists": 1, "established": 1},
        )
        self.assertGreaterEqual(wikidata["award"], 1)
        # Declarative sources: the undated player and the expansion draft
        # row are filtered; the undated and year-3036 releases are skipped.
        self.assertEqual(
            self.events_for("nba"),
            {"life": 2, "career": 2, "draft": 1, "game": 2, "run": 2},
        )
        self.assertEqual(self.events_for("musicbrainz"), {"release": 3})
        # Year 0 is "unknown" in Book-Crossing and stays out.
        self.assertEqual(self.events_for("bx_books"), {"publication": 2})
        self.assertEqual(self.events_for("steam"), {"release": 1})
        self.assertEqual(self.events_for("paintings"), {"life": 1})
        self.assertEqual(self.events_for("cricket"), {"game": 3})
        self.assertEqual(self.events_for("mls"), {"game": 1})
        self.assertEqual(
            self.events_for("wikipedia_lists"), {"publication": 2, "listed": 1}
        )

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
            "WHERE entities_fts MATCH '\"washing\"'"
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


class SqliteFeaturesTest(IngestTest):
    """The span flag, the R*Tree interval index and the Julian-day columns."""

    def test_spans_are_flagged_and_open_ended_in_the_rtree(self) -> None:
        self.sync_all()
        rows = self.conn.execute(
            "SELECT kind, span FROM events WHERE kind IN ('life', 'career', 'run', "
            "'award', 'release') GROUP BY kind"
        ).fetchall()
        self.assertEqual(
            dict(rows), {"award": 0, "career": 1, "life": 1, "release": 0, "run": 1}
        )
        # Ohtani is still playing: his career extends to the open-end sentinel.
        end = self.conn.execute(
            "SELECT events_span.end_year FROM events_span JOIN events ON events.id = events_span.id "
            "WHERE events.external_id = 'ohtansh01:career'"
        ).fetchone()[0]
        self.assertEqual(end, 9999)
        # An instant occupies a single year.
        row = self.conn.execute(
            "SELECT start_year, end_year FROM events_span WHERE id = "
            "(SELECT id FROM events WHERE kind = 'hall_of_fame')"
        ).fetchone()
        self.assertEqual(row, (1982, 1982))

    def test_rtree_overlap_and_point_in_time(self) -> None:
        self.sync_all()
        alive_1960 = self.conn.execute(
            "SELECT DISTINCT entity_name FROM v_events JOIN events_span ON events_span.id = v_events.id "
            "WHERE events_span.start_year <= 1960 AND events_span.end_year >= 1960 "
            "AND v_events.kind = 'life' ORDER BY 1"
        ).fetchall()
        self.assertEqual(
            [r[0] for r in alive_1960],
            [
                "Douglas Adams",
                "Eddie Mathews",
                "Francis Ford Coppola",
                "Hank Aaron",
                "Marlon Brando",
            ],
        )
        self.assertEqual(
            self.count("SELECT COUNT(*) FROM events"),
            self.count("SELECT COUNT(*) FROM events_span"),
        )

    def test_rtree_follows_updates_and_deletes(self) -> None:
        self.syncer.sync(SOURCES["lahman"])
        before = self.count("SELECT COUNT(*) FROM events_span")
        self.conn.execute(
            "UPDATE events SET end_year = 2030, end_date = '2030' WHERE external_id = 'ohtansh01:career'"
        )
        end = self.conn.execute(
            "SELECT end_year FROM events_span WHERE id = (SELECT id FROM events WHERE external_id = 'ohtansh01:career')"
        ).fetchone()[0]
        self.assertEqual(end, 2030)
        self.conn.execute("DELETE FROM entities WHERE external_id = 'ohtansh01'")
        self.assertEqual(self.count("SELECT COUNT(*) FROM events_span"), before - 2)

    def test_julian_days_only_for_day_precision(self) -> None:
        self.sync_all()
        rows = self.conn.execute(
            "SELECT precision, start_julian IS NOT NULL, end_julian IS NOT NULL FROM events "
            "WHERE external_id IN ('aaronha01:life', 'Q23:life') AND source_id IN "
            "(SELECT id FROM sources WHERE slug IN ('lahman', 'wikidata_age')) ORDER BY precision"
        ).fetchall()
        self.assertEqual(rows, [("day", 1, 1), ("year", 0, 0)])
        days = self.conn.execute(
            "SELECT CAST(b.start_julian - a.start_julian AS INTEGER) FROM events a, events b "
            "WHERE a.external_id = 'aaronha01:life' AND b.external_id = 'aaronha01:career'"
        ).fetchone()[0]
        self.assertEqual(days, 7372)

    def test_trigram_substring_search(self) -> None:
        self.sync_all()
        hits = self.conn.execute(
            "SELECT DISTINCT entities.name FROM entities_fts JOIN entities ON entities.id = entities_fts.rowid "
            "WHERE entities_fts MATCH '\"ARISTO\"'"
        ).fetchall()
        self.assertEqual(hits, [("Aristotle",)])

    def test_genres_are_normalised(self) -> None:
        # The migration splits rows that already exist; the IMDB import runs
        # this same SQL after every load.
        self.conn.executescript(
            (REPO / "sql" / "import_genres.sql").read_text(encoding="utf-8")
        )
        rows = self.conn.execute(
            "SELECT genre, title_count FROM genres ORDER BY genre"
        ).fetchall()
        # Seinfeld and its two episodes are all Comedy.
        self.assertEqual(rows, [("Comedy", 3), ("Crime", 1), ("Drama", 1)])
        titles = self.conn.execute(
            "SELECT primaryTitle, numVotes FROM v_genre_titles WHERE genre = 'Drama'"
        ).fetchall()
        self.assertEqual(titles, [("The Godfather", 2000000)])
        professions = self.conn.execute(
            "SELECT profession FROM person_professions WHERE person_id = 1 ORDER BY 1"
        ).fetchall()
        self.assertEqual([p[0] for p in professions], ["actor", "director"])


class ScaleModelTest(IngestTest):
    """Density table, participants, certainty and entity links."""

    def test_density_is_precomputed_and_refreshed(self) -> None:
        self.sync_all()
        total = self.count("SELECT SUM(count) FROM event_density")
        self.assertEqual(total, self.count("SELECT COUNT(*) FROM events"))
        row = self.conn.execute(
            "SELECT count FROM event_density JOIN sources ON sources.id = source_id "
            "WHERE slug = 'lahman' AND category = 'baseball' AND year = 1957"
        ).fetchone()
        # 1957: the championship and the first season of the franchise run.
        self.assertEqual(row, (2,))
        # Re-syncing a source replaces its slice without touching others.
        self.syncer.sync(SOURCES["lahman"], force=True)
        self.assertEqual(
            self.count("SELECT SUM(count) FROM event_density"),
            self.count("SELECT COUNT(*) FROM events"),
        )

    def test_participants_from_rosters_and_cast(self) -> None:
        self.sync_all()
        roster = self.conn.execute(
            "SELECT entities.name, event_participants.role FROM event_participants "
            "JOIN events ON events.id = event_participants.event_id "
            "JOIN entities ON entities.id = event_participants.entity_id "
            "WHERE events.external_id = 'ATL:championship:1957' ORDER BY 1"
        ).fetchall()
        self.assertEqual(
            roster, [("Eddie Mathews", "player"), ("Hank Aaron", "player")]
        )
        cast = self.conn.execute(
            "SELECT entities.name, event_participants.role FROM event_participants "
            "JOIN events ON events.id = event_participants.event_id "
            "JOIN entities ON entities.id = event_participants.entity_id "
            "WHERE events.external_id = 'tt0068646:release' ORDER BY 1"
        ).fetchall()
        # 'Nameless' has no birth year but is credited, so is an entity with
        # no life span; the crew table adds nothing new for Coppola.
        self.assertEqual(
            cast,
            [
                ("Francis Ford Coppola", "director"),
                ("Marlon Brando", "actor"),
                ("Nameless", "actor"),
            ],
        )
        self.assertEqual(
            self.count(
                "SELECT COUNT(*) FROM events WHERE external_id = 'nm0000001:life'"
            ),
            0,
        )
        # Participants are rebuilt on every sync, never duplicated.
        self.syncer.sync(SOURCES["lahman"], force=True)
        self.assertEqual(
            self.count(
                "SELECT COUNT(*) FROM event_participants WHERE event_id = "
                "(SELECT id FROM events WHERE external_id = 'ATL:championship:1957')"
            ),
            2,
        )

    def test_episodes_sit_on_the_series_lane_with_their_credits(self) -> None:
        self.syncer.sync(SOURCES["imdb"])
        episodes = self.conn.execute(
            "SELECT label, start_year, entity_name, detail ->> 'season', detail ->> 'episode', "
            "detail ->> 'votes' FROM v_events WHERE kind = 'episode' ORDER BY start_year"
        ).fetchall()
        self.assertEqual(
            episodes,
            [
                ("The Seinfeld Chronicles", 1989, "Seinfeld", 1, 1, None),
                ("The Contest", 1992, "Seinfeld", 4, 11, 8000),
            ],
        )
        credits = self.conn.execute(
            "SELECT entities.name, event_participants.role FROM event_participants "
            "JOIN events ON events.id = event_participants.event_id "
            "JOIN entities ON entities.id = event_participants.entity_id "
            "WHERE events.external_id = 'tt0697784:episode' ORDER BY 1"
        ).fetchall()
        self.assertEqual(credits, [("Larry David", "writer"), ("Nameless", "actor")])
        # The episode's people exist as entities and carry IMDb ids for linking.
        self.assertEqual(
            self.conn.execute(
                "SELECT value FROM entity_identifiers JOIN entities ON entities.id = entity_id "
                "WHERE entities.name = 'Larry David'"
            ).fetchone(),
            ("nm0000002",),
        )

    def test_episodes_can_be_switched_off(self) -> None:
        result = self.syncer.sync(SOURCES["imdb"], options={"imdb_episodes": False})
        self.assertEqual(result.status, "ok")
        self.assertNotIn("episode", self.events_for("imdb"))
        self.assertEqual(
            self.count("SELECT COUNT(*) FROM entities WHERE name = 'Larry David'"), 0
        )

    def test_certainty_defaults_to_exact(self) -> None:
        self.sync_all()
        self.assertEqual(
            self.count("SELECT COUNT(*) FROM events WHERE certainty <> 'exact'"), 0
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("UPDATE events SET certainty = 'maybe' WHERE id = 1")

    def test_entities_link_across_sources(self) -> None:
        self.sync_all()
        links = self.syncer.link()
        # IMDB's Brando and Lahman's Aaron carry the ids Wikidata has (P345,
        # P1825); the Kaggle extract's rows share QIDs with the dump.
        self.assertEqual(
            (links.by_identifier, links.by_wikidata, links.by_name_dates), (2, 4, 0)
        )
        rows = self.conn.execute(
            "SELECT dup.name, src.slug, canon.wikidata_id, entity_links.method, entity_links.confidence "
            "FROM entity_links "
            "JOIN entities dup ON dup.id = entity_links.entity_id "
            "JOIN sources src ON src.id = dup.source_id "
            "JOIN entities canon ON canon.id = entity_links.canonical_id "
            "JOIN sources cs ON cs.id = canon.source_id "
            "WHERE src.slug IN ('imdb', 'lahman') AND cs.slug = 'wikidata' ORDER BY 1"
        ).fetchall()
        self.assertEqual(
            rows,
            [
                ("Hank Aaron", "lahman", "Q215777", "identifier", 1.0),
                ("Marlon Brando", "imdb", "Q34012", "identifier", 1.0),
            ],
        )

    def test_name_dates_fallback_when_only_the_kaggle_extract_is_loaded(self) -> None:
        for slug in ("lahman", "imdb", "wikidata_age"):
            self.syncer.sync(SOURCES[slug])
        links = self.syncer.link()
        self.assertEqual(
            (links.by_identifier, links.by_wikidata, links.by_name_dates), (0, 0, 2)
        )
        rows = self.conn.execute(
            "SELECT dup.name, src.slug, canon.wikidata_id, entity_links.method, entity_links.confidence "
            "FROM entity_links "
            "JOIN entities dup ON dup.id = entity_links.entity_id "
            "JOIN sources src ON src.id = dup.source_id "
            "JOIN entities canon ON canon.id = entity_links.canonical_id "
            "ORDER BY 1"
        ).fetchall()
        self.assertEqual(
            rows,
            [
                ("Hank Aaron", "lahman", "Q215777", "name_dates", 0.9),
                ("Marlon Brando", "imdb", "Q34012", "name_dates", 0.9),
            ],
        )
        # Two Wikidata John Smiths with identical dates are ambiguous and are
        # never used as a canonical target; living people (no death year)
        # are still linkable at lower confidence.
        self.assertEqual(
            self.count(
                "SELECT COUNT(*) FROM entity_links JOIN entities ON entities.id = canonical_id "
                "WHERE entities.name = 'John Smith'"
            ),
            0,
        )

    def test_link_is_idempotent_and_follows_deletions(self) -> None:
        self.sync_all()
        self.syncer.link()
        self.syncer.link()
        self.assertEqual(self.count("SELECT COUNT(*) FROM entity_links"), 6)
        self.conn.execute("DELETE FROM entities WHERE wikidata_id = 'Q215777'")
        self.assertEqual(self.count("SELECT COUNT(*) FROM entity_links"), 4)


class WikidataTest(IngestTest):
    """The dump extractor and the wikidata source on real entities."""

    def test_extract_keeps_selected_classes_and_all_labels(self) -> None:
        items = {
            json.loads(line)["id"]: json.loads(line)
            for line in gzip.open(self.data / "wikidata" / "items.jsonl.gz", "rt")
        }
        self.assertEqual(
            {q: i["kind"] for q, i in items.items()},
            {
                "Q34012": "person",
                "Q215777": "person",
                "Q23": "person",
                "Q868": "person",
                "Q362": "conflict",
                "Q37922": "award",
                "Q30": "country",
            },
        )
        # The Oscar category is not an instance of an award class, so it is
        # not selected as an item; people's P166 references still name it
        # through the labels file.
        self.assertEqual(items["Q34012"]["imdb"], "nm0000008")
        # Raw value; the adapter strips the letter directory to match Lahman.
        self.assertEqual(items["Q215777"]["bbref"], "a/aaronha01")
        self.assertEqual(items["Q868"]["birth"], {"year": -384, "julian": True})
        self.assertEqual(items["Q362"]["start"], {"year": 1939, "month": 9, "day": 1})
        labels = sum(
            1 for _ in gzip.open(self.data / "wikidata" / "labels.jsonl.gz", "rt")
        )
        self.assertEqual(labels, 11)

    def test_wikidata_events_participants_and_identifiers(self) -> None:
        self.syncer.sync(SOURCES["wikidata"])
        life = self.conn.execute(
            "SELECT start_date, end_date, precision, certainty, category FROM v_events "
            "WHERE source = 'wikidata' AND kind = 'life' AND entity_name = 'Marlon Brando'"
        ).fetchone()
        self.assertEqual(
            life, ("1924-04-03", "2004-07-01", "day", "exact", "film actor")
        )
        aristotle = self.conn.execute(
            "SELECT start_year, end_year, detail ->> 'julian' FROM v_events "
            "WHERE source = 'wikidata' AND entity_name = 'Aristotle'"
        ).fetchone()
        self.assertEqual(aristotle, (-384, -322, 1))
        war = self.conn.execute(
            "SELECT start_date, end_date, span FROM v_events WHERE kind = 'conflict'"
        ).fetchone()
        self.assertEqual(war, ("1939-09-01", "1945-09-02", 1))
        participants = self.conn.execute(
            "SELECT entities.kind, entities.name FROM event_participants "
            "JOIN events ON events.id = event_participants.event_id "
            "JOIN entities ON entities.id = event_participants.entity_id "
            "WHERE events.external_id = 'Q362:conflict' ORDER BY 2"
        ).fetchall()
        self.assertIn(("country", "United States"), participants)
        oscar = self.conn.execute(
            "SELECT events.label, events.start_year, entities.name FROM event_participants "
            "JOIN events ON events.id = event_participants.event_id "
            "JOIN entities ON entities.id = event_participants.entity_id "
            "WHERE events.kind = 'award' ORDER BY events.start_year LIMIT 1"
        ).fetchone()
        self.assertEqual(
            oscar,
            ("Academy Award for Best Actor", 1955, "Academy Award for Best Actor"),
        )
        ids = self.conn.execute(
            "SELECT scheme, value FROM entity_identifiers JOIN entities ON entities.id = entity_id "
            "WHERE entities.name = 'Hank Aaron' ORDER BY 1"
        ).fetchall()
        self.assertEqual(ids, [("bbref", "aaronha01"), ("imdb", "nm0007459")])
        url = self.conn.execute(
            "SELECT url FROM entities WHERE wikidata_id = 'Q362'"
        ).fetchone()[0]
        self.assertEqual(url, "https://en.wikipedia.org/wiki/World_War_II")


class CsvSourceTest(IngestTest):
    """Declarative TOML sources: NBA and MusicBrainz."""

    def test_templates_and_dates(self) -> None:
        from ingest.csvsource import parse_date, render

        self.assertEqual(render("{a|int}-{b}", {"a": "66.0", "b": "x"}), "66-x")
        self.assertEqual(parse_date("1968-06-24 00:00:00"), ("1968-06-24", "day", 1968))
        self.assertEqual(parse_date("1990.0"), ("1990", "year", 1990))
        self.assertEqual(parse_date("7/31/1996"), ("1996-07-31", "day", 1996))
        self.assertEqual(parse_date("1946-11"), ("1946-11", "month", 1946))
        self.assertIsNone(parse_date(""))
        self.assertIsNone(parse_date("n/a"))

    def test_nba_players_games_and_franchises(self) -> None:
        result = self.syncer.sync(SOURCES["nba"])
        self.assertEqual(result.status, "ok")
        jordan = self.conn.execute(
            "SELECT kind, start_date, end_date, precision, label FROM v_events "
            "WHERE source = 'nba' AND entity_name = 'Michael Jordan' ORDER BY kind"
        ).fetchall()
        self.assertEqual(
            jordan,
            [
                ("career", "1984", "2002", "year", "Michael Jordan's NBA career"),
                ("draft", "1984", None, "year", "Drafted #3 by the Chicago Bulls"),
                ("life", "1963-02-17", None, "day", "Michael Jordan"),
            ],
        )
        game = self.conn.execute(
            "SELECT label, start_date, entity_name, detail ->> 'home_points', detail ->> 'type' "
            "FROM v_events WHERE kind = 'game' ORDER BY start_year"
        ).fetchall()
        self.assertEqual(
            game,
            [
                (
                    "Toronto Huskies 66 – New York Knicks 68",
                    "1946-11-01",
                    "Toronto Huskies",
                    66,
                    "Regular Season",
                ),
                (
                    "Chicago Bulls 87 – Utah Jazz 86",
                    "1998-06-14",
                    "Chicago Bulls",
                    87,
                    "Playoffs",
                ),
            ],
        )
        away = self.conn.execute(
            "SELECT entities.name, role FROM event_participants "
            "JOIN events ON events.id = event_participants.event_id "
            "JOIN entities ON entities.id = event_participants.entity_id "
            "WHERE events.external_id = 'game:0049700086'"
        ).fetchall()
        self.assertEqual(away, [("Utah Jazz", "away")])
        eras = self.conn.execute(
            "SELECT label, start_year, end_year FROM v_events WHERE source = 'nba' AND kind = 'run' ORDER BY start_year"
        ).fetchall()
        self.assertEqual(
            eras, [("Toronto Huskies", 1946, 1946), ("Chicago Bulls", 1966, 2019)]
        )
        ids = self.conn.execute(
            "SELECT scheme, value FROM entity_identifiers JOIN entities ON entities.id = entity_id "
            "WHERE entities.name = 'Michael Jordan'"
        ).fetchall()
        self.assertEqual(ids, [("nba", "893")])

    def test_musicbrainz_releases_with_partial_dates(self) -> None:
        self.syncer.sync(SOURCES["musicbrainz"])
        rows = self.conn.execute(
            "SELECT entity_name, label, start_date, precision, detail ->> 'type' "
            "FROM v_events WHERE source = 'musicbrainz' ORDER BY start_year"
        ).fetchall()
        self.assertEqual(
            rows,
            [
                ("The Beatles", "Abbey Road", "1969-09-26", "day", "Album"),
                ("Tori Amos", "Little Earthquakes", "1992", "year", "Album"),
                ("Tori Amos", "A Sorta Fairytale", "2002-10-14", "day", "Single"),
            ],
        )
        self.assertEqual(
            self.conn.execute(
                "SELECT value FROM entity_identifiers JOIN entities ON entities.id = entity_id "
                "WHERE entities.name = 'The Beatles'"
            ).fetchone(),
            ("b10bbbfc-cf9e-42e0-be17-e2c3e1d2600d",),
        )
        # The compilation placeholder artist is skipped by the spec's `unless`.
        self.assertEqual(
            self.count("SELECT COUNT(*) FROM entities WHERE name = 'Various Artists'"),
            0,
        )


class ScanScaleTest(IngestTest):
    """Rank, the level-of-detail table and the scan indexes."""

    def test_rank_reflects_votes_participants_and_entity_breadth(self) -> None:
        self.sync_all()
        godfather, obscure = (
            self.conn.execute(
                "SELECT rank FROM events WHERE external_id = ?", (eid,)
            ).fetchone()[0]
            for eid in ("tt0068646:release", "tt0098904:run")
        )
        # 2M votes and three credits beat 350k votes and no credits.
        self.assertGreater(godfather, obscure)
        aaron, nobody = (
            self.conn.execute(
                "SELECT rank FROM events WHERE external_id = ?", (eid,)
            ).fetchone()[0]
            for eid in ("aaronha01:life", "mathed01:life")
        )
        # Aaron owns more events (awards, All-Star games, Hall of Fame).
        self.assertGreater(aaron, nobody)

    def test_lod_keeps_the_top_events_per_bucket(self) -> None:
        self.sync_all()
        sizes = [
            r[0]
            for r in self.conn.execute(
                "SELECT DISTINCT bucket_size FROM event_lod ORDER BY 1"
            )
        ]
        self.assertEqual(sizes, [1, 10, 100])
        self.assertEqual(self.count("SELECT COUNT(*) FROM event_lod WHERE pos > 20"), 0)
        # Negative years bucket downwards: Aristotle (-384) is in -400.
        row = self.conn.execute(
            "SELECT bucket FROM event_lod JOIN events ON events.id = event_id "
            "WHERE bucket_size = 100 AND events.label = 'Aristotle'"
        ).fetchone()
        self.assertEqual(row, (-400,))
        # The best film of the 1970s bucket is The Godfather.
        top = self.conn.execute(
            "SELECT events.label FROM event_lod JOIN events ON events.id = event_id "
            "WHERE bucket_size = 10 AND bucket = 1970 AND event_lod.category = 'film' "
            "ORDER BY pos LIMIT 1"
        ).fetchone()
        self.assertEqual(top, ("The Godfather",))
        # Re-syncing a source rebuilds only its slice; totals stay consistent.
        before = self.count("SELECT COUNT(*) FROM event_lod")
        self.syncer.sync(SOURCES["lahman"], force=True)
        self.assertEqual(self.count("SELECT COUNT(*) FROM event_lod"), before)

    def test_span_lod_covers_every_bucket_a_span_overlaps(self) -> None:
        self.sync_all()
        # Aaron (1934-2021, Lahman) overlaps the 1930s through the 2020s.
        buckets = [
            r[0]
            for r in self.conn.execute(
                "SELECT bucket FROM span_lod JOIN events ON events.id = event_id "
                "WHERE bucket_size = 10 AND events.external_id = 'aaronha01:life' "
                "AND span_lod.category = 'baseball' ORDER BY bucket"
            )
        ]
        self.assertEqual(buckets, list(range(1930, 2030, 10)))
        # Ohtani is still playing: his career runs to the open-end cap.
        last = self.conn.execute(
            "SELECT max(bucket) FROM span_lod JOIN events ON events.id = event_id "
            "WHERE bucket_size = 100 AND events.external_id = 'ohtansh01:career'"
        ).fetchone()[0]
        self.assertEqual(last, 2000)
        # '*' rows rank across categories: the 1900s century has lives from
        # several sources and categories, each capped at LOD_KEEP per source.
        self.assertGreater(
            self.count(
                "SELECT COUNT(*) FROM span_lod WHERE bucket_size = 100 AND bucket = 1900 "
                "AND category = '*'"
            ),
            0,
        )
        self.assertEqual(self.count("SELECT COUNT(*) FROM span_lod WHERE pos > 20"), 0)
        self.assertGreater(
            self.count("SELECT COUNT(*) FROM event_lod WHERE category = '*'"), 0
        )

    def test_window_scan_uses_an_ordered_index(self) -> None:
        self.sync_all()
        plan = " ".join(
            r[3]
            for r in self.conn.execute(
                "EXPLAIN QUERY PLAN SELECT events.id FROM events "
                "WHERE events.category = 'baseball' AND events.start_year BETWEEN 1950 AND 1980 "
                "AND (events.start_year, events.id) > (1957, 0) "
                "ORDER BY events.start_year, events.id LIMIT 50"
            )
        )
        self.assertIn("events_by_category", plan)
        self.assertNotIn("TEMP B-TREE", plan)
        plan = " ".join(
            r[3]
            for r in self.conn.execute(
                "EXPLAIN QUERY PLAN SELECT events.id FROM events "
                "WHERE events.start_year BETWEEN 1950 AND 1980 "
                "ORDER BY events.start_year, events.id LIMIT 50"
            )
        )
        self.assertIn("events_by_start", plan)
        self.assertNotIn("TEMP B-TREE", plan)

    def test_rerank_covers_every_source(self) -> None:
        self.sync_all()
        self.conn.execute("UPDATE events SET rank = 0")
        self.conn.execute("DELETE FROM event_lod")
        self.assertEqual(self.syncer.rerank(), len(SOURCES))
        self.assertGreater(self.count("SELECT COUNT(*) FROM event_lod"), 0)
        self.assertGreater(self.count("SELECT COUNT(*) FROM events WHERE rank > 0"), 0)


if __name__ == "__main__":
    unittest.main()
