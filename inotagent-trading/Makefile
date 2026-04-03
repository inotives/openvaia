# Load .env if it exists
ifneq (,$(wildcard .env))
	include .env
	export
endif

.PHONY: install sync test lint format

# Setup
install:
	uv sync

sync: install

# Testing
test:
	uv run pytest tests/ -v

# Lint
lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .

# Migrations are managed from the repo root:
#   make trading-migrate  (from repo root)
