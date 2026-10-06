# Contributing to Thyme

## Prerequisites

- TrailBase v0.34 or newer (`trail` on your PATH), from
  https://github.com/trailbaseio/trailbase/releases
- Node.js 20+ and Yarn 1.22 (pinned through Volta in `package.json`)
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
| `wasm/src/` | Custom endpoints (`/search`, `/timeline`...) as a TrailBase WASM component |
| `scripts/ingest/` | Source adapters and the sync engine |
| `scripts/import_imdb_sqlite.py` | Raw IMDB import into `titles`, `persons`, ... |
| `templates/`, `static/` | Alpine.js pages rendered by `scripts/build.ts` |
| `scripts/__tests__/`, `scripts/test_ingest_events.py` | Tests |

## Workflow

1. Branch from `main`.
2. Make the change with tests: Jest for TypeScript (`yarn test`), unittest for
   the ingest (`make test-ingest`).
3. `make lint` (Biome, `tsc`, ruff) and `make test` must pass. The pre-commit
   hook runs Biome on staged files.
4. Commit with a conventional message: `feat(scope): ...`, `fix(scope): ...`,
   `docs: ...`, `chore: ...`. The commit-msg hook enforces the format.
5. Open a pull request.

## Conventions

- Schema changes are new migration files, never edits to applied ones.
- Every record API in the config is read-only; data enters through the import
  and ingest scripts.
- Views exposed as record APIs need a column that traces to an INTEGER
  primary key and must not use table aliases.
- A new data source is one class in `scripts/ingest/sources/` registered in
  `SOURCES`, yielding `Entity`, `Event` and optionally `Participant` rows.
- Keep the pure parts of handlers (parsers, query builders) exported so they
  can be unit tested outside the WASM runtime.
