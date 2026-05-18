#!/usr/bin/env bash
# Manage the dev PostgreSQL container lifecycle.
# Usage: dev-db.sh {start|stop|seed|reset|watch|status}

set -euo pipefail

CONTAINER=volunteer-call-dev-db
VOLUME=volunteer-call-dev-pgdata
IMAGE=postgres:16-alpine
DB_USER=volunteer_call
DB_PASS=volunteer_call_dev
DB_NAME=volunteer_call
PORT="${DB_PORT:-5432}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
INITDB_DIR="$PROJECT_DIR/scripts/initdb"
CHECKSUM_FILE="$PROJECT_DIR/.dev-db-checksum"

compute_checksum() {
    cat "$INITDB_DIR"/0*.sql | shasum -a 256 | awk '{print $1}'
}

saved_checksum() {
    [ -f "$CHECKSUM_FILE" ] && cat "$CHECKSUM_FILE" || echo ""
}

container_running() {
    docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true
}

container_exists() {
    docker inspect "$CONTAINER" &>/dev/null
}

wait_healthy() {
    # On a fresh container Postgres starts twice: a temporary init server
    # runs the docker-entrypoint initdb scripts, shuts down, then restarts
    # for real. pg_isready against the temp server can succeed and then
    # the socket disappears mid-seed. Require N consecutive successful
    # round-trips (not just pg_isready) so we wait past the restart.
    echo "Waiting for PostgreSQL to be ready..."
    local consecutive=0 required=3
    for _i in $(seq 1 60); do
        if docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres \
                -tAc 'SELECT 1' &>/dev/null; then
            consecutive=$((consecutive + 1))
            if [ "$consecutive" -ge "$required" ]; then
                echo "PostgreSQL is ready."
                return 0
            fi
        else
            consecutive=0
        fi
        sleep 1
    done
    echo "ERROR: PostgreSQL did not become ready in 60s"
    exit 1
}

run_sql_file() {
    docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f - < "$1"
}

do_seed() {
    # If SEED env var is set (typically via `make dev-db-reset SEED=...`)
    # apply that single .sql file instead of the default initdb sequence.
    # Writes the current initdb checksum either way so `do_start`'s
    # auto-reseed-on-changed-files detection doesn't fire on the next
    # start and stomp the just-loaded data.
    local snapshot="${SEED:-}"
    if [ -n "$snapshot" ]; then
        if [ ! -f "$snapshot" ]; then
            echo "ERROR: snapshot file not found: $snapshot"
            exit 1
        fi
        echo "Seeding database from snapshot: $snapshot"
        docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres \
            -c "DROP DATABASE IF EXISTS $DB_NAME;" \
            -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
        run_sql_file "$snapshot"
    else
        echo "Seeding database..."
        docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres \
            -c "DROP DATABASE IF EXISTS $DB_NAME;" \
            -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
        for f in "$INITDB_DIR"/0*.sql; do
            echo "  Running $(basename "$f")..."
            run_sql_file "$f"
        done
    fi
    compute_checksum > "$CHECKSUM_FILE"
    echo "Seed complete."
}

do_snapshot() {
    local out="${1:-}"
    if [ -z "$out" ]; then
        echo "Usage: $0 snapshot <output-file-path>"
        exit 1
    fi
    if ! container_running; then
        echo "ERROR: $CONTAINER is not running. Start it with 'make dev' first."
        exit 1
    fi
    local dir
    dir="$(dirname "$out")"
    [ "$dir" != "." ] && mkdir -p "$dir"
    # Write through a temp file so a failed pg_dump doesn't leave a
    # half-written snapshot. --clean / --if-exists make the output
    # replayable; --no-owner / --no-privileges strip role + grant
    # metadata that would only be valid on the original DB.
    local tmp="${out}.tmp"
    echo "Dumping $DB_NAME → $out ..."
    docker exec "$CONTAINER" pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --clean --if-exists --no-owner --no-privileges \
        > "$tmp"
    mv "$tmp" "$out"
    echo "Snapshot written: $out ($(wc -c <"$out") bytes)"
}

do_start() {
    if container_running; then
        echo "Container $CONTAINER is already running."
    else
        if container_exists; then
            echo "Starting existing container $CONTAINER..."
            docker start "$CONTAINER" >/dev/null
        else
            echo "Creating container $CONTAINER..."
            docker run -d \
                --name "$CONTAINER" \
                -e POSTGRES_USER="$DB_USER" \
                -e POSTGRES_PASSWORD="$DB_PASS" \
                -e POSTGRES_DB="$DB_NAME" \
                -p "$PORT:5432" \
                -v "$VOLUME:/var/lib/postgresql/data" \
                "$IMAGE" >/dev/null
        fi
        wait_healthy
    fi

    # Auto-reseed if SQL files changed
    current=$(compute_checksum)
    if [ "$current" != "$(saved_checksum)" ]; then
        echo "Schema/seed files changed — reseeding..."
        do_seed
    fi
}

do_stop() {
    local quiet="${1:-}"
    if container_running; then
        echo "Stopping $CONTAINER..."
        docker stop "$CONTAINER" >/dev/null
        echo "Stopped."
    elif [ "$quiet" != "-q" ]; then
        echo "Container $CONTAINER is not running."
    fi
}

do_reset() {
    echo "Resetting database (removing volume)..."
    if container_exists; then
        docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
    fi
    docker volume rm "$VOLUME" 2>/dev/null || true
    rm -f "$CHECKSUM_FILE"
    do_start
}

do_watch() {
    if ! command -v fswatch &>/dev/null; then
        # Graceful degradation — no fswatch, no watching
        return 0
    fi
    echo "Watching $INITDB_DIR for changes..."
    fswatch -o "$INITDB_DIR"/*.sql | while read -r _; do
        echo ""
        echo "SQL files changed — reseeding..."
        do_seed
    done
}

do_status() {
    if container_running; then
        echo "$CONTAINER is running (port $PORT)"
    elif container_exists; then
        echo "$CONTAINER exists but is stopped"
    else
        echo "$CONTAINER does not exist"
    fi
}

case "${1:-}" in
    start)    do_start ;;
    stop)     do_stop "${2:-}" ;;
    seed)     do_seed ;;
    reset)    do_reset ;;
    watch)    do_watch ;;
    status)   do_status ;;
    snapshot) do_snapshot "${2:-}" ;;
    *)
        echo "Usage: $0 {start|stop|seed|reset|watch|status|snapshot <path>}"
        echo "Env:   SEED=<path>  pass to 'reset' or 'seed' to load that .sql"
        echo "                    file instead of the default initdb sequence."
        exit 1
        ;;
esac
