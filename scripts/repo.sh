#!/bin/bash
# Agent repo management CLI — runs against Postgres directly
# Usage: ./scripts/repo.sh <command> [options]

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
Agent repo management CLI

Usage: ./scripts/repo.sh <command> [options]

Commands:
  list [--agent NAME]                              List repos (filterable by agent)
  add --url URL --name NAME --to AGENT --by AGENT [--desc DESCRIPTION]
  remove --url URL --agent AGENT                   Remove a repo assignment
  agent AGENT                                      Show repos assigned to an agent

Examples:
  ./scripts/repo.sh list
  ./scripts/repo.sh list --agent robin
  ./scripts/repo.sh add --url https://github.com/user/repo --name my-repo --to robin --by ino
  ./scripts/repo.sh remove --url https://github.com/user/repo --agent robin
  ./scripts/repo.sh agent robin
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
        where="WHERE r.agent_name = '$agent'"
    fi

    $PSQL -F '|' <<SQL | column -t -s '|'
SELECT r.agent_name, r.name, r.repo_url, r.assigned_by, r.created_at::date
FROM ${S}.agent_repos r
$where
ORDER BY r.agent_name, r.created_at DESC;
SQL
}

cmd_add() {
    local url="" name="" to="" by="" desc=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --url) url="$2"; shift 2;;
            --name) name="$2"; shift 2;;
            --to) to="$2"; shift 2;;
            --by) by="$2"; shift 2;;
            --desc) desc="$2"; shift 2;;
            *) shift;;
        esac
    done

    if [ -z "$url" ] || [ -z "$name" ] || [ -z "$to" ] || [ -z "$by" ]; then
        echo "Usage: repo.sh add --url URL --name NAME --to AGENT --by AGENT [--desc DESCRIPTION]"
        exit 1
    fi

    local desc_val="NULL"
    if [ -n "$desc" ]; then desc_val="'$desc'"; fi

    $PSQL <<SQL
INSERT INTO ${S}.agent_repos (agent_name, repo_url, name, description, assigned_by)
VALUES ('$to', '$url', '$name', $desc_val, '$by')
ON CONFLICT (agent_name, repo_url) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    assigned_by = EXCLUDED.assigned_by
RETURNING name || ' assigned to ' || agent_name || ' (by ' || assigned_by || ')';
SQL
}

cmd_remove() {
    local url="" agent=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --url) url="$2"; shift 2;;
            --agent) agent="$2"; shift 2;;
            *) shift;;
        esac
    done

    if [ -z "$url" ] || [ -z "$agent" ]; then
        echo "Usage: repo.sh remove --url URL --agent AGENT"
        exit 1
    fi

    $PSQL <<SQL
DELETE FROM ${S}.agent_repos
WHERE agent_name = '$agent' AND repo_url = '$url'
RETURNING name || ' removed from ' || agent_name;
SQL
}

cmd_agent() {
    local agent="$1"
    if [ -z "$agent" ]; then echo "Usage: repo.sh agent AGENT"; exit 1; fi

    $PSQL -F '|' <<SQL | column -t -s '|'
SELECT r.name, r.repo_url, COALESCE(r.description, '-'), r.assigned_by, r.created_at::date
FROM ${S}.agent_repos r
WHERE r.agent_name = '$agent'
ORDER BY r.created_at DESC;
SQL
}

# Route command
case "${1:-}" in
    list) shift; cmd_list "$@";;
    add) shift; cmd_add "$@";;
    remove) shift; cmd_remove "$@";;
    agent) shift; cmd_agent "$@";;
    *) usage;;
esac
