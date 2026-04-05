.PHONY: deploy deploy-all start stop restart down ps logs ui ui-logs ui-dev ui-dev-restart ui-dev-stop ui-dev-build shell test bootstrap build build-base task-list task-get task-create task-update task-summary task-board repo-list repo-add repo-remove repo-agent inotagent-test trading-start trading-stop trading-status trading-logs trading-build trading-migrate trading-seed trading-sync-coingecko trading-fetch-daily trading-test

build-base:
	docker build -f inotagent/Dockerfile -t inotagent-base .

build: build-base
	docker compose build $(AGENT)

# First-time deploy (build + start): make deploy or make deploy AGENT=ino
deploy: build
	docker compose up -d $(AGENT)

# Deploy with local Postgres container
deploy-all: build
	docker compose --profile infra up -d $(AGENT)

# Start existing container(s): make start or make start AGENT=ino
start:
	docker compose start $(AGENT)

# Stop container(s) without removing: make stop or make stop AGENT=ino
stop:
	docker compose stop $(AGENT)

# Restart container(s): make restart or make restart AGENT=ino
restart:
	docker compose restart $(AGENT)

# Start only Postgres (no agents or UI)
db:
	docker compose --profile infra up -d postgres

# Wipe DB schema only (no rebuild): make wipe-db
wipe-db:
	docker compose --profile infra down
	docker compose --profile infra up -d postgres
	@echo "Waiting for Postgres to be healthy..."
	@until docker exec openvaia_postgres pg_isready -U inotives -q 2>/dev/null; do sleep 1; done
	docker exec openvaia_postgres psql -U inotives -d inotives -c "DROP SCHEMA IF EXISTS $${PLATFORM_SCHEMA:-openvaia} CASCADE; DROP SCHEMA IF EXISTS trading_platform CASCADE; DELETE FROM public.schema_migrations WHERE TRUE;" 2>/dev/null || true
	docker compose --profile infra down
	@echo "DB wiped. Run 'make deploy-all' to rebuild."

# Clean slate: wipe DB + rebuild + wait for migrations + import skills
clean-slate: wipe-db
	docker compose --profile infra up -d postgres
	@echo "Waiting for Postgres..."
	@until docker exec openvaia_postgres pg_isready -U inotives -q 2>/dev/null; do sleep 1; done
	$(MAKE) local-migrate
	$(MAKE) build
	docker compose --profile infra build
	docker compose --profile infra up -d
	@sleep 5
	$(MAKE) import-skills
	$(MAKE) seed-tasks
	$(MAKE) seed-chains
	$(MAKE) trading-setup

# Tear down everything (removes containers)
down:
	docker compose --profile infra down

ps:
	docker compose --profile infra ps

# Docker container logs (last 40 lines): make logs AGENT=ino
logs:
	docker compose logs --tail 40 $(AGENT)

# Docker container logs (live follow): make logs-follow AGENT=ino
logs-follow:
	docker compose logs -f $(AGENT)

# --- UI ---

# Start the admin UI: make ui
ui:
	docker compose up -d --build ui

# UI logs
ui-logs:
	docker compose logs -f ui

# --- UI local dev ---

UI_PORT ?= 3310

# Install UI dependencies: make ui-install
ui-install:
	cd ui && npm install

# --- UI local dev ---

# Start UI dev server: make ui-dev
ui-dev:
	cd ui && npx next dev -p $(UI_PORT)

# Restart UI dev server: make ui-dev-restart
ui-dev-restart:
	@lsof -ti:$(UI_PORT) 2>/dev/null | xargs kill -9 2>/dev/null || true
	@rm -rf ui/.next
	cd ui && npx next dev -p $(UI_PORT)

# Stop UI dev server: make ui-dev-stop
ui-dev-stop:
	@lsof -ti:$(UI_PORT) 2>/dev/null | xargs kill -9 2>/dev/null && echo "Stopped UI dev server on port $(UI_PORT)" || echo "No UI dev server running on port $(UI_PORT)"

# Build UI (check for errors): make ui-dev-build
ui-dev-build:
	cd ui && npx next build

# --- Agent debugging ---

# Shell into agent container: make shell AGENT=ino
shell:
	docker compose exec agent_$(AGENT) bash

# --- Task management ---

# List tasks: make task-list or make task-list AGENT=robin STATUS=todo
task-list:
	@./scripts/task.sh list $(if $(AGENT),--agent $(AGENT)) $(if $(STATUS),--status $(STATUS))

# Get task details: make task-get KEY=INO-001
task-get:
	@./scripts/task.sh get $(KEY)

