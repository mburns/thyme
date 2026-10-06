#!/usr/bin/env python3
"""Tests for the Wikipedia list parser (``scripts/ingest/sources/wikipedia_lists``).

Run: python3 scripts/test_wikipedia_lists.py
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ingest.sources.wikipedia_lists import (  # noqa: E402
    parse_page,
    strip_markup,
    subject_of,
    template_params,
)

WIKITEXT = """
== Overviews ==
* {{cite book |last=Malone |first=Michael P. |last2=Roeder |first2=Richard B.
  |title=Montana: A History of Two Centuries |publisher=[[University of Washington Press]]
  |year=1991 |isbn=0-295-97129-0}}
* {{cite journal |last=Smith |first=Jane |title=Mining Camps of the [[Rocky Mountains]]
  |journal=Montana: The Magazine of Western History |date=Spring 1978 |volume=28}}
* Toole, K. Ross. ''Montana: An Uncommon Land''. Norman: University of Oklahoma Press, 1959.
* [[Lewis and Clark Expedition|The expedition]] reaches the Three Forks of the Missouri, July 1805.<ref>Journals</ref>
* A line without any date that should be ignored.
Prose that is not a bullet, 1864, is ignored too.
"""


class ParsePageTest(unittest.TestCase):
    def setUp(self) -> None:
        self.entries = parse_page("Bibliography of Montana history", WIKITEXT)
        self.by_title = {e.title: e for e in self.entries}

    def test_cite_book_becomes_a_book_with_authors(self) -> None:
        e = self.by_title["Montana: A History of Two Centuries"]
        self.assertEqual(e.kind, "book")
        self.assertEqual(e.year, 1991)
        self.assertEqual(e.authors, ["Michael P. Malone", "Richard B. Roeder"])
        self.assertEqual(e.publisher, "University of Washington Press")
        self.assertEqual(e.detail["isbn"], "0-295-97129-0")

    def test_cite_journal_becomes_an_article_with_the_year_of_its_date(self) -> None:
        e = self.by_title["Mining Camps of the Rocky Mountains"]
        self.assertEqual(e.kind, "article")
        self.assertEqual(e.year, 1978)
        self.assertEqual(e.publisher, "Montana: The Magazine of Western History")

    def test_plain_bullet_with_italic_title_is_a_book(self) -> None:
        e = self.by_title["Montana: An Uncommon Land"]
        self.assertEqual(e.kind, "book")
        self.assertEqual(e.year, 1959)
        self.assertEqual(e.authors, ["Toole, K. Ross"])

    def test_other_dated_bullets_are_generic_entries(self) -> None:
        generic = [e for e in self.entries if e.kind == "entry"]
        self.assertEqual(len(generic), 1)
        self.assertEqual(generic[0].year, 1805)
        self.assertTrue(generic[0].title.startswith("The expedition reaches"))
        self.assertNotIn("<ref>", generic[0].title)

    def test_undated_lines_and_prose_are_ignored(self) -> None:
        self.assertEqual(len(self.entries), 4)

    def test_ids_are_stable_per_page_title_and_year(self) -> None:
        again = parse_page("Bibliography of Montana history", WIKITEXT)
        self.assertEqual(
            [e.external_id for e in again], [e.external_id for e in self.entries]
        )


class HelpersTest(unittest.TestCase):
    def test_subject_of(self) -> None:
        self.assertEqual(
            subject_of("Bibliography of Montana history"), "Montana history"
        )
        self.assertEqual(subject_of("List of treaties"), "treaties")
        self.assertEqual(subject_of("Something else"), "Something else")

    def test_strip_markup(self) -> None:
        self.assertEqual(
            strip_markup("'''Bold''' [[Link|text]] {{tpl|x}} <ref>r</ref> ''it''"),
            "Bold text it",
        )

    def test_template_params_ignore_pipes_inside_links(self) -> None:
        params = template_params("title=A [[B|C]] D |year=2001| isbn = 1")
        self.assertEqual(params, {"title": "A C D", "year": "2001", "isbn": "1"})


if __name__ == "__main__":
    unittest.main()
