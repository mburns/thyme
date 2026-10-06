# Thyme 🌿

A minimalist IMDB data browser built with TrailBase, featuring efficient data import and a clean, modern interface.

[![CI](https://github.com/yourusername/thyme/workflows/CI/badge.svg)](https://github.com/yourusername/thyme/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Shell Script](https://img.shields.io/badge/shell-bash-blue.svg)](https://www.gnu.org/software/bash/)
[![Code style: shellcheck](https://img.shields.io/badge/code%20style-shellcheck-000000.svg)](https://github.com/koalaman/shellcheck)

## ✨ Features

- **Efficient Data Import**: Uses SQLite's bulk import capabilities for fast IMDB data loading
- **Modern UI**: Clean, responsive interface built with Alpine.js
- **Comprehensive Search**: Full-text search across movies, TV shows, people, and genres using FTS5
- **Real-time Data**: Dynamic content loading with pagination
- **Static Site Generation**: Build process creates optimized static files
- **Professional Development**: Full CI/CD pipeline with shell script quality checks

## 🔍 Search Functionality

The website includes powerful full-text search capabilities powered by SQLite's FTS5:

### Search Features
- **Multi-field Search**: Search across titles, people, genres, and years
- **Filtered Results**: Filter by content type (titles, persons, genres, years)
- **Pagination**: Navigate through large result sets
- **Real-time Search**: Debounced search as you type
- **Ranked Results**: Results are ranked by relevance using FTS5 ranking

### Search Examples
- Movie titles: "The Godfather", "Star Wars"
- Actor names: "Tom Hanks", "Meryl Streep"
- Genres: "action", "drama", "comedy"
- Years: "1999"
- Combined title searches: "action 2023", "godfather 1972"
- Exact phrases: `"the godfather"` (quotes keep the words together)

Terms are AND-ed and the last term is prefix-matched, so typing "godf" already
finds "The Godfather". Titles are ordered by number of votes, then relevance;
people by relevance.

### Technical Implementation
- **FTS5 Virtual Tables**: `titles_fts` (primary/original title, genres, start
  year) and `persons_fts` (name, professions) are external-content tables over
  `titles` and `persons`
- **Automatic Sync**: Database triggers keep both indexes up to date; the
  migration also rebuilds them from existing rows
- **TrailBase API**: `GET /search` in `wasm/src/search.ts` turns the query
  into a safe FTS5 `MATCH` expression and paginates each type with `page` and
  `limit` (max 100)
- **Alpine.js Frontend**: Reactive search interface with debouncing

### Testing Search
```bash
# Unit tests for the query builder and parameter parsing
yarn test

# Check the FTS5 indexes in an imported database
python3 scripts/test_search.py traildepot/data/main.db

# Start TrailBase and hit the API
trail run
curl "http://localhost:4000/search?q=godfather&limit=5"
curl "http://localhost:4000/search?q=hanks&titles=false"
```

## 🚀 Quick Start

### Prerequisites

- Bash 4.0 or higher
- SQLite 3.39 or higher
- Git
- Make (optional, for using Makefile commands)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/thyme.git
   cd thyme
   ```

2. **Check system dependencies**
   ```bash
   make check-deps
   ```

3. **Set up development environment**
   ```bash
   # Install development dependencies (pre-commit)
   make install-dev
   
   # Install pre-commit hooks
   make setup-hooks
   ```

4. **Install TrailBase v0.34 or newer** and start it once to create the
   database and apply the migrations
   ```bash
   # https://github.com/trailbaseio/trailbase/releases
   trail run
   ```

5. **Import IMDB data** (stop the server first, then start it again)
   ```bash
   make import-data
   make sync-events
   ```

6. **Build the custom endpoints and the static site**
   ```bash
   yarn install
   make wasm          # compiles wasm/src into traildepot/wasm/component.wasm
   yarn build:site    # renders templates/ into dist/
   ```

7. **Serve the site and the API from one origin**
   ```bash
   trail run --public-dir dist     # or: make run
   ```

Visit `http://localhost:4000` to see your IMDB browser. The pages call
`/api/records/v1/...` and `/search` on the same host, so a separate static
file server will not work.

## 🛠️ Development

### Available Commands

```bash
make help          # Show all available commands
make check-deps    # Check system dependencies
make install-dev   # Install development dependencies
make setup-hooks   # Install pre-commit hooks
make lint          # Run linting checks (shellcheck)
make test          # Run tests and validation
make build         # Build static site
make clean         # Clean build artifacts
make all           # Run all checks
make info          # Show project information
```

### Code Quality

This project uses several tools to maintain high code quality:

- **Pre-commit hooks** - Automated checks before each commit
- **shellcheck** - Shell script linting and best practices
- **shfmt** - Shell script formatting
- **GitHub Actions** - Continuous integration
- **Markdown linting** - Documentation quality

### Project Structure

```
thyme/
├── templates/              # HTML templates
├── static/                # Static assets (CSS, JS, images)
├── traildepot/            # TrailBase configuration and migrations
│   └── migrations/        # Database migrations
├── data/                  # IMDB data files (downloaded automatically)
├── dist/                  # Built static site (generated)
├── *.sh                   # Shell scripts
├── .github/workflows/     # CI/CD configuration
└── docs/                  # Documentation
```

## 📊 Data Import

The project includes efficient data import scripts that:

1. **Download datasets** from [IMDB's official source](https://datasets.imdbws.com/)
2. **Use SQLite's bulk import** for maximum performance
3. **Handle data transformation** and foreign key relationships
4. **Provide progress tracking** and error handling

### Import Process

```bash
# The import script will:
# 1. Download missing datasets automatically
# 2. Decompress .tsv.gz files
# 3. Use SQLite's .import command for bulk loading
# 4. Transform data with proper types and relationships
# 5. Clean up temporary files

make import-data
```

IMDB exports live in `data/imdb/`. The script downloads any that are missing.

## 🕰️ Timeline Events

Every dataset is a *source* that contributes *entities* (a person, a title, a
team) and *events* attached to them. An event is an instant (a release, an
award, a medal) or a span (a life, a career, a TV run) with an explicit date
precision, so year-only dates are never mistaken for 1 January. The schema is
in `traildepot/migrations/U1791237000__events.sql`; `v_events` is the
flattened read model and `entities_fts` the name index.

| Source | Files | Events |
|---|---|---|
| `imdb` | derived from the imported `titles`/`persons`/`episodes`/`principals`/`crew` tables | title releases and series runs (titles with at least 1000 votes), every episode of an included series on the series' lane, the full cast and crew of each as participants, people's life spans, IMDb ids for linking |
| `lahman` | `data/sports/baseball/*.csv` | player life and career spans, awards, All-Star games, Hall of Fame, franchise runs and World Series wins |
| `olympics` | `data/sports/olympic_events/athlete_events.csv` | each Games, each athlete appearance, each medal |
| `wikidata_age` | `data/wiki/AgeDataset-V*.csv` | 1.2M people's life spans with Wikidata QIDs and occupation |
| `wikidata` | `data/wikidata/{items,labels}.jsonl.gz` (from the dump, see below) | people (life spans, awards received, positions held), wars and battles with their participants, countries, awards; IMDb and Baseball-Reference ids for exact linking |

```bash
make sources        # list sources, row counts, last sync, whether files changed
make sync-events    # import every source whose files changed
python3 scripts/ingest_events.py sync --force imdb --imdb-min-votes 500
python3 scripts/ingest_events.py sync --force imdb --no-imdb-episodes   # titles only
```

IMDB scales with the vote threshold: at 1,000 votes roughly 100k titles,
a few million episodes and tens of millions of credits; at 100 votes about
three times as many titles. Episodes are instants on their series' lane
(`kind=episode`, season and episode number in `detail`), never stand-alone
titles, and people are entities as soon as they are credited, with a life
span only when IMDB knows a birth year.

Each sync fingerprints the source's files (path, size, mtime), skips the
source if nothing changed, upserts rows by their stable per-source key,
deletes rows the source no longer produces, and logs the run in
`source_syncs`. Drop a newer file in place (for example `AgeDataset-V2.csv`)
and the next `make sync-events` picks it up.

To add a source, subclass `ingest.core.Source` in `scripts/ingest/sources/`,
yield `Entity` and `Event` rows, and register it in `SOURCES`. Use the
`wikidata_id` column wherever a QID is known; it is the join key between
sources.

### Timeline API

`GET /timeline` (in `wasm/src/timeline.ts`) returns events that
overlap a year range, with filters for `category`, `source`, `kind`, `span`,
an entity-name substring `q`, and `participant=<entity id>` for events an
entity owns or took part in. Pass `anchor=<entity id>` to get every event's
offset in years (and days, at day precision) from that entity's life, career
or run. `from=1972&to=1972&span=1` answers "what was going on in 1972". The
`total` is counted separately and capped (`totalCapped: true` means "at
least"), so an unfiltered window over millions of events stays fast.

- `GET /timeline/density` returns counts per year bucket and category from
  the precomputed `event_density` table, so histogram strips cost the same
  at any zoom level.
- `GET /timeline/participants?event=<id>` lists who took part in an event:
  a film's cast and crew, a World Series roster.
- `GET /timeline/links?entity=<id>` resolves an entity to its canonical
  record and lists every source's version of it.

```bash
curl -g "http://localhost:4000/timeline?from=1950&to=1960&category=baseball&kind=championship"
curl -g "http://localhost:4000/timeline?q=aaron&anchor=24023&limit=50"
curl -g "http://localhost:4000/timeline?participant=24023&from=1800&to=2030"
curl -g "http://localhost:4000/timeline/density?from=1800&to=2020&bucket=10&source=wikidata_age"
curl -g "http://localhost:4000/timeline/links?entity=24023"
```

### Wikidata from the dump

Wikidata is the hub: it has every person with a Wikipedia article, every
war, award and country, and it carries the IMDb and Baseball-Reference ids
that make linking exact. The full JSON dump
(https://dumps.wikimedia.org/wikidatawiki/entities/, `latest-all.json.gz`,
100+ GB) is reduced once per release to two small files:

```bash
# hours for the full dump; decompress outside Python for speed
pigz -dc latest-all.json.gz | python3 scripts/wikidata_extract.py -
# or, for a quick look at the first million items
python3 scripts/wikidata_extract.py latest-all.json.gz --limit 1000000
make sync-events
```

`items.jsonl.gz` holds humans, conflicts, countries and awards with their
dates, identifiers and dated relations (`P166` award received, `P39`
position held, `P607`/`P710` conflict participation); `labels.jsonl.gz`
names everything those items refer to. The `wikidata` source then yields
life spans, award instants, position spans, conflict spans with their
combatants and participating countries, and country existence spans. Dates
coarser than a year become `certainty: circa`; Julian-calendar dates are
flagged in `detail`. `scripts/fixtures/wikidata-mini-dump.json` is an
eleven-entity slice of the real dump used by the tests.

### One person, several sources

Hank Aaron arrives from Lahman, IMDB and Wikidata as three entities.
`make link` (also run automatically after every sync) fills `entity_links`:
entities sharing an external identifier (`entity_identifiers`: IMDb nconst,
Baseball-Reference id) or a Wikidata QID link with certainty, and people
whose name, birth year and death year match, and are unique in both
sources, link at 0.9 (0.7 when still alive). Wikidata is the canonical side
because QIDs are the cross-source key; the dump source wins over the Kaggle
extract when both are loaded. Events carry `certainty` (`exact`, `circa`, `unknown`)
for sources that know their dates are approximate.

### SQLite features in use

The database is plain SQLite, read by TrailBase's bundled build (3.53 in
v0.34) and written by the Python ingest; everything below works in both.

### Custom endpoints as a WASM component

TrailBase runs custom code as WebAssembly components. The handlers live in
`wasm/src/` as ordinary TypeScript against the `trailbase-wasm` SDK
(`HttpHandler`, `HttpResponse`, `query`). `make wasm` bundles them with Vite,
turns the bundle into a component with `jco componentize`, and copies it to
`traildepot/wasm/component.wasm`, which TrailBase loads at startup. Editing a
handler body needs a rebuild plus `kill -HUP <trail pid>`; adding or removing
a route needs a restart. The pure parts (query builders, parsers) are unit
tested with Jest outside the runtime.

| Feature | Where |
|---|---|
| STRICT tables, CHECK constraints, foreign keys with cascades | every table |
| FTS5 external-content indexes with `unicode61` for prefix search and `highlight()` | `titles_fts`, `persons_fts`, `/search` |
| FTS5 `trigram` tokenizer for substring name search | `entities_fts`, `/timeline?q=` |
| R*Tree (`rtree_i32`) over `[start_year, end_year]` for interval overlap | `events_span`, kept in sync by triggers |
| VIRTUAL generated columns (`julianday`) for day-level offsets | `events.start_julian`, `events.end_julian` |
| JSON: `json_each` to normalise comma lists, `json_object` for event details, `json_valid` CHECK | `title_genres`, `person_professions`, `events.detail` |
| Window functions (`row_number`, `count(*) OVER ()`) | `/timeline` |
| UPSERT (`ON CONFLICT DO UPDATE`), `WITHOUT ROWID` staging, partial indexes | ingest, `entities_by_wikidata` |
| STAT4 statistics via `ANALYZE` and `PRAGMA optimize`, WAL journal | end of every sync |

Not available in TrailBase's build and therefore avoided: the math functions
(`ln`, `floor`) and geopoly.

## 🎨 Customization

### Adding New Pages

1. Create a new template in `templates/`
2. Add it to the build script's page templates list
3. Update navigation if needed

### Styling

- CSS is in `static/style.css`
- Uses CSS custom properties for theming
- Responsive design with mobile-first approach

### Database Schema

The database schema is defined in TrailBase migrations:

- `titles` - Movie and TV show information
- `persons` - Actor, director, and crew information
- `principals` - Cast and crew relationships
- `ratings` - User ratings and vote counts
- `episodes` - TV episode information
- `crew` - Director and writer relationships

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make all` to ensure quality
5. Submit a pull request

### Shell Script Best Practices

- Use `set -euo pipefail` for strict error handling
- Follow shellcheck recommendations
- Use meaningful variable names
- Add comments for complex logic
- Quote all variable expansions

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [IMDB](https://www.imdb.com/) for providing the dataset
- [TrailBase](https://trailbase.dev/) for the database framework
- [Alpine.js](https://alpinejs.dev/) for the reactive UI
- [shellcheck](https://www.shellcheck.net/) for shell script quality
- All contributors and maintainers

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/thyme/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/thyme/discussions)
- **Documentation**: Check inline code comments and this README

---

Made with ❤️ by the Thyme community
