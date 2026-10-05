"""Lahman Baseball Database (SABR), ``data/sports/baseball/*.csv``.

Players get a life span, an MLB career span (debut to final game, day
precision), awards, All-Star selections and Hall of Fame induction.
Franchises get a span of active seasons and a championship event per World
Series win.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from ingest.core import Entity, Event, Source, SyncContext, iso_date, read_csv

CATEGORY = "baseball"
BASE = "sports/baseball"


def _int(value: str | None) -> int | None:
    return int(value) if value else None


def _year_of(date: str) -> int:
    return int(date[:4])


class LahmanSource(Source):
    slug = "lahman"
    name = "Lahman Baseball Database"
    homepage = "https://sabr.org/lahman-database/"
    license = "CC BY-SA 3.0"
    description = (
        "MLB players (life and career spans, awards, All-Star games, Hall of "
        "Fame) and franchises (active seasons, World Series wins), 1871 on."
    )
    file_patterns = (f"{BASE}/*.csv", f"{BASE}/readme*.txt")

    def version(self, ctx: SyncContext) -> str | None:
        for readme in ctx.data_dir.glob(f"{BASE}/readme*.txt"):
            text = readme.read_text(encoding="utf-8", errors="replace")[:2000]
            span = re.search(r"Database (\d{4}-\d{4})", text)
            date = re.search(r"Release Date:\s*(.+)", text)
            if span or date:
                parts = [m.group(1).strip() for m in (span, date) if m]
                return "Lahman " + ", ".join(parts)
        return super().version(ctx)

    def _path(self, ctx: SyncContext, name: str) -> Path:
        return ctx.data_dir / BASE / name

    def _people(self, ctx: SyncContext) -> list[dict[str, str]]:
        return list(read_csv(self._path(ctx, "People.csv"), ctx.limit))

    def _franchises(self, ctx: SyncContext) -> dict[str, dict[str, str]]:
        path = self._path(ctx, "TeamsFranchises.csv")
        if not path.exists():
            return {}
        return {row["franchID"]: row for row in read_csv(path)}

    def entities(self, ctx: SyncContext) -> Iterable[Entity]:
        for p in self._people(ctx):
            name = f"{p['nameFirst']} {p['nameLast']}".strip()
            if not name:
                continue
            bbref = p.get("bbrefID") or ""
            yield Entity(
                external_id=p["playerID"],
                kind="person",
                name=name,
                description="Baseball player",
                url=(
                    f"https://www.baseball-reference.com/players/{bbref[0]}/{bbref}.shtml"
                    if bbref
                    else None
                ),
            )
        for franch_id, f in self._franchises(ctx).items():
            yield Entity(
                external_id=franch_id,
                kind="team",
                name=f["franchName"],
                description="MLB franchise",
            )

    def events(self, ctx: SyncContext) -> Iterable[Event]:
        yield from self._player_events(ctx)
        yield from self._award_events(ctx)
        yield from self._team_events(ctx)

    def _player_events(self, ctx: SyncContext) -> Iterable[Event]:
        for p in self._people(ctx):
            pid = p["playerID"]
            name = f"{p['nameFirst']} {p['nameLast']}".strip()
            birth_year = _int(p["birthYear"])
            if birth_year is not None:
                start, precision = iso_date(
                    birth_year, _int(p["birthMonth"]), _int(p["birthDay"])
                )
                death_year = _int(p["deathYear"])
                end = (
                    iso_date(death_year, _int(p["deathMonth"]), _int(p["deathDay"]))[0]
                    if death_year is not None
                    else None
                )
                yield Event(
                    external_id=f"{pid}:life",
                    entity_kind="person",
                    entity_external_id=pid,
                    kind="life",
                    label=name,
                    start_date=start,
                    end_date=end,
                    precision=precision,
                    start_year=birth_year,
                    end_year=death_year,
                    span=True,
                    category=CATEGORY,
                    detail={
                        "birthplace": ", ".join(
                            x
                            for x in (
                                p["birthCity"],
                                p["birthState"],
                                p["birthCountry"],
                            )
                            if x
                        )
                        or None,
                        "bats": p["bats"] or None,
                        "throws": p["throws"] or None,
                    },
                )
            debut = p["debut"]
            if debut:
                final = p["finalGame"] or None
                yield Event(
                    external_id=f"{pid}:career",
                    entity_kind="person",
                    entity_external_id=pid,
                    kind="career",
                    label=f"{name}'s MLB career",
                    start_date=debut,
                    end_date=final,
                    precision="day",
                    start_year=_year_of(debut),
                    end_year=_year_of(final) if final else None,
                    span=True,
                    category=CATEGORY,
                )

    def _award_events(self, ctx: SyncContext) -> Iterable[Event]:
        awards = self._path(ctx, "AwardsPlayers.csv")
        if awards.exists():
            for a in read_csv(awards, ctx.limit):
                year = int(a["yearID"])
                key = f"{a['playerID']}:award:{year}:{a['awardID']}:{a['lgID']}:{a['notes']}"
                yield Event(
                    external_id=key,
                    entity_kind="person",
                    entity_external_id=a["playerID"],
                    kind="award",
                    label=a["awardID"],
                    start_date=iso_date(year)[0],
                    precision="year",
                    start_year=year,
                    category=CATEGORY,
                    detail={"league": a["lgID"], "notes": a["notes"] or None},
                )
        hof = self._path(ctx, "HallOfFame.csv")
        if hof.exists():
            for h in read_csv(hof, ctx.limit):
                if h["inducted"] != "Y":
                    continue
                year = int(h["yearid"])
                yield Event(
                    external_id=f"{h['playerID']}:hall_of_fame",
                    entity_kind="person",
                    entity_external_id=h["playerID"],
                    kind="hall_of_fame",
                    label="Inducted into the Baseball Hall of Fame",
                    start_date=iso_date(year)[0],
                    precision="year",
                    start_year=year,
                    category=CATEGORY,
                    detail={"voted_by": h["votedBy"], "as": h["category"]},
                )
        allstar = self._path(ctx, "AllstarFull.csv")
        if allstar.exists():
            for s in read_csv(allstar, ctx.limit):
                year = int(s["yearID"])
                yield Event(
                    external_id=f"{s['playerID']}:all_star:{year}:{s['gameNum']}",
                    entity_kind="person",
                    entity_external_id=s["playerID"],
                    kind="all_star",
                    label=f"All-Star ({s['lgID']})",
                    start_date=iso_date(year)[0],
                    precision="year",
                    start_year=year,
                    category=CATEGORY,
                    detail={"team": s["teamID"]},
                )

    def _team_events(self, ctx: SyncContext) -> Iterable[Event]:
        teams = self._path(ctx, "Teams.csv")
        franchises = self._franchises(ctx)
        if not teams.exists() or not franchises:
            return
        seasons: dict[str, list[int]] = defaultdict(list)
        latest = 0
        for t in read_csv(teams, ctx.limit):
            year = int(t["yearID"])
            latest = max(latest, year)
            franch = t["franchID"]
            if franch not in franchises:
                continue
            seasons[franch].append(year)
            if t["WSWin"] == "Y":
                yield Event(
                    external_id=f"{franch}:championship:{year}",
                    entity_kind="team",
                    entity_external_id=franch,
                    kind="championship",
                    label=f"{t['name']} win the World Series",
                    start_date=iso_date(year)[0],
                    precision="year",
                    start_year=year,
                    category=CATEGORY,
                    detail={"team": t["name"], "league": t["lgID"]},
                )
        for franch, years in seasons.items():
            first, last = min(years), max(years)
            active = franchises[franch]["active"] == "Y" and last == latest
            yield Event(
                external_id=f"{franch}:run",
                entity_kind="team",
                entity_external_id=franch,
                kind="run",
                label=franchises[franch]["franchName"],
                start_date=iso_date(first)[0],
                end_date=None if active else iso_date(last)[0],
                precision="year",
                start_year=first,
                end_year=None if active else last,
                span=True,
                category=CATEGORY,
                detail={"seasons": len(years)},
            )