# Create task: make task-create TITLE="Build auth" BY=ino TO=robin PRIORITY=high REPO=inotives_cryptos
# Create mission (unassigned): make task-create TITLE="Research DeFi yields" BY=boss TAGS=research,defi
task-create:
	@./scripts/task.sh create --title "$(TITLE)" --by $(BY) $(if $(TO),--to $(TO)) $(if $(PRIORITY),--priority $(PRIORITY)) $(if $(PARENT),--parent $(PARENT)) $(if $(TAGS),--tags $(TAGS)) $(if $(REPO),--repo $(REPO)) $(if $(STATUS),--status $(STATUS))

# Update task: make task-update KEY=INO-001 STATUS=done RESULT="Completed"
task-update:
	@./scripts/task.sh update $(KEY) $(if $(STATUS),--status $(STATUS)) $(if $(RESULT),--result "$(RESULT)") $(if $(TO),--to $(TO)) $(if $(PRIORITY),--priority $(PRIORITY))

# Task summary: make task-summary or make task-summary AGENT=robin
task-summary:
	@./scripts/task.sh summary $(AGENT)

# Kanban board view: make task-board
task-board:
	@./scripts/task.sh board

# --- Repo management ---

# List repos: make repo-list or make repo-list AGENT=robin
repo-list:
	@./scripts/repo.sh list $(if $(AGENT),--agent $(AGENT))

# Add repo: make repo-add URL=https://github.com/user/repo NAME=my-repo TO=robin BY=ino
repo-add:
	@./scripts/repo.sh add --url "$(URL)" --name "$(NAME)" --to $(TO) --by $(BY) $(if $(DESC),--desc "$(DESC)")

# Remove repo: make repo-remove URL=https://github.com/user/repo AGENT=robin
repo-remove:
	@./scripts/repo.sh remove --url "$(URL)" --agent $(AGENT)

# Show agent's repos: make repo-agent AGENT=robin
repo-agent:
	@./scripts/repo.sh agent $(AGENT)

# --- Cron job management ---

# List cron jobs: make cron-list or make cron-list AGENT=ino
cron-list:
	@./scripts/cron.sh list $(if $(AGENT),--agent $(AGENT))

# Add cron job: make cron-add NAME="crypto_news" PROMPT="Summarize crypto news" AGENT=ino INTERVAL=720
# Add global job: make cron-add NAME="health_report" PROMPT="Generate report" INTERVAL=60
cron-add:
	@./scripts/cron.sh add --name "$(NAME)" --prompt "$(PROMPT)" $(if $(AGENT),--agent $(AGENT)) $(if $(INTERVAL),--interval $(INTERVAL)) $(if $(DISABLED),--disabled)

# Update cron job: make cron-update ID=3 INTERVAL=360 ENABLED=false
cron-update:
	@./scripts/cron.sh update $(ID) $(if $(PROMPT),--prompt "$(PROMPT)") $(if $(INTERVAL),--interval $(INTERVAL)) $(if $(filter true,$(ENABLED)),--enable) $(if $(filter false,$(ENABLED)),--disable)

# Remove cron job: make cron-remove ID=3
cron-remove:
	@./scripts/cron.sh remove $(ID)

# Import skills from inotagent/skills/ into DB (skip existing)
import-skills:
	POSTGRES_HOST=localhost POSTGRES_PORT=$${EXTERNAL_POSTGRES_PORT:-5445} POSTGRES_USER=inotives POSTGRES_PASSWORD=$$(grep POSTGRES_PASSWORD .env | cut -d= -f2) POSTGRES_DB=inotives PLATFORM_SCHEMA=$${PLATFORM_SCHEMA:-openvaia} python3 scripts/import-skills.py

# Reset a skill to file version: make reset-skill NAME=code_review
reset-skill:
	POSTGRES_HOST=localhost POSTGRES_PORT=$${EXTERNAL_POSTGRES_PORT:-5445} POSTGRES_USER=inotives POSTGRES_PASSWORD=$$(grep POSTGRES_PASSWORD .env | cut -d= -f2) POSTGRES_DB=inotives PLATFORM_SCHEMA=$${PLATFORM_SCHEMA:-openvaia} python3 scripts/import-skills.py --reset $(NAME)

# Force re-import all skills (delete + re-insert)
reimport-skills:
	POSTGRES_HOST=localhost POSTGRES_PORT=$${EXTERNAL_POSTGRES_PORT:-5445} POSTGRES_USER=inotives POSTGRES_PASSWORD=$$(grep POSTGRES_PASSWORD .env | cut -d= -f2) POSTGRES_DB=inotives PLATFORM_SCHEMA=$${PLATFORM_SCHEMA:-openvaia} python3 scripts/import-skills.py --force

