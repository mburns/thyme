.PHONY: help check-deps import-data test-import sources sync-events link wasm site run \
        test test-ingest test-search lint format clean clean-all

help:
	@echo "Thyme - timeline browser on TrailBase"
	@echo "====================================="
	@echo ""
	@echo "Data:"
	@echo "  check-deps   - Check required system tools (sqlite3, curl, gunzip, node, python3)"
	@echo "  import-data  - Download and import the IMDB datasets (data/imdb)"
	@echo "  test-import  - Import 1000 rows per IMDB file for development"
	@echo "  sources      - List timeline data sources and their sync state"
	@echo "  sync-events  - Import timeline events from sources whose files changed"
	@echo "  link         - Rebuild entity links (the same person across sources)"
	@echo ""
	@echo "Build and run:"
	@echo "  wasm         - Build the WASM component with the custom endpoints"
	@echo "  site         - Render templates/ into dist/"
	@echo "  run          - Build component and site, then start TrailBase on one origin"
	@echo ""
	@echo "Quality:"
	@echo "  test         - Run every test suite (Jest, ingest, search smoke test)"
	@echo "  test-ingest  - Run the timeline ingest tests"
	@echo "  test-search  - Check the FTS5 indexes in traildepot/data/main.db"
	@echo "  lint         - Biome, TypeScript and ruff checks"
	@echo "  format       - Format TypeScript and Python"
	@echo "  clean        - Remove build artifacts"
	@echo "  clean-all    - Also remove the database and TrailBase runtime files"

check-deps:
	@for tool in sqlite3 curl gunzip node yarn python3 trail; do \
	  command -v $$tool >/dev/null 2>&1 || { echo "❌ $$tool is required but not installed"; exit 1; }; \
	done
	@echo "✅ All system dependencies are installed"

import-data:
	@python3 scripts/import_imdb_sqlite.py
	@echo "✅ IMDB import complete"

test-import:
	@python3 scripts/import_imdb_sqlite.py --limit 1000
	@echo "✅ IMDB sample import complete"

sources:
	@python3 scripts/ingest_events.py list

sync-events:
	@python3 scripts/ingest_events.py sync
	@echo "✅ Timeline events synced"

link:
	@python3 scripts/ingest_events.py link

wasm:
	@yarn --silent wasm:build
	@echo "✅ Component built: traildepot/wasm/component.wasm"

site:
	@yarn --silent build:site

run: wasm site
	trail run --public-dir dist

test: test-ingest
	@yarn --silent test

test-ingest:
	@python3 scripts/test_ingest_events.py

test-search:
	@python3 scripts/test_search.py

lint:
	@yarn --silent lint
	@yarn --silent type-check
	@ruff check scripts
	@echo "✅ Lint passed"

format:
	@yarn --silent format
	@ruff format scripts

clean:
	@rm -rf dist wasm/dist traildepot/wasm temp_import
	@echo "✅ Build artifacts removed"

clean-all: clean
	@rm -rf traildepot/data traildepot/secrets traildepot/uploads traildepot/backups
	@echo "✅ Database and TrailBase runtime files removed"
