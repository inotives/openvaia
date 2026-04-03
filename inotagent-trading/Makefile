# Load .env if it exists
ifneq (,$(wildcard .env))
	include .env
	export
endif

.PHONY: install sync migrate migrate-down migrate-status test lint format

# Setup
install:
	uv sync

sync: install

# Database
migrate:
	uv run dbmate -d db/migrations up

migrate-down:
	uv run dbmate -d db/migrations down

migrate-status:
	uv run dbmate -d db/migrations status

migrate-new:
	@read -p "Migration name: " name; \
	uv run dbmate -d db/migrations new $$name

# Testing
test:
	uv run pytest tests/ -v

# Lint
lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