# Seed recurring tasks for proactive agent behavior
seed-tasks:
	POSTGRES_HOST=localhost POSTGRES_PORT=$${EXTERNAL_POSTGRES_PORT:-5445} POSTGRES_USER=inotives POSTGRES_PASSWORD=$$(grep POSTGRES_PASSWORD .env | cut -d= -f2) POSTGRES_DB=inotives PLATFORM_SCHEMA=$${PLATFORM_SCHEMA:-openvaia} python3 scripts/seed-recurring-tasks.py

# Seed skill chains for dynamic skill equipping
seed-chains:
	POSTGRES_HOST=localhost POSTGRES_PORT=$${EXTERNAL_POSTGRES_PORT:-5445} POSTGRES_USER=inotives POSTGRES_PASSWORD=$$(grep POSTGRES_PASSWORD .env | cut -d= -f2) POSTGRES_DB=inotives PLATFORM_SCHEMA=$${PLATFORM_SCHEMA:-openvaia} python3 scripts/seed-skill-chains.py

# ============================================================
# Local Development (without Docker)
# ============================================================

# Prerequisites: Python 3.12, uv, Postgres running, dbmate installed
# Usage:
#   make db                    # start Postgres (Docker)
#   make local-setup           # first time: install deps + migrate + seed
#   make local-run AGENT=ino   # run single agent
#   make local-run-multi       # run multi-agent (ino,robin)

DB_ENV = POSTGRES_HOST=localhost POSTGRES_PORT=$${EXTERNAL_POSTGRES_PORT:-5445} POSTGRES_USER=inotives POSTGRES_PASSWORD=$$(grep POSTGRES_PASSWORD .env | cut -d= -f2) POSTGRES_DB=inotives PLATFORM_SCHEMA=$${PLATFORM_SCHEMA:-openvaia}

# Install Python dependencies locally via uv
local-install:
	cd inotagent && uv sync --no-dev

# Run DB migrations locally (requires dbmate)
local-migrate:
	@DB_URL="postgresql://inotives:$$(grep POSTGRES_PASSWORD .env | cut -d= -f2)@localhost:$${EXTERNAL_POSTGRES_PORT:-5445}/inotives?sslmode=disable"; \
	uv run dbmate -d infra/postgres/migrations --url "$$DB_URL" --no-dump-schema up

# Full local setup: install + migrate + import skills + seed tasks + seed chains
local-setup: local-install local-migrate import-skills seed-tasks seed-chains trading-setup
	@echo "Local setup complete. Run: make local-run AGENT=ino"

# Run single agent locally
# Exports DB vars + agent env, DB vars set LAST to override Docker defaults
local-run:
	@if [ -z "$(AGENT)" ]; then echo "Usage: make local-run AGENT=ino"; exit 1; fi
	@echo "Starting $(AGENT) locally (Postgres on localhost:$${EXTERNAL_POSTGRES_PORT:-5445})..."
	@export POSTGRES_HOST=localhost; \
	export POSTGRES_PORT=$${EXTERNAL_POSTGRES_PORT:-5445}; \
	export POSTGRES_USER=inotives; \
	export POSTGRES_PASSWORD=$$(grep POSTGRES_PASSWORD .env | cut -d= -f2); \
	export POSTGRES_DB=inotives; \
	export PLATFORM_SCHEMA=$${PLATFORM_SCHEMA:-openvaia}; \
	set -a; . agents/$(AGENT)/.env 2>/dev/null; set +a; \
	export POSTGRES_HOST=localhost; \
	export POSTGRES_PORT=$${EXTERNAL_POSTGRES_PORT:-5445}; \
	cd inotagent && uv run python -m inotagent --agent-dir ../agents/$(AGENT)

# Run multi-agent locally
local-run-multi:
	@echo "Starting agents locally (Postgres on localhost:$${EXTERNAL_POSTGRES_PORT:-5445})..."
	@export POSTGRES_HOST=localhost; \
	export POSTGRES_PORT=$${EXTERNAL_POSTGRES_PORT:-5445}; \
	export POSTGRES_USER=inotives; \
	export POSTGRES_PASSWORD=$$(grep POSTGRES_PASSWORD .env | cut -d= -f2); \
	export POSTGRES_DB=inotives; \
	export PLATFORM_SCHEMA=$${PLATFORM_SCHEMA:-openvaia}; \
	cd inotagent && uv run python -m inotagent --agents $${AGENTS:-ino,robin}

# Stop locally running agents
local-stop:
	@pkill -f 'python -m inotagent' 2>/dev/null && echo "Local agent(s) stopped" || echo "No local agents running"

# Run project integrity tests
test:
	uv run pytest tests/ -v

# Run inotagent unit tests
inotagent-test:
	cd inotagent && uv run pytest tests/ -v

# Create new agent: make create-agent NAME=kai EMAIL=kai@inotives.ai
create-agent:
	@./scripts/create-agent.sh $(NAME) $(if $(EMAIL),--email $(EMAIL))

