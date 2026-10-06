#!/usr/bin/env python3
"""Fetch Wikipedia list pages as wikitext into ``data/wikipedia/lists/``.

Bibliographies ("Bibliography of Montana history") and "List of ..." pages
are long, hand-curated lists of dated things: books with a year of
publication, events with a date. The ``wikipedia_lists`` ingest adapter
turns every dated entry into a timeline event; this script gets the pages.

Seeds are index pages such as "Lists of books". Each seed's wikitext is
fetched, every linked page whose title starts with "Bibliography of",
"List of" or "Lists of" is queued, and the first ``--max-pages`` of those
are fetched and written as one JSON file per page::

    {"title": ..., "pageid": ..., "revid": ..., "fetched": ..., "wikitext": ...}

Usage:
    python3 scripts/wikipedia_lists_fetch.py                  # seeds: Lists of books
    python3 scripts/wikipedia_lists_fetch.py "Bibliography of Montana history"
    python3 scripts/wikipedia_lists_fetch.py "Lists of books" --max-pages 200

Pages are fetched through the MediaWiki API with a descriptive User-Agent,
twenty titles per request, with a short pause between requests, as the
Wikimedia API etiquette asks. Re-running refreshes files whose revision
changed and leaves the rest untouched.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "thyme-timeline/0.1 (https://github.com/mburns/thyme; data ingest)"
BATCH = 20
PAUSE_SECONDS = 1.0
LIST_PREFIXES = ("Bibliography of ", "List of ", "Lists of ")

logger = logging.getLogger("wikipedia_lists_fetch")

_LINK = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def slugify(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")[:120]


def linked_lists(wikitext: str) -> list[str]:
    """Titles of list pages linked from a page, in order, without repeats."""
    out: list[str] = []
    seen: set[str] = set()
    for m in _LINK.finditer(wikitext):
        title = m.group(1).strip().replace("_", " ")
        if title.startswith(LIST_PREFIXES) and title not in seen:
            seen.add(title)
            out.append(title)
    return out


def api_get(params: dict[str, str]) -> dict:
    query = urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    req = urllib.request.Request(f"{API}?{query}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def fetch_wikitext(titles: list[str]) -> dict[str, dict]:
    """``{title: {"pageid", "revid", "wikitext"}}`` for the titles that exist."""
    out: dict[str, dict] = {}
    for i in range(0, len(titles), BATCH):
        batch = titles[i : i + BATCH]
        data = api_get(
            {
                "action": "query",
                "prop": "revisions",
                "rvprop": "content|ids",
                "rvslots": "main",
                "redirects": "1",
                "titles": "|".join(batch),
            }
        )
        for page in data.get("query", {}).get("pages", []):
            if page.get("missing") or not page.get("revisions"):
                continue
            rev = page["revisions"][0]
            out[page["title"]] = {
                "pageid": page["pageid"],
                "revid": rev["revid"],
                "wikitext": rev["slots"]["main"]["content"],
            }
        if i + BATCH < len(titles):
            time.sleep(PAUSE_SECONDS)
    return out


def existing_revid(path: Path) -> int | None:
    try:
        with path.open(encoding="utf-8") as f:
            return int(json.load(f).get("revid", 0)) or None
    except (OSError, ValueError):
        return None


def run(seeds: list[str], out_dir: Path, max_pages: int) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    seed_pages = fetch_wikitext(seeds)
    queue: list[str] = []
    for title in seeds:
        page = seed_pages.get(title)
        if page is None:
            logger.warning("seed page not found: %s", title)
            continue
        # A seed that is itself a list (a bibliography) is kept too.
        if title.startswith(LIST_PREFIXES):
            queue.append(title)
        for linked in linked_lists(page["wikitext"]):
            if linked not in queue:
                queue.append(linked)
    queue = queue[:max_pages]
    logger.info("%d list pages to fetch", len(queue))

    written = 0
    pages = fetch_wikitext(queue)
    for title, page in pages.items():
        path = out_dir / f"{slugify(title)}.json"
        if existing_revid(path) == page["revid"]:
            continue
        record = {
            "title": title,
            "pageid": page["pageid"],
            "revid": page["revid"],
            "fetched": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_"),
            "wikitext": page["wikitext"],
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False)
        written += 1
    logger.info("%d pages written or refreshed under %s", written, out_dir)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("seeds", nargs="*", default=["Lists of books"])
    parser.add_argument("--max-pages", type=int, default=60)
    parser.add_argument(
        "--out-dir", type=Path, default=Path("data") / "wikipedia" / "lists"
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args.seeds, args.out_dir, args.max_pages)
    return 0


if __name__ == "__main__":
    sys.exit(main())
