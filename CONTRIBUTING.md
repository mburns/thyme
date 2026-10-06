# Contributing to Thyme

## Prerequisites

- TrailBase v0.34 or newer (`trail` on your PATH), from
  https://github.com/trailbaseio/trailbase/releases
- Node.js 22.20+ (the WASM componentizer's native modules need it) and Yarn
  1.22, pinned through Volta in `package.json`
- Python 3.11+ with `ruff` (`pip install -r requirements.txt`)
- `sqlite3`, `curl`, `gunzip`

Run `make check-deps` to verify.

## Setup

```bash
yarn install
trail run                 # once: creates traildepot/data and applies migrations
make test-import          # small IMDB sample, or make import-data for everything
make sync-events          # events from every source under data/
make run                  # builds the WASM component and the site, serves on :4000
```

## Where things live

| Path | What |
|---|---|
| `traildepot/migrations/` | Schema, as TrailBase migrations (`U<unix time>__name.sql`) |
| `traildepot/config.textproto` | Record APIs (all read-only) |
| `wasm/src/` | Custom endpoints (`/search`, `/timeline…`, `/timeline/domains`) as a TrailBase WASM component |
| `wasm/src/domains.ts` | The domains the site browses by: categories, kinds, sources, what is planned |
| `web/timeline/` | The timeline app (TypeScript, bundled by Vite into `dist/static/js/`) |
| `scripts/ingest/` | The sync engine (`core.py`), the CSV spec adapter and Python adapters |
| `scripts/ingest/specs/` | Declarative CSV sources (TOML) |
| `scripts/wikipedia_lists_fetch.py`, `scripts/wikidata_extract.py` | Fetch or reduce upstream data into `data/` |
| `scripts/import_imdb_sqlite.py` | Raw IMDB import into `titles`, `persons`, ... |
| `templates/`, `static/` | Alpine.js pages rendered by `scripts/build.ts` |
| `scripts/__tests__/`, `web/__tests__/`, `scripts/test_*.py` | Tests |

## Workflow

1. Branch from `main`.
2. Make the change with tests: Jest for TypeScript (`yarn test`), unittest for
   the ingest and parsers (`make test-ingest`).
3. `make lint` (Biome, `tsc` for `wasm/` and `web/`, ruff) and `make test`
   must pass. The pre-commit hook runs Biome on staged files.
4. Commit with a conventional message: `feat(scope): ...`, `fix(scope): ...`,
   `perf(scope): ...`, `docs: ...`, `chore: ...`. The commit-msg hook enforces
   the format.
5. Open a pull request.

## Conventions

- Schema changes are new migration files, never edits to applied ones. A
  migration that changes the level-of-detail tables needs `make rerank` on
  existing databases; say so in the migration's comment.
- Every record API in the config is read-only; data enters through the import
  and ingest scripts.
- Views exposed as record APIs need a column that traces to an INTEGER
  primary key and must not use table aliases.
- A new CSV dataset is a TOML spec in `scripts/ingest/specs/`; a source that
  needs logic is a `Source` subclass in `scripts/ingest/sources/` registered
  in `SOURCES`. Either yields `Entity`, `Event` and optionally `Participant`
  and `Identifier` rows. Emit `wikidata_id` and external identifiers whenever
  the dataset has them; they are the join keys between sources. Add a fixture
  for it to `scripts/test_ingest_events.py`, which syncs every registered
  source.
- New event categories belong to a domain in `wasm/src/domains.ts`; a
  category with no data yet is fine there, it shows as a stub.
- Queries over `events` must drive from an index that bounds the window
  (`events_by_start`, `events_by_category`, `events_by_source_year`, the FTS
  hits) and pin the join order with `CROSS JOIN`; check the plan against a
  large database, the planner flips after `ANALYZE`.
- Keep the pure parts of handlers and of the timeline app (parsers, query
  builders, layout maths) exported so they can be unit tested outside the
  runtime and the browser.
