#!/usr/bin/env bash
set -euo pipefail

AGENT_NAME="${AGENT_NAME:?AGENT_NAME required}"
echo "=== inotagent boot: ${AGENT_NAME} ==="

# Step 1: Git credentials
GIT_TOKEN="${GITHUB_TOKEN_PATS:-${GITHUB_TOKEN:-}}"
if [[ -n "${GIT_TOKEN}" ]]; then
    echo "Configuring git credentials..."
    git config --global url."https://${GIT_TOKEN}@github.com/".insteadOf "https://github.com/"
    git config --global user.name "${AGENT_NAME}"
    git config --global user.email "${GIT_EMAIL:-${AGENT_NAME}@inotives.com}"
fi

# Step 2: Ensure database exists
echo "Ensuring database '${POSTGRES_DB}' exists..."
python3 -c "
import psycopg
conn = psycopg.connect(
    host='${POSTGRES_HOST}',
    port=${POSTGRES_PORT:-5432},
    user='${POSTGRES_USER}',
    password='${POSTGRES_PASSWORD}',
    dbname='postgres',
    autocommit=True,
)
try:
    conn.execute('CREATE DATABASE \"${POSTGRES_DB}\"')
    print('Created database ${POSTGRES_DB}')
except psycopg.errors.DuplicateDatabase:
    print('Database ${POSTGRES_DB} already exists')
conn.close()
"

# Step 3: Migrations — run from host via 'make local-migrate' before starting containers.
# Not run here to avoid schema_migrations sync issues between host and container dbmate.
echo "Skipping migrations (run 'make local-migrate' from host before deploy)"

# Step 4: Bootstrap
# Multi-agent mode: AGENTS env var contains comma-separated names
# Single-agent mode: AGENT_NAME env var
if [[ -n "${AGENTS:-}" ]]; then
    echo "Multi-agent mode: ${AGENTS}"
    IFS=',' read -ra AGENT_LIST <<< "${AGENTS}"
    for agent in "${AGENT_LIST[@]}"; do
        agent=$(echo "$agent" | xargs)  # trim whitespace
        echo "Running bootstrap for ${agent}..."
        AGENT_NAME="${agent}" python3 -m inotagent.bootstrap
    done

    echo "Starting inotagent for [${AGENTS}]..."
    exec python3 -m inotagent \
        --agents "${AGENTS}" \
        --agents-root "/app/agents" \
        --log-level "${LOG_LEVEL:-INFO}"
else
    echo "Running bootstrap for ${AGENT_NAME}..."
    python3 -m inotagent.bootstrap

    echo "Starting inotagent for ${AGENT_NAME}..."
    exec python3 -m inotagent \
        --agent-dir "/app/agents/${AGENT_NAME}" \
        --log-level "${LOG_LEVEL:-INFO}"
fi
