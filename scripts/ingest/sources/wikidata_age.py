"""Wikidata-derived people with birth and death years, ``data/wiki``.

The "Age Dataset" (1.2M people) carries Wikidata QIDs, which makes it the
natural hub for linking people across sources. Each person gets one ``life``
span; their occupation becomes the event category.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from ingest.core import Entity, Event, Source, SyncContext, iso_date, read_csv

PATTERN = "wiki/AgeDataset-V*.csv"


def _int(value: str) -> int | None:
    return int(value) if value.lstrip("-").isdigit() else None


class WikidataAgeSource(Source):
    slug = "wikidata_age"
    name = "Wikidata people (Age Dataset)"
    homepage = "https://www.kaggle.com/datasets/imoore/age-dataset"
    license = "CC0 (Wikidata)"
    description = "1.2M notable people with birth year, death year and occupation."
    file_patterns = (PATTERN,)

    def _file(self, ctx: SyncContext) -> Path:
        # Newest version wins if several are present (V1, V2, ...).
        return sorted(ctx.data_dir.glob(PATTERN))[-1]

    def _rows(self, ctx: SyncContext) -> Iterable[dict[str, str]]:
        return read_csv(self._file(ctx), ctx.limit)

    def entities(self, ctx: SyncContext) -> Iterable[Entity]:
        for r in self._rows(ctx):
            if _int(r["Birth year"]) is None or not r["Name"]:
                continue
            yield Entity(
                external_id=r["Id"],
                kind="person",
                name=r["Name"],
                description=r["Short description"] or None,
                wikidata_id=r["Id"],
                url=f"https://www.wikidata.org/wiki/{r['Id']}",
            )

    def events(self, ctx: SyncContext) -> Iterable[Event]:
        for r in self._rows(ctx):
            birth = _int(r["Birth year"])
            if birth is None or not r["Name"]:
                continue
            death = _int(r["Death year"])
            yield Event(
                external_id=f"{r['Id']}:life",
                entity_kind="person",
                entity_external_id=r["Id"],
                kind="life",
                label=r["Name"],
                start_date=iso_date(birth)[0],
                end_date=None if death is None else iso_date(death)[0],
                precision="year",
                start_year=birth,
                end_year=death,
                span=True,
                category=(r["Occupation"] or "person").strip().lower(),
                detail={
                    "gender": r["Gender"] or None,
                    "country": r["Country"] or None,
                    "manner_of_death": r["Manner of death"] or None,
                },
            )
