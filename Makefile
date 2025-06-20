# Makefile for Timeline App

.PHONY: run lint format test docs type-check

run:
	flask run

lint:
	flake8 thyme sample_data.py

format:
	black thyme sample_data.py
	isort thyme sample_data.py

test:
	pytest

docs:
	cd docs && make html

type-check:
	mypy thyme sample_data.py

# Development workflow
dev: format lint type-check test 