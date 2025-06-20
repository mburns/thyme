# Makefile for Timeline App

.PHONY: run lint format test docs type-check import-wikidata import-wikidata-sparql install-dev

# Check if virtual environment is activated
check-venv:
	@if [ -z "$$VIRTUAL_ENV" ]; then \
		echo "Error: Virtual environment not activated. Please run: source venv/bin/activate"; \
		exit 1; \
	fi

# Install development dependencies
install-dev: check-venv
	pip install -r requirements.txt

# Run the application
run: check-venv
	flask run

# Lint the code
lint: check-venv
	flake8 thyme sample_data.py wikidata_import.py wikidata_sparql_import.py

# Format the code
format: check-venv
	black thyme sample_data.py wikidata_import.py wikidata_sparql_import.py
	isort thyme sample_data.py wikidata_import.py wikidata_sparql_import.py

# Run tests
test: check-venv
	pytest

# Generate documentation
docs: check-venv
	cd docs && make html

# Type checking
type-check: check-venv
	mypy thyme sample_data.py wikidata_import.py wikidata_sparql_import.py

# Wikidata import commands
import-wikidata: check-venv
	python wikidata_import.py

import-wikidata-sparql: check-venv
	python wikidata_sparql_import.py

# Development workflow
dev: format lint type-check test

# Help
help:
	@echo "Available commands:"
	@echo "  install-dev      - Install development dependencies"
	@echo "  run             - Run the Flask application"
	@echo "  lint            - Run flake8 linting"
	@echo "  format          - Format code with black and isort"
	@echo "  test            - Run tests with pytest"
	@echo "  docs            - Generate documentation"
	@echo "  type-check      - Run mypy type checking"
	@echo "  import-wikidata - Import events from Wikidata (API)"
	@echo "  import-wikidata-sparql - Import events from Wikidata (SPARQL)"
	@echo "  dev             - Run full development workflow"
	@echo ""
	@echo "Remember to activate your virtual environment first:"
	@echo "  source venv/bin/activate" 