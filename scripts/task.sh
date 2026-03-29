#!/bin/bash
# Task management CLI — runs against Postgres directly
# Usage: ./scripts/task.sh <command> [options]

set -e

# Load env
if [ -f .env ]; then
    set -a; source .env; set +a
fi

DB_USER="${POSTGRES_USER:-inotives}"
DB_NAME="${POSTGRES_DB:-inotives}"
S="${PLATFORM_SCHEMA:-platform}"
CONTAINER="${POSTGRES_CONTAINER:-openvaia_postgres}"

# Use docker exec to run psql inside the Postgres container
PSQL="docker exec -i $CONTAINER psql -U $DB_USER -d $DB_NAME -t -A"

usage() {
    cat <<EOF
Task management CLI

Usage: ./scripts/task.sh <command> [options]

Commands:
  list [--agent NAME] [--status STATUS]   List tasks (filterable)
  get KEY                                 Show task details
  create --title TITLE --by AGENT [--to AGENT] [--priority PRIORITY] [--parent KEY] [--tags TAGS] [--repo NAME] [--status STATUS]
  update KEY --status STATUS [--result TEXT]
  summary [AGENT]                         Task counts by status
  board                                   Quick kanban view

Examples:
  ./scripts/task.sh list
  ./scripts/task.sh list --agent robin --status todo,in_progress
  ./scripts/task.sh create --title "Build auth module" --by ino --to robin --priority high --repo inotives_cryptos
  ./scripts/task.sh create --title "Research DeFi yields" --by boss --tags research,defi  # mission board
  ./scripts/task.sh update INO-001 --status in_progress
  ./scripts/task.sh update INO-001 --status done --result "Completed successfully"
  ./scripts/task.sh board
EOF
    exit 1
}

cmd_list() {
    local agent="" status=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --agent) agent="$2"; shift 2;;
            --status) status="$2"; shift 2;;
            *) shift;;
        esac
    done

    local where=""
    if [ -n "$agent" ]; then
        where="WHERE (t.assigned_to = '$agent' OR t.created_by = '$agent')"
    fi
    if [ -n "$status" ]; then
        local in_list=$(echo "$status" | sed "s/,/','/g")
        if [ -n "$where" ]; then
            where="$where AND t.status IN ('$in_list')"
        else
            where="WHERE t.status IN ('$in_list')"
        fi
    fi

    $PSQL -F '|' <<SQL | column -t -s '|'
SELECT t.key, t.title, t.status, t.priority, COALESCE(t.assigned_to, '-') AS assigned, t.created_by,
       COALESCE(p.key, '-') AS parent, COALESCE(r.name, '-') AS repo
FROM ${S}.tasks t
LEFT JOIN ${S}.tasks p ON t.parent_task_id = p.id
LEFT JOIN ${S}.agent_repos r ON t.repo_id = r.id
$where
ORDER BY
    CASE t.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END,
    t.created_at DESC
LIMIT 50;
SQL
}

cmd_get() {
    local key="$1"
    if [ -z "$key" ]; then echo "Usage: task.sh get KEY"; exit 1; fi

    $PSQL <<SQL
SELECT
    t.key || ' — ' || t.title AS task,
    'Status: ' || t.status || '  Priority: ' || t.priority AS info,
    'Assigned: ' || COALESCE(t.assigned_to, '-') || '  Created by: ' || t.created_by AS people,
    'Parent: ' || COALESCE(p.key, '-') || '  Tags: ' || COALESCE(array_to_string(t.tags, ', '), '-') AS meta,
    'Repo: ' || COALESCE(r.name, '-') || '  URL: ' || COALESCE(r.repo_url, '-') AS repo,
    'Created: ' || t.created_at::text || '  Updated: ' || t.updated_at::text AS dates,
    COALESCE('Description: ' || t.description, '') AS description,
    COALESCE('Result: ' || t.result, '') AS result
FROM ${S}.tasks t
LEFT JOIN ${S}.tasks p ON t.parent_task_id = p.id
LEFT JOIN ${S}.agent_repos r ON t.repo_id = r.id
WHERE t.key = '$key';
SQL

    # Show subtasks
    local subtasks=$($PSQL -F '|' <<SQL
SELECT key, title, status, priority, COALESCE(assigned_to, '-')
FROM ${S}.tasks
WHERE parent_task_id = (SELECT id FROM ${S}.tasks WHERE key = '$key')
ORDER BY created_at;
SQL
)
    if [ -n "$subtasks" ]; then
        echo ""
        echo "Subtasks:"
        echo "$subtasks" | column -t -s '|'
    fi
}

