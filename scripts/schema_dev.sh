#!/bin/bash
# Dev schema utility — snapshot, test migrations, cleanup
# Usage: ./scripts/schema_dev.sh <command> [options]
#
# Designed to run INSIDE agent containers (has psycopg2, dbmate, no psql).

set -e

# Load env
if [ -f .env ]; then
    set -a; source .env; set +a
fi

DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-inotives}"
DB_PASS="${POSTGRES_PASSWORD}"
DB_NAME="${POSTGRES_DB:-inotives}"

usage() {
    cat <<EOF
Dev schema utility — safe migration testing

Usage: ./scripts/schema_dev.sh <command> [options]

Commands:
  snapshot <schema>              Clone schema structure into <schema>_dev (no data)
  test <schema> <migration>      Run migration up+down against <schema>_dev
  verify <schema>                Show tables and columns in <schema>_dev
  cleanup <schema>               Drop <schema>_dev schema

Examples:
  ./scripts/schema_dev.sh snapshot openvaia
  ./scripts/schema_dev.sh test openvaia infra/postgres/migrations/20260315_add_email.sql
  ./scripts/schema_dev.sh verify openvaia
  ./scripts/schema_dev.sh cleanup openvaia
EOF
    exit 1
}

run_sql() {
    python3 -c "
import psycopg2, sys
conn = psycopg2.connect(
    host='${DB_HOST}', port=${DB_PORT},
    user='${DB_USER}', password='${DB_PASS}',
    dbname='${DB_NAME}'
)
conn.autocommit = True
cur = conn.cursor()
cur.execute(sys.stdin.read())
try:
    for row in cur.fetchall():
        print('|'.join(str(c) for c in row))
except psycopg2.ProgrammingError:
    pass
cur.close()
conn.close()
" <<< "$1"
}

