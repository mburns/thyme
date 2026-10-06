# Thyme 🌿

When did that happen, compared to everything else? Thyme lines up millions of
dated events from open datasets on one scrolling timeline: album releases next
to ball games, lives next to film premieres, books next to the wars they were
written about. Pick an event and read every other event as years before or
after it.

[![CI](https://github.com/mburns/thyme/workflows/CI/badge.svg)](https://github.com/mburns/thyme/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Built on [TrailBase](https://trailbase.io) (SQLite with a REST API, a static
file server and WebAssembly endpoints), a Python ingest, a few static pages
hydrated with Alpine.js, and a small TypeScript app for the timeline itself.

## What you get

- **Timeline** (`/timeline.html`): one horizontal band per data source,
  scrolled sideways across a world range of years, with a sticky year axis
  and a density minimap. Zoomed out, each band shows its top events per
  century, decade or year; zoomed in, every event. Filter by name, category,
  kind, source or domain; click an event for details and *Compare from
  here* to get a second axis of years before and after it. The view state is
  in the URL.
- **Browse** (`/browse.html`): a dozen domains (Film, TV & games, Music,
  Sports, Books, Awards, Science, Politics, Wars, Religion, Business, Arts,
  Exploration, Lives, Wikipedia lists), each a set of event categories and
  kinds with live counts; categories that are planned but empty show as
  stubs.
- **Sources** (`/sources.html`): every dataset with counts, year range,
  licence, last sync and what is planned.
- **Search** (`/search.html`): entities from every source plus the IMDB
  tables, each linking to its entity page and its place on the timeline.
- The original IMDB browser (movies, TV, people, genres, top rated) is still
  there, reached from the Film domain.

## Quick start

```bash
# TrailBase v0.34+ (https://github.com/trailbaseio/trailbase/releases),
# Node 22.20+, Yarn 1.22, Python 3.11+, sqlite3
make check-deps
yarn install
trail run                 # once: creates traildepot/data and applies migrations; stop it again
make test-import          # small IMDB sample (or make import-data for the full datasets)
make sync-events          # every source under data/ (see Sources below)
make run                  # builds the WASM component and the site, serves on :4000
```

Visit `http://localhost:4000`. The pages call `/api/records/v1/...` and the
custom endpoints on the same origin, so a separate static file server will
not do. After adding data run `make sync-events` (and `make rerank` after a
migration that changes the level-of-detail tables); the server can keep
running, the ingest waits for it.

## Sources

Every dataset is a *source* that contributes *entities* (a person, a team, a
book) and *events* attached to them: instants (a release, a game, a medal) or
spans (a life, a career, a run), each with a date precision and a certainty.
Sources that are CSV files are TOML specs in `scripts/ingest/specs/`
(`csvsource.py` documents the format); anything needing logic is a `Source`
subclass in `scripts/ingest/sources/`. Both register automatically.

| Source | Files under `data/` | Events |
|---|---|---|
| `imdb` | derived from the imported IMDB tables | releases and series runs, episodes, cast and crew as participants, people's lives |
| `musicbrainz` | `music/official_releases.csv` | every official release (5M) on its artist's lane |
| `wikidata_age` | `wiki/AgeDataset-V*.csv` | 1.2M lives with QIDs and occupation (the category) |
| `lahman` | `sports/baseball/*.csv` | MLB lives and careers, awards, All-Star games, Hall of Fame, franchises, World Series |
| `nba` | `sports/nba/csv/*.csv` | NBA lives, careers, drafts, every game since 1946, franchise eras |
| `olympics` | `sports/olympic_events/athlete_events.csv` | each Games, each athlete appearance, each medal |
| `cricket` | `sports/cricket/*.csv` | Tests, ODIs and T20Is since 1877 |
| `mls` | `sports/mls/matches.csv` | every MLS match since 1996 |
| `bx_books` | `books/BX-Books.csv` | 271k books with year of publication, authors as participants |
| `steam` | `steam/games_march2025_cleaned.csv` | 89k game releases, keyed by Steam app id |
| `paintings` | `art/artist.csv` | the lives of 421 famous painters |
| `wikipedia_lists` | `wikipedia/lists/*.json` | dated entries of Wikipedia bibliographies and lists (see below) |
| `wikidata` | `wikidata/{items,labels}.jsonl.gz` | people, wars, countries, awards from the dump (see below) |

```bash
make sources        # every source, its row counts, last sync, whether files changed
make sync-events    # import the sources whose files changed
make link           # the same person across sources (also runs after every sync)
make rerank         # recompute rank and the level-of-detail tables
```

A sync fingerprints the source's files, skips unchanged sources, upserts rows
by their stable per-source key, removes rows the source no longer produces
and logs the run in `source_syncs`. Entities sharing an external identifier
(IMDb, Baseball-Reference, MusicBrainz, NBA.com, Steam) or a Wikidata QID
link with certainty; people whose name and years match link at lower
confidence. Rank (votes, credits, how much else the owner did) decides what a
zoomed-out view shows.

### Wikipedia lists and bibliographies

```bash
make wikipedia-lists                                  # seeds: "Lists of books"
make wikipedia-lists SEEDS="Bibliography of Montana history" MAX_PAGES=1
make wikipedia-lists SEEDS="List of treaties" MAX_PAGES=20
make sync-events
```

The fetcher pulls the wikitext of bibliographies and "List of ..." pages
through the MediaWiki API. The adapter turns `{{cite book}}`/`{{cite
journal}}` templates and italic-title lines into books and articles with
their authors, and every other dated line into a stub `listed` event, so a
list of treaties or earthquakes is on the timeline before it has a parser of
its own. Each list page is an entity that takes part in its entries.

### Wikidata from the dump

```bash
pigz -dc latest-all.json.gz | python3 scripts/wikidata_extract.py -
python3 scripts/wikidata_extract.py latest-all.json.gz --limit 1000000    # a quick look
python3 scripts/wikidata_extract.py latest-all.json.gz --all-dated        # every dated item
make sync-events
```

The extract keeps humans, conflicts, countries and awards with their dates,
identifiers and dated relations (awards received, positions held, conflict
participation). With `--all-dated` any other item that has a calendar date
(inception, publication, point in time) is kept as a `dated` stub under its
first class, which is how every dated Wikipedia subject can be represented
before it gets a parser.

## Timeline API

The custom endpoints are a TrailBase WASM component built from `wasm/src/`
(`make wasm`): TypeScript against the `trailbase-wasm` SDK, bundled by Vite
and componentized with `jco`. Editing a handler body needs a rebuild plus
`kill -HUP <trail pid>`; adding a route needs a restart.

- `GET /timeline?from&to&category&source&kind&span&q&participant&anchor&cursor&limit`:
  one page of a window in (start, id) order, read by walking an index and
  stopping at `limit`; `active` are the notable spans still open at `from`;
  `next` is a keyset cursor; `total` is capped. Filters that the LOD tables
  cannot answer (a name, a kind) read the event stream, driven by the FTS
  hits when a name is given.
- `GET /timeline/overview?from&to&bucket&per&category&source`: the top `per`
  events per bucket (1, 10 or 100 years) across the requested categories,
  from the precomputed `event_lod` table, so a 500-year view costs what a
  decade costs.
- `GET /timeline/density?from&to&bucket&by=source|category`: counts per year
  bucket from `event_density`.
- `GET /timeline/sources`, `GET /timeline/domains`: what is loaded, with
  counts.
- `GET /timeline/participants?event=`, `GET /timeline/links?entity=`: who
  took part in an event; the same entity across sources.
- `GET /search?q=&entities&titles&persons`: entities from every source
  (trigram FTS, ranked by their top event) and the IMDB tables.

```bash
curl -g "http://localhost:4000/timeline?from=1960&to=1975&q=beatles&limit=50"
curl -g "http://localhost:4000/timeline/overview?from=1500&to=1999&bucket=10&per=8&category=astronomer,physicist"
curl -g "http://localhost:4000/timeline/density?from=-500&to=2030&bucket=10&by=source"
```

## SQLite features in use

| Feature | Where |
|---|---|
| STRICT tables, CHECK constraints, foreign keys with cascades | every table |
| FTS5 external-content indexes with `unicode61` and `highlight()` | `titles_fts`, `persons_fts`, `/search` |
| FTS5 `trigram` tokenizer for substring name search | `entities_fts`, `/timeline?q=`, entity search |
| R*Tree (`rtree_i32`) over `[start_year, end_year]` | `events_span`, kept in sync by triggers |
| VIRTUAL generated columns (`julianday`) | `events.start_julian`, `events.end_julian` |
| JSON (`json_each`, `json_object`, `json_valid`) | genres, professions, `events.detail` |
| Window functions | `/timeline`, `/timeline/overview`, the LOD rebuild |
| Recursive CTE | `span_lod` (a span in every bucket it overlaps) |
| UPSERT, `WITHOUT ROWID` staging and LOD tables, partial indexes | ingest |
| `ANALYZE`, `PRAGMA optimize`, WAL | end of every sync |

Join order is pinned with `CROSS JOIN` where the planner, after `ANALYZE`,
would otherwise start from the seven-row `sources` table; source filters are
checked on the events row, and a sparse source inside a dense window is paged
on its own index first.

## Development

```bash
make lint          # Biome, TypeScript (wasm/ and web/), ruff
make test          # Jest, the ingest and parser test suites
yarn build:site    # templates/ -> dist/, web/ -> dist/static/js/timeline.js
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the layout and conventions.

## Licence

MIT for the code. Each dataset keeps its own licence, listed on the sources
page.