bootstrap:
	./scripts/bootstrap.sh

# ─── Trading Toolkit ───────────────────────────────────────────

trading-build:
	docker compose build poller-public poller-private poller-ta

trading-poller-start:
	@echo "Starting pollers locally (Postgres on localhost:$${EXTERNAL_POSTGRES_PORT:-5445})..."
	@cd inotagent-trading && $(TRADING_DB_ENV) nohup uv run python -m poller.public --interval 60 > /tmp/poller-public.log 2>&1 & echo $$! > /tmp/poller-public.pid
	@cd inotagent-trading && $(TRADING_DB_ENV) nohup uv run python -m poller.private --interval 60 > /tmp/poller-private.log 2>&1 & echo $$! > /tmp/poller-private.pid
	@cd inotagent-trading && $(TRADING_DB_ENV) nohup uv run python -m poller.ta --interval 60 > /tmp/poller-ta.log 2>&1 & echo $$! > /tmp/poller-ta.pid
	@sleep 2 && echo "Pollers started" && $(MAKE) trading-poller-status

trading-poller-stop:
	@for p in public private ta; do \
		if [ -f /tmp/poller-$$p.pid ]; then \
			kill $$(cat /tmp/poller-$$p.pid) 2>/dev/null && echo "Stopped poller-$$p" || echo "poller-$$p not running"; \
			rm -f /tmp/poller-$$p.pid; \
		fi; \
	done

trading-poller-status:
	@for p in public private ta; do \
		if [ -f /tmp/poller-$$p.pid ] && kill -0 $$(cat /tmp/poller-$$p.pid) 2>/dev/null; then \
			echo "poller-$$p: running (PID $$(cat /tmp/poller-$$p.pid))"; \
		else \
			echo "poller-$$p: stopped"; \
		fi; \
	done

trading-poller-logs:
	@tail -20 /tmp/poller-public.log /tmp/poller-private.log /tmp/poller-ta.log 2>/dev/null || echo "No poller logs"

# Docker pollers (alternative — use when deploying fully in Docker)
trading-start:
	docker compose --profile trading up -d

trading-stop:
	docker compose --profile trading stop

trading-migrate: local-migrate

TRADING_DB_ENV = POSTGRES_HOST=localhost POSTGRES_PORT=$${EXTERNAL_POSTGRES_PORT:-5445} POSTGRES_USER=inotives POSTGRES_PASSWORD=$$(grep POSTGRES_PASSWORD .env | cut -d= -f2) POSTGRES_DB=inotives TRADING_SCHEMA=trading_platform
TRADING_CG_ENV = COINGECKO_API_KEY=$$(grep COINGECKO_API_KEY agents/robin/.env 2>/dev/null | head -1 | cut -d= -f2)

trading-seed:
	$(TRADING_DB_ENV) python3 scripts/seed-trading.py

trading-sync-coingecko:
	@echo "Syncing CoinGecko coin universe + platforms..."
	@cd inotagent-trading && $(TRADING_DB_ENV) $(TRADING_CG_ENV) uv run python -m cli.market sync-coingecko

trading-seed-ohlcv:
	@cd inotagent-trading && for pair in "BTC btc" "ETH eth" "SOL sol" "XRP xrp"; do \
		set -- $$pair; \
		CSV="data/seeds/$${2}_historical_data.csv"; \
		if [ -f "$$CSV" ]; then \
			echo "Seeding $$1 from $$CSV..."; \
			$(TRADING_DB_ENV) uv run python -m cli.market seed-daily --asset $$1 --venue coinmarketcap --file $$CSV; \
		else \
			echo "SKIP $$1 — $$CSV not found"; \
		fi; \
	done

trading-fetch-daily: ## Fetch daily OHLCV from CoinGecko. DAYS=1|7|14|30 (free), 90|180|365 (paid)
	@echo "Fetching latest daily OHLCV from CoinGecko ($(or $(DAYS),7) days)..."
	@cd inotagent-trading && $(TRADING_DB_ENV) $(TRADING_CG_ENV) uv run python -m cli.market fetch-daily --days $(or $(DAYS),7)

trading-backfill-ta:
	@cd inotagent-trading && for asset in BTC ETH SOL XRP; do \
		echo "Backfilling TA for $$asset..."; \
		$(TRADING_DB_ENV) uv run python -m cli.market backfill-daily-ta --asset $$asset; \
	done

trading-setup: trading-seed trading-sync-coingecko trading-seed-ohlcv trading-fetch-daily trading-backfill-ta
	@echo "Trading setup complete: reference data + CoinGecko universe + OHLCV + TA indicators"

trading-test:
	cd inotagent-trading && make test
