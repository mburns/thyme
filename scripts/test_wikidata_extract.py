#!/usr/bin/env python3
"""Tests for the dated-stub mode of ``scripts/wikidata_extract.py``.

Run: python3 scripts/test_wikidata_extract.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import wikidata_extract  # noqa: E402


def _time(value: str, precision: int = 11) -> dict:
    return {
        "mainsnak": {
            "datavalue": {
                "value": {
                    "time": value,
                    "precision": precision,
                    "calendarmodel": "http://www.wikidata.org/entity/Q1985727",
                }
            }
        },
        "rank": "normal",
    }


def _item(qid: str, classes: list[str], **claims: list[dict]) -> dict:
    return {
        "id": qid,
        "type": "item",
        "labels": {"en": {"value": f"Item {qid}"}},
        "claims": {
            "P31": [
                {"mainsnak": {"datavalue": {"value": {"id": c}}}, "rank": "normal"}
                for c in classes
            ],
            **claims,
        },
    }


class AllDatedTest(unittest.TestCase):
    def test_other_classes_are_dropped_without_the_flag(self) -> None:
        book = _item("Q1", ["Q571"], P577=[_time("+1991-00-00T00:00:00Z", 9)])
        _, item = wikidata_extract.extract(book)
        self.assertIsNone(item)

    def test_dated_item_becomes_a_stub_with_the_flag(self) -> None:
        book = _item("Q1", ["Q571"], P577=[_time("+1991-00-00T00:00:00Z", 9)])
        _, item = wikidata_extract.extract(book, all_dated=True)
        assert item is not None
        self.assertEqual(item["kind"], "dated")
        self.assertEqual(item["classes"], ["Q571"])
        self.assertEqual(item["published"], {"year": 1991})

    def test_undated_items_stay_out_even_with_the_flag(self) -> None:
        _, item = wikidata_extract.extract(_item("Q2", ["Q571"]), all_dated=True)
        self.assertIsNone(item)

    def test_selected_classes_keep_their_kind(self) -> None:
        human = _item("Q3", ["Q5"], P569=[_time("+1950-02-03T00:00:00Z")])
        _, item = wikidata_extract.extract(human, all_dated=True)
        assert item is not None
        self.assertEqual(item["kind"], "person")
        self.assertEqual(item["birth"], {"year": 1950, "month": 2, "day": 3})

    def test_prefilter_matches_date_statements(self) -> None:
        line = '{"type":"item","id":"Q9","claims":{"P577":[{"mainsnak":{}}]}}'
        self.assertIsNotNone(wikidata_extract._DATE_PREFILTER.search(line))
        self.assertIsNone(wikidata_extract._DATE_PREFILTER.search('{"P31":[]}'))


if __name__ == "__main__":
    unittest.main()
