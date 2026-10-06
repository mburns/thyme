#!/usr/bin/env python3
"""Stream a Wikidata JSON dump and keep only what the timeline needs.

The full dump (``latest-all.json.gz``, 100+ GB compressed, ~110M items) is
too big to load; this script reads it once, line by line, and writes two
much smaller files under ``data/wikidata/``:

* ``items.jsonl.gz``   one compact record per selected item (humans,
  conflicts, countries, awards): English label and description, classes,
  the dates we plot, external identifiers, and the dated relations
  (awards received, positions held, conflicts, participants).
* ``labels.jsonl.gz``  ``{"id", "label", "description", "classes"}`` for
  every item with an English label, so items that selected items refer to
  (an award, an occupation, a participant) can be named without a second
  pass.

Usage:
    python3 scripts/wikidata_extract.py latest-all.json.gz
    pigz -dc latest-all.json.gz | python3 scripts/wikidata_extract.py -
    python3 scripts/wikidata_extract.py dump.json.bz2 --limit 100000

Expect several hours for the full dump in Python; decompressing with
``pigz``/``pbzip2`` outside Python and piping in is noticeably faster. The
output is deterministic for a given dump, so run it once per dump release.
"""

from __future__ import annotations

import argparse
import bz2
import gzip
import json
import logging
import re
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import IO, Any

logger = logging.getLogger("wikidata_extract")

# P31 (instance of) classes that select an item. Wikidata's class tree is
# deep, so this is a pragmatic list of the classes that actually carry
# most items, not a closure over subclasses.
HUMAN = {"Q5"}
CONFLICT = {
    "Q198",  # war
    "Q103495",  # world war
    "Q178561",  # battle
    "Q180684",  # conflict
    "Q645883",  # military operation
    "Q831663",  # military campaign
    "Q3119",  # siege
    "Q124734",  # rebellion
    "Q10931",  # revolution
    "Q8465",  # civil war
    "Q1261499",  # naval battle
    "Q2001676",  # military offensive
}
COUNTRY = {
    "Q6256",  # country
    "Q3624078",  # sovereign state
    "Q7275",  # state
    "Q3024240",  # historical country
    "Q48349",  # empire
    "Q417175",  # kingdom
    "Q1250464",  # realm
    "Q99541706",  # historical unrecognized state
}
AWARD = {
    "Q618779",  # award
    "Q4220917",  # film award
    "Q1364556",  # music award
    "Q1407225",  # television award
    "Q1709894",  # literary award
    "Q378427",  # literary prize
    "Q7191",  # Nobel Prize
    "Q1826282",  # sports award
    "Q4364047",  # order (chivalric)
}
KINDS = {
    "person": HUMAN,
    "conflict": CONFLICT,
    "country": COUNTRY,
    "award": AWARD,
}

# Properties copied into items.jsonl, by meaning.
DATE_PROPS = {
    "P569": "birth",
    "P570": "death",
    "P580": "start",
    "P582": "end",
    "P571": "inception",
    "P576": "dissolved",
    "P585": "point",
}
ID_PROPS = {
    "P345": "imdb",
    "P1825": "bbref",
    "P3171": "olympedia",
    "P2002": "twitter",
}
# Relation properties with the qualifiers that date them.
RELATION_PROPS = {
    "P166": "awards",  # award received (P585 point in time)
    "P39": "positions",  # position held (P580/P582)
    "P607": "conflicts",  # conflict (person took part in)
    "P710": "participants",  # participant (of a conflict)
    "P106": "occupations",
}
QUALIFIER_DATES = ("P585", "P580", "P582")

# Cheap pre-filter: a selected item's line must mention one of these class
# ids as a P31 value, so skip json.loads for the ~90% of lines that cannot
# match. Humans are the bulk: "numeric-id":5 is unambiguous enough.
_CLASS_IDS = set().union(*KINDS.values())
_PREFILTER = re.compile(
    r'"numeric-id":(%s)[,}]' % "|".join(sorted({c[1:] for c in _CLASS_IDS}))
)


def open_dump(path: str) -> IO[str]:
    if path == "-":
        return sys.stdin
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")
    if path.endswith(".bz2"):
        return bz2.open(path, "rt", encoding="utf-8")
    return open(path, encoding="utf-8")


def iter_lines(stream: IO[str]) -> Iterator[str]:
    """Yield one JSON object per line, tolerating the dump's array framing."""
    for line in stream:
        line = line.strip()
        if not line or line in ("[", "]"):
            continue
        if line.endswith(","):
            line = line[:-1]
        yield line


def wikidata_time(value: dict[str, Any]) -> dict[str, Any] | None:
    """Reduce a Wikidata time value to year/month/day plus precision.

    Wikidata precision: 11 day, 10 month, 9 year, 8 decade, 7 century, 6
    millennium. Anything coarser than a year is kept as a year with
    ``certainty: "circa"`` so the timeline can show it as approximate.
    """
    text = value.get("time", "")
    m = re.match(r"^([+-])(\d+)-(\d\d)-(\d\d)T", text)
    if not m:
        return None
    sign, year, month, day = m.groups()
    y = int(year) * (-1 if sign == "-" else 1)
    if y == 0:
        return None
    precision = int(value.get("precision", 9))
    out: dict[str, Any] = {"year": y}
    if precision >= 10 and month != "00":
        out["month"] = int(month)
    if precision >= 11 and day != "00":
        out["day"] = int(day)
    if precision < 9:
        out["circa"] = True
    if "Q1985786" in value.get("calendarmodel", ""):
        out["julian"] = True
    return out


def _value(snak: dict[str, Any]) -> Any:
    dv = snak.get("datavalue")
    return None if dv is None else dv.get("value")


