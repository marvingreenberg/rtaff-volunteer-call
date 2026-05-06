#!/usr/bin/env bash
# Manage the dev PostgreSQL container lifecycle.
# Usage: dev-db.sh {start|stop|seed|reset|watch|status}

set -euo pipefail

CONTAINER=vcall-dev-db
VOLUME=vcall-dev-pgdata
IMAGE=postgres:16-alpine
DB_USER=vcall
DB_PASS=vcall_dev
DB_NAME=vcall
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
    echo "Waiting for PostgreSQL to be ready..."
    for _i in $(seq 1 30); do
        if docker exec "$CONTAINER" pg_isready -U "$DB_USER" &>/dev/null; then
            echo "PostgreSQL is ready."
            return 0
        fi
        sleep 1
    done
    echo "ERROR: PostgreSQL did not become ready in 30s"
    exit 1
}

run_sql_file() {
    docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB_NAME" -f - < "$1"
}

do_seed() {
    echo "Seeding database..."
    docker exec "$CONTAINER" psql -U "$DB_USER" -d postgres \
        -c "DROP DATABASE IF EXISTS $DB_NAME;" \
        -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    for f in "$INITDB_DIR"/0*.sql; do
        echo "  Running $(basename "$f")..."
        run_sql_file "$f"
    done
    compute_checksum > "$CHECKSUM_FILE"
    echo "Seed complete."
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
    start)  do_start ;;
    stop)   do_stop "${2:-}" ;;
    seed)   do_seed ;;
    reset)  do_reset ;;
    watch)  do_watch ;;
    status) do_status ;;
    *)
        echo "Usage: $0 {start|stop|seed|reset|watch|status}"
        exit 1
        ;;
esac
