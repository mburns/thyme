# Makefile for Timeline App with TrailBase

.PHONY: all run lint format test docs type-check clean install-dev develop init-db fetch-people fetch-events import-data update-data trailbase-start trailbase-stop trailbase-init trailbase-download import-csv

# Check if virtual environment is activated
check-venv:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "Error: Virtual environment not activated. Please run: source venv/bin/activate"; \
		exit 1; \
	fi

# Install development dependencies
install-dev: check-venv
	pip install -r requirements.txt

# Install package in development mode
develop: check-venv
	pip install -e .

# Initialize the database (legacy SQLAlchemy)
init-db: check-venv
	python init_db.py

# Download TrailBase binary
trailbase-download: check-venv
	@echo "Downloading TrailBase binary..."
	python download_trailbase.py

# Initialize TrailBase
trailbase-init: check-venv
	@echo "Initializing TrailBase..."
	@if [ ! -f "./trail" ]; then \
		echo "TrailBase binary not found. Run 'make trailbase-download' first."; \
		exit 1; \
	fi
	@mkdir -p data
	@echo "TrailBase initialized. Run 'make trailbase-start' to start the server."

# Start TrailBase server
trailbase-start: check-venv
	@echo "Starting TrailBase server..."
	@if [ ! -f "./trail" ]; then \
		echo "TrailBase binary not found. Run 'make trailbase-download' first."; \
		exit 1; \
	fi
	@./trail run --config trailbase_config.json --schema trailbase_schema.json

# Stop TrailBase server (if running)
trailbase-stop:
	@pkill -f trail || echo "TrailBase not running"

# Import CSV data into TrailBase
import-csv: check-venv
	@if [ -z "$(CSV_FILE)" ]; then \
		echo "Error: Please specify CSV_FILE=path/to/file.csv"; \
		echo "Usage: make import-csv CSV_FILE=data/sample_people.csv"; \
		echo "Optional: add DRY_RUN=1 for dry run mode"; \
		exit 1; \
	fi
	@if [ "$(DRY_RUN)" = "1" ]; then \
		echo "Running CSV import in DRY RUN mode..."; \
		python scripts/import_people_csv.py $(CSV_FILE) --dry-run; \
	else \
		echo "Importing CSV data into TrailBase..."; \
		python scripts/import_people_csv.py $(CSV_FILE); \
	fi

# Run the Flask application with TrailBase
run: check-venv
	python thyme_trailbase.py

# Run the legacy Flask application
run-legacy: check-venv
	flask run

# Lint the code
lint: check-venv
	flake8 thyme tests

# Format the code
format: check-venv
	black thyme tests
	isort thyme tests

# Run tests
test: check-venv
	pytest

# Generate documentation
docs: check-venv
	cd docs && make html

# Type checking
type-check: check-venv
	mypy thyme

# Data fetching and importing
fetch-people: check-venv
	python scripts/fetch_wikidata.py --type people --limit 25

fetch-events: check-venv
	python scripts/fetch_wikidata.py --type events --limit 25

import-data: check-venv
	python scripts/import_from_json.py

# Combined data workflow
update-data: fetch-people fetch-events import-data

# Clean up generated files
clean:
	rm -rf instance
	rm -f data/*.json
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

# Help
help:
	@echo "Available commands:"
	@echo "  install-dev       - Install development dependencies"
	@echo "  develop           - Install package in development mode"
	@echo "  init-db           - Initialize the legacy SQLAlchemy database"
	@echo "  trailbase-download - Download TrailBase binary"
	@echo "  trailbase-init    - Initialize TrailBase configuration"
	@echo "  trailbase-start   - Start TrailBase server"
	@echo "  trailbase-stop    - Stop TrailBase server"
	@echo "  import-csv        - Import CSV data into TrailBase"
	@echo "  run               - Run the Flask application with TrailBase"
	@echo "  run-legacy        - Run the legacy Flask application"
	@echo "  lint              - Run flake8 linting"
	@echo "  format            - Format code with black and isort"
	@echo "  test              - Run tests with pytest"
	@echo "  docs              - Generate documentation"
	@echo "  type-check        - Run mypy type checking"
	@echo "  fetch-people      - Fetch random people from Wikidata"
	@echo "  fetch-events      - Fetch random events from Wikidata"
	@echo "  import-data       - Import data from local JSON files"
	@echo "  update-data       - Run the full fetch and import pipeline"
	@echo "  clean             - Remove generated files (DB, JSON, pycache)"
	@echo ""
	@echo "TrailBase Workflow:"
	@echo "  1. make trailbase-download - Download TrailBase binary"
	@echo "  2. make trailbase-init     - Initialize TrailBase"
	@echo "  3. make trailbase-start    - Start TrailBase server"
	@echo "  4. make update-data        - Fetch and import data"
	@echo "  5. make run                - Run Flask app with TrailBase"
	@echo ""
	@echo "CSV Import Usage:"
	@echo "  make import-csv CSV_FILE=data/sample_people.csv"
	@echo "  make import-csv CSV_FILE=data/sample_people.csv DRY_RUN=1"
	@echo ""
	@echo "Remember to activate your virtual environment first:"
	@echo "  source venv/bin/activate" 