#!/bin/bash
# Cron job management CLI — runs against Postgres directly
# Usage: ./scripts/cron.sh <command> [options]

set -e

# Load env
if [ -f .env ]; then
    set -a; source .env; set +a
fi

DB_USER="${POSTGRES_USER:-inotives}"
DB_NAME="${POSTGRES_DB:-inotives}"
S="${PLATFORM_SCHEMA:-platform}"
CONTAINER="${POSTGRES_CONTAINER:-openvaia_postgres}"

PSQL="docker exec -i $CONTAINER psql -U $DB_USER -d $DB_NAME -t -A"

usage() {
    cat <<EOF
Cron job management CLI

Usage: ./scripts/cron.sh <command> [options]

Commands:
  list [--agent NAME]                              List cron jobs (filterable by agent)
  add --name NAME --prompt PROMPT [--agent AGENT] [--interval MINUTES] [--disabled]
  update ID [--prompt PROMPT] [--interval MINUTES] [--enable|--disable]
  remove ID                                        Delete a cron job

Examples:
  ./scripts/cron.sh list
  ./scripts/cron.sh list --agent ino
  ./scripts/cron.sh add --name "crypto_news" --prompt "Summarize today's crypto news" --agent ino --interval 720
  ./scripts/cron.sh add --name "health_report" --prompt "Generate health report" --interval 60
  ./scripts/cron.sh update 3 --interval 360 --disable
  ./scripts/cron.sh remove 3
EOF
    exit 1
}

cmd_list() {
    local agent=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --agent) agent="$2"; shift 2;;
            *) shift;;
        esac
    done

    local where=""
    if [ -n "$agent" ]; then
        where="WHERE agent_name = '$agent' OR agent_name IS NULL"
    fi

    $PSQL -F '|' <<SQL | column -t -s '|'
SELECT id, COALESCE(agent_name, '*'), name, interval_minutes || 'min',
       CASE WHEN enabled THEN 'on' ELSE 'off' END,
       COALESCE(last_run_at::text, 'never'),
       LEFT(prompt, 60) || CASE WHEN LENGTH(prompt) > 60 THEN '...' ELSE '' END
FROM ${S}.cron_jobs
$where
ORDER BY COALESCE(agent_name, ''), name;
SQL
}

cmd_add() {
    local name="" prompt="" agent="" interval="30" enabled="true"
    while [[ $# -gt 0 ]]; do
        case $1 in
            --name) name="$2"; shift 2;;
            --prompt) prompt="$2"; shift 2;;
            --agent) agent="$2"; shift 2;;
            --interval) interval="$2"; shift 2;;
            --disabled) enabled="false"; shift;;
            *) shift;;
        esac
    done

    if [ -z "$name" ] || [ -z "$prompt" ]; then
        echo "Usage: cron.sh add --name NAME --prompt PROMPT [--agent AGENT] [--interval MINUTES] [--disabled]"
        exit 1
    fi

    local agent_val="NULL"
    if [ -n "$agent" ]; then agent_val="'$agent'"; fi

    $PSQL <<SQL
INSERT INTO ${S}.cron_jobs (agent_name, name, prompt, interval_minutes, enabled)
VALUES ($agent_val, '$name', '$prompt', $interval, $enabled)
ON CONFLICT (COALESCE(agent_name, ''), name) DO UPDATE SET
    prompt = EXCLUDED.prompt,
    interval_minutes = EXCLUDED.interval_minutes,
    enabled = EXCLUDED.enabled,
    updated_at = NOW()
RETURNING 'Created cron job: ' || name || ' (id=' || id || ', every ' || interval_minutes || 'min, agent=' || COALESCE(agent_name, '*') || ')';
SQL
}

cmd_update() {
    local id="$1"; shift
    if [ -z "$id" ]; then echo "Usage: cron.sh update ID [options]"; exit 1; fi

    local sets=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --prompt) sets="$sets prompt = '$2',"; shift 2;;
            --interval) sets="$sets interval_minutes = $2,"; shift 2;;
            --enable) sets="$sets enabled = true,"; shift;;
            --disable) sets="$sets enabled = false,"; shift;;
            *) shift;;
        esac
    done

    if [ -z "$sets" ]; then echo "Nothing to update"; exit 1; fi

    # Add updated_at and strip trailing comma
    sets="$sets updated_at = NOW()"

    $PSQL <<SQL
UPDATE ${S}.cron_jobs SET $sets WHERE id = $id
RETURNING 'Updated job ' || id || ': ' || name || ' (agent=' || COALESCE(agent_name, '*') || ', every ' || interval_minutes || 'min, enabled=' || enabled || ')';
SQL
}

cmd_remove() {
    local id="$1"
    if [ -z "$id" ]; then echo "Usage: cron.sh remove ID"; exit 1; fi

    $PSQL <<SQL
DELETE FROM ${S}.cron_jobs WHERE id = $id
RETURNING 'Removed job ' || id || ': ' || name || ' (agent=' || COALESCE(agent_name, '*') || ')';
SQL
}

# Route command
case "${1:-}" in
    list) shift; cmd_list "$@";;
    add) shift; cmd_add "$@";;
    update) shift; cmd_update "$@";;
    remove) shift; cmd_remove "$@";;
    *) usage;;
esac