def _item_id(snak: dict[str, Any]) -> str | None:
    v = _value(snak)
    return v.get("id") if isinstance(v, dict) else None


def _claims(entity: dict[str, Any], prop: str) -> list[dict[str, Any]]:
    """Statements for a property, preferred rank first, deprecated dropped."""
    statements = [
        s
        for s in entity.get("claims", {}).get(prop, [])
        if s.get("rank") != "deprecated"
    ]
    statements.sort(key=lambda s: 0 if s.get("rank") == "preferred" else 1)
    return statements


def classify(classes: list[str]) -> str | None:
    for kind, ids in KINDS.items():
        if any(c in ids for c in classes):
            return kind
    return None


def extract(entity: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Return (label record, item record or None) for one dump entity."""
    qid = entity["id"]
    label = entity.get("labels", {}).get("en", {}).get("value")
    description = entity.get("descriptions", {}).get("en", {}).get("value")
    classes = [
        c for c in (_item_id(s["mainsnak"]) for s in _claims(entity, "P31")) if c
    ]
    label_record = {
        "id": qid,
        "label": label,
        "description": description,
        "classes": classes[:3],
    }

    kind = classify(classes)
    if kind is None or not label:
        return label_record, None

    item: dict[str, Any] = {
        "id": qid,
        "kind": kind,
        "label": label,
        "description": description,
        "classes": classes[:5],
        "enwiki": entity.get("sitelinks", {}).get("enwiki", {}).get("title"),
    }
    for prop, name in DATE_PROPS.items():
        for s in _claims(entity, prop):
            v = _value(s["mainsnak"])
            t = wikidata_time(v) if isinstance(v, dict) else None
            if t:
                item[name] = t
                break
    for prop, name in ID_PROPS.items():
        values = [
            v
            for v in (_value(s["mainsnak"]) for s in _claims(entity, prop))
            if isinstance(v, str)
        ]
        if values:
            item[name] = values[0]
    for prop, name in RELATION_PROPS.items():
        rels = []
        for s in _claims(entity, prop):
            target = _item_id(s["mainsnak"])
            if not target:
                continue
            rel: dict[str, Any] = {"id": target}
            for qp in QUALIFIER_DATES:
                for q in s.get("qualifiers", {}).get(qp, []):
                    v = _value(q)
                    t = wikidata_time(v) if isinstance(v, dict) else None
                    if t:
                        rel[DATE_PROPS[qp]] = t
                        break
            rels.append(rel)
        if rels:
            item[name] = rels
    return label_record, item


def run(dump: str, out_dir: Path, limit: int | None, log_every: int) -> tuple[int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    items_path = out_dir / "items.jsonl.gz"
    labels_path = out_dir / "labels.jsonl.gz"
    seen = kept = 0
    started = time.time()
    with (
        open_dump(dump) as stream,
        gzip.open(items_path, "wt", encoding="utf-8") as items_out,
        gzip.open(labels_path, "wt", encoding="utf-8") as labels_out,
    ):
        for line in iter_lines(stream):
            seen += 1
            if limit is not None and seen > limit:
                break
            # Labels for everything; full parse only for candidate lines.
            if not _PREFILTER.search(line):
                head = _cheap_label(line)
                if head is not None:
                    labels_out.write(json.dumps(head, ensure_ascii=False) + "\n")
                continue
            try:
                entity = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("skipping unparsable line %d", seen)
                continue
            if entity.get("type") != "item":
                continue
            label_record, item = extract(entity)
            if label_record["label"]:
                labels_out.write(json.dumps(label_record, ensure_ascii=False) + "\n")
            if item is not None:
                kept += 1
                items_out.write(json.dumps(item, ensure_ascii=False) + "\n")
            if seen % log_every == 0:
                rate = seen / max(time.time() - started, 1e-9)
                logger.info(
                    "%s lines, %s kept, %.0f lines/s", f"{seen:,}", f"{kept:,}", rate
                )
    logger.info(
        "done: %s lines, %s items kept in %.0fs",
        f"{seen:,}",
        f"{kept:,}",
        time.time() - started,
    )
    return seen, kept


_ID_RE = re.compile(r'"id":"(Q\d+)"')
_LABEL_RE = re.compile(
    r'"labels":\{.*?"en":\{"language":"en","value":"((?:[^"\\]|\\.)*)"'
)
_DESC_RE = re.compile(
    r'"descriptions":\{.*?"en":\{"language":"en","value":"((?:[^"\\]|\\.)*)"'
)


def _cheap_label(line: str) -> dict[str, Any] | None:
    """Pull id and English label from a non-candidate line without parsing it.

    Non-candidates are ~90% of the dump; a full json.loads for each would
    dominate the run time. Regexes over the raw JSON are good enough for a
    label and a description.
    """
    if not line.startswith('{"type":"item"'):
        return None
    m_id = _ID_RE.search(line)
    m_label = _LABEL_RE.search(line)
    if not m_id or not m_label:
        return None
    desc = _DESC_RE.search(line)
    return {
        "id": m_id.group(1),
        "label": json.loads(f'"{m_label.group(1)}"'),
        "description": json.loads(f'"{desc.group(1)}"') if desc else None,
        "classes": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("dump", help="latest-all.json(.gz|.bz2) or - for stdin")
    parser.add_argument("--out-dir", type=Path, default=Path("data") / "wikidata")
    parser.add_argument("--limit", type=int, help="stop after this many dump lines")
    parser.add_argument("--log-every", type=int, default=1_000_000)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args.dump, args.out_dir, args.limit, args.log_every)
    return 0


if __name__ == "__main__":
    sys.exit(main())
