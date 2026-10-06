"""Olympic athlete events, ``data/sports/olympic_events/athlete_events.csv``.

One row per athlete per event. Produces a ``games`` event per Olympics, a
``competed`` event per athlete per Games, and a ``medal`` event per podium.
"""

from __future__ import annotations

from collections.abc import Iterable

from ingest.core import Entity, Event, Source, SyncContext, iso_date, read_csv

CATEGORY = "olympics"
FILE = "sports/olympic_events/athlete_events.csv"


def _val(value: str) -> str | None:
    return None if value in ("", "NA") else value


class OlympicsSource(Source):
    slug = "olympics"
    name = "Olympic athletes and results, 1896-2016"
    homepage = "https://www.kaggle.com/datasets/heesoo37/120-years-of-olympic-history-athletes-and-results"
    license = "CC0 (scraped from sports-reference.com)"
    description = "Every Games, every athlete appearance and every medal."
    file_patterns = (FILE, "sports/olympic_events/noc_regions.csv")

    def _rows(self, ctx: SyncContext) -> Iterable[dict[str, str]]:
        return read_csv(ctx.data_dir / FILE, ctx.limit)

    def entities(self, ctx: SyncContext) -> Iterable[Entity]:
        seen_athletes: set[str] = set()
        seen_games: set[str] = set()
        for r in self._rows(ctx):
            if r["ID"] not in seen_athletes:
                seen_athletes.add(r["ID"])
                yield Entity(
                    external_id=r["ID"],
                    kind="person",
                    name=r["Name"],
                    description=f"{r['Sport']} ({r['Team']})",
                )
            if r["Games"] not in seen_games:
                seen_games.add(r["Games"])
                yield Entity(
                    external_id=r["Games"],
                    kind="games",
                    name=f"{r['Year']} {r['Season']} Olympics",
                    description=r["City"],
                )

    def events(self, ctx: SyncContext) -> Iterable[Event]:
        seen_games: set[str] = set()
        seen_competed: set[tuple[str, str]] = set()
        for r in self._rows(ctx):
            year = int(r["Year"])
            date = iso_date(year)[0]
            games = r["Games"]
            if games not in seen_games:
                seen_games.add(games)
                yield Event(
                    external_id=f"games:{games}",
                    entity_kind="games",
                    entity_external_id=games,
                    kind="games",
                    label=f"{year} {r['Season']} Olympics, {r['City']}",
                    start_date=date,
                    precision="year",
                    start_year=year,
                    category=CATEGORY,
                    detail={"city": r["City"], "season": r["Season"]},
                )
            if (r["ID"], games) not in seen_competed:
                seen_competed.add((r["ID"], games))
                yield Event(
                    external_id=f"{r['ID']}:competed:{games}",
                    entity_kind="person",
                    entity_external_id=r["ID"],
                    kind="competed",
                    label=f"{r['Sport']} at the {games} Olympics",
                    start_date=date,
                    precision="year",
                    start_year=year,
                    category=CATEGORY,
                    detail={
                        "team": r["Team"],
                        "noc": r["NOC"],
                        "sport": r["Sport"],
                        "age": _val(r["Age"]),
                    },
                )
            medal = _val(r["Medal"])
            if medal:
                yield Event(
                    external_id=f"{r['ID']}:medal:{games}:{r['Event']}:{medal}",
                    entity_kind="person",
                    entity_external_id=r["ID"],
                    kind="medal",
                    label=f"{medal} medal, {r['Event']}",
                    start_date=date,
                    precision="year",
                    start_year=year,
                    category=CATEGORY,
                    detail={"medal": medal, "team": r["Team"], "noc": r["NOC"]},
                )