cmd_snapshot() {
    local schema="$1"
    if [ -z "$schema" ]; then echo "Usage: schema_dev.sh snapshot <schema>"; exit 1; fi

    local dev="${schema}_dev"

    echo "Snapshotting ${schema} -> ${dev}..."

    # Drop dev schema if it exists, then create fresh
    run_sql "DROP SCHEMA IF EXISTS ${dev} CASCADE;"
    run_sql "CREATE SCHEMA ${dev};"

    # Get all tables and recreate their structure in dev schema
    local tables
    tables=$(run_sql "
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = '${schema}' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    ")

    if [ -z "$tables" ]; then
        echo "No tables found in ${schema}"
        return
    fi

    for table in $tables; do
        echo "  Cloning structure: ${schema}.${table} -> ${dev}.${table}"
        run_sql "CREATE TABLE ${dev}.${table} (LIKE ${schema}.${table} INCLUDING ALL);"
    done

    # Copy sequences (recreate with current values)
    local sequences
    sequences=$(run_sql "
        SELECT sequence_name FROM information_schema.sequences
        WHERE sequence_schema = '${schema}'
        ORDER BY sequence_name;
    ")

    for seq in $sequences; do
        if [ -n "$seq" ]; then
            local val
            val=$(run_sql "SELECT last_value FROM ${schema}.${seq};")
            echo "  Cloning sequence: ${seq} (current: ${val})"
            run_sql "CREATE SEQUENCE IF NOT EXISTS ${dev}.${seq};"
            run_sql "SELECT setval('${dev}.${seq}', ${val});"
        fi
    done

    echo "Done. Dev schema '${dev}' ready."
    cmd_verify "$schema"
}

cmd_test() {
    local schema="$1"
    local migration="$2"
    if [ -z "$schema" ] || [ -z "$migration" ]; then
        echo "Usage: schema_dev.sh test <schema> <migration_file>"
        exit 1
    fi

    local dev="${schema}_dev"

    # Check dev schema exists
    local exists
    exists=$(run_sql "SELECT schema_name FROM information_schema.schemata WHERE schema_name = '${dev}';")
    if [ -z "$exists" ]; then
        echo "Error: ${dev} does not exist. Run 'snapshot' first."
        exit 1
    fi

    # Check migration file exists
    if [ ! -f "$migration" ]; then
        echo "Error: Migration file not found: ${migration}"
        exit 1
    fi

    # Preprocess migration: replace schema references with dev schema
    # Handles both raw migrations (platform.) and preprocessed ones (schema_name.)
    local tmp_migration="/tmp/schema_dev_migration_$$.sql"
    sed -e "s/CREATE SCHEMA IF NOT EXISTS platform/CREATE SCHEMA IF NOT EXISTS ${dev}/g" \
        -e "s/DROP SCHEMA IF EXISTS platform/DROP SCHEMA IF EXISTS ${dev}/g" \
        -e "s/CREATE SCHEMA IF NOT EXISTS ${schema}/CREATE SCHEMA IF NOT EXISTS ${dev}/g" \
        -e "s/DROP SCHEMA IF EXISTS ${schema}/DROP SCHEMA IF EXISTS ${dev}/g" \
        -e "s/${schema}\./${dev}\./g" \
        -e "s/platform\./${dev}\./g" \
        "$migration" > "$tmp_migration"

    # Extract up and down sections
    local up_sql down_sql
    up_sql=$(sed -n '/-- migrate:up/,/-- migrate:down/p' "$tmp_migration" | head -n -1 | tail -n +2)
    down_sql=$(sed -n '/-- migrate:down/,$p' "$tmp_migration" | tail -n +2)

    # Run UP migration
    echo "=== Testing UP migration against ${dev} ==="
    if run_sql "$up_sql"; then
        echo "UP migration: OK"
    else
        echo "UP migration: FAILED"
        rm -f "$tmp_migration"
        exit 1
    fi

    # Show state after up
    echo ""
    echo "Schema state after UP:"
    cmd_verify "$schema"

    # Run DOWN migration
    echo ""
    echo "=== Testing DOWN migration (rollback) ==="
    if run_sql "$down_sql"; then
        echo "DOWN migration: OK"
    else
        echo "DOWN migration: FAILED"
        rm -f "$tmp_migration"
        exit 1
    fi

    # Re-apply UP so dev schema reflects the final state
    echo ""
    echo "=== Re-applying UP migration (final state) ==="
    run_sql "$up_sql"

    echo ""
    echo "Migration test PASSED (up + down + up all succeeded)"
    rm -f "$tmp_migration"
}

cmd_verify() {
    local schema="$1"
    if [ -z "$schema" ]; then echo "Usage: schema_dev.sh verify <schema>"; exit 1; fi

    local dev="${schema}_dev"

    echo "Tables in ${dev}:"
    run_sql "
        SELECT table_name,
               (SELECT count(*) FROM information_schema.columns c
                WHERE c.table_schema = '${dev}' AND c.table_name = t.table_name) AS columns
        FROM information_schema.tables t
        WHERE table_schema = '${dev}' AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    " | while IFS='|' read -r tbl cols; do
        echo "  ${tbl} (${cols} columns)"

        # Show columns
        run_sql "
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = '${dev}' AND table_name = '${tbl}'
            ORDER BY ordinal_position;
        " | while IFS='|' read -r col dtype nullable def; do
            local null_str=""
            if [ "$nullable" = "NO" ]; then null_str=" NOT NULL"; fi
            local def_str=""
            if [ -n "$def" ] && [ "$def" != "None" ]; then def_str=" DEFAULT ${def}"; fi
            echo "    - ${col} ${dtype}${null_str}${def_str}"
        done
    done
}

cmd_cleanup() {
    local schema="$1"
    if [ -z "$schema" ]; then echo "Usage: schema_dev.sh cleanup <schema>"; exit 1; fi

    local dev="${schema}_dev"
    echo "Dropping ${dev}..."
    run_sql "DROP SCHEMA IF EXISTS ${dev} CASCADE;"
    echo "Done."
}

# Route command
case "${1:-}" in
    snapshot) shift; cmd_snapshot "$@";;
    test) shift; cmd_test "$@";;
    verify) shift; cmd_verify "$@";;
    cleanup) shift; cmd_cleanup "$@";;
    *) usage;;
esac