cmd_create() {
    local title="" by="" to="" priority="medium" parent="" tags="" repo="" status=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            --title) title="$2"; shift 2;;
            --by) by="$2"; shift 2;;
            --to) to="$2"; shift 2;;
            --priority) priority="$2"; shift 2;;
            --parent) parent="$2"; shift 2;;
            --tags) tags="$2"; shift 2;;
            --repo) repo="$2"; shift 2;;
            --status) status="$2"; shift 2;;
            *) shift;;
        esac
    done

    if [ -z "$title" ] || [ -z "$by" ]; then
        echo "Usage: task.sh create --title TITLE --by AGENT [--to AGENT] [--priority PRIORITY] [--repo NAME]"
        exit 1
    fi

    local prefix=$(echo "$by" | head -c 3 | tr '[:lower:]' '[:upper:]')
    local seq=$($PSQL -c "SELECT nextval('${S}.task_key_seq')")
    local key=$(printf "%s-%03d" "$prefix" "$seq")

    local parent_id="NULL"
    if [ -n "$parent" ]; then
        parent_id="(SELECT id FROM ${S}.tasks WHERE key = '$parent')"
    fi

    local to_val="NULL"
    if [ -n "$to" ]; then to_val="'$to'"; fi

    local tag_array="'{}'::text[]"
    if [ -n "$tags" ]; then
        tag_array="ARRAY[$(echo "$tags" | sed "s/,/','/g" | sed "s/^/'/" | sed "s/$/'/" )]"
    fi

    local repo_id="NULL"
    if [ -n "$repo" ]; then
        repo_id="(SELECT id FROM ${S}.agent_repos WHERE name = '$repo' LIMIT 1)"
    fi

    # Default status: todo if assigned, backlog if unassigned (mission board)
    if [ -z "$status" ]; then
        if [ -n "$to" ]; then status="todo"; else status="backlog"; fi
    fi

    # Parse schedule:* tag into recurrence_minutes and schedule_at
    local recurrence="NULL"
    local schedule_at="NULL"
    if [ -n "$tags" ]; then
        for tag in $(echo "$tags" | tr ',' ' '); do
            local base="${tag%%@*}"
            local at_time="${tag#*@}"
            if [ "$at_time" = "$tag" ]; then at_time=""; fi
            case "$base" in
                schedule:5m) recurrence=5;;
                schedule:15m) recurrence=15;;
                schedule:30m) recurrence=30;;
                schedule:hourly) recurrence=60;;
                schedule:4h) recurrence=240;;
                schedule:12h) recurrence=720;;
                schedule:daily) recurrence=1440;;
                schedule:weekly) recurrence=10080;;
                schedule:monthly) recurrence=-1;;
            esac
            if [ -n "$at_time" ]; then schedule_at="'$at_time'"; fi
        done
    fi

    $PSQL <<SQL
INSERT INTO ${S}.tasks (key, title, created_by, assigned_to, priority, parent_task_id, tags, repo_id, status, recurrence_minutes, schedule_at)
VALUES ('$key', '$title', '$by', $to_val, '$priority', $parent_id, $tag_array, $repo_id, '$status', $recurrence, $schedule_at)
RETURNING key || ' created (' || status || ', ' || priority || ', assigned to ' || COALESCE(assigned_to, 'mission board') || ')';
SQL
}

cmd_update() {
    local key="$1"; shift
    if [ -z "$key" ]; then echo "Usage: task.sh update KEY --status STATUS [--result TEXT]"; exit 1; fi

    local sets="updated_at = NOW()"
    while [[ $# -gt 0 ]]; do
        case $1 in
            --status)
                sets="$sets, status = '$2'"
                if [ "$2" = "done" ]; then sets="$sets, last_completed_at = NOW()"; fi
                shift 2;;
            --result) sets="$sets, result = '$2'"; shift 2;;
            --to) sets="$sets, assigned_to = '$2'"; shift 2;;
            --priority) sets="$sets, priority = '$2'"; shift 2;;
            *) shift;;
        esac
    done

    $PSQL <<SQL
UPDATE ${S}.tasks SET $sets WHERE key = '$key'
RETURNING key || ' → ' || status || ' (updated)';
SQL
}

cmd_summary() {
    local agent="$1"
    local where=""
    if [ -n "$agent" ]; then
        where="WHERE assigned_to = '$agent' OR created_by = '$agent'"
    fi

    $PSQL -F '|' <<SQL | column -t -s '|'
SELECT status, COUNT(*) AS count
FROM ${S}.tasks
$where
GROUP BY status
ORDER BY
    CASE status WHEN 'backlog' THEN 0 WHEN 'todo' THEN 1 WHEN 'in_progress' THEN 2
    WHEN 'review' THEN 3 WHEN 'done' THEN 4 WHEN 'blocked' THEN 5 END;
SQL
}

cmd_board() {
    echo "=== KANBAN BOARD ==="
    for status in backlog todo in_progress review done blocked; do
        local label=$(echo "$status" | tr '_' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1')
        local tasks=$($PSQL -F '  ' <<SQL
SELECT t.key, '[' || t.priority || ']', t.title, COALESCE('→ ' || t.assigned_to, '')
FROM ${S}.tasks t
WHERE t.status = '$status'
ORDER BY
    CASE t.priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END;
SQL
)
        local count=$($PSQL -c "SELECT COUNT(*) FROM ${S}.tasks WHERE status = '$status'")
        echo ""
        echo "--- $label ($count) ---"
        if [ -n "$tasks" ]; then
            echo "$tasks"
        else
            echo "  (empty)"
        fi
    done
}

# Route command
case "${1:-}" in
    list) shift; cmd_list "$@";;
    get) shift; cmd_get "$@";;
    create) shift; cmd_create "$@";;
    update) shift; cmd_update "$@";;
    summary) shift; cmd_summary "$@";;
    board) shift; cmd_board "$@";;
    *) usage;;
esac
