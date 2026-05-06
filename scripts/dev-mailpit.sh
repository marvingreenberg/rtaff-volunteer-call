#!/usr/bin/env bash
# Manage the dev Mailpit container lifecycle.
# Usage: dev-mailpit.sh {start|stop|status}

set -euo pipefail

CONTAINER=volunteer-call-mailpit
IMAGE=axllent/mailpit:latest
SMTP_PORT="${SMTP_PORT:-1025}"
UI_PORT="${MAILPIT_UI_PORT:-8025}"

container_running() {
    docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null | grep -q true
}

container_exists() {
    docker inspect "$CONTAINER" &>/dev/null
}

do_start() {
    if container_running; then
        echo "Container $CONTAINER is already running."
        return 0
    fi
    if container_exists; then
        echo "Starting existing container $CONTAINER..."
        docker start "$CONTAINER" >/dev/null
    else
        echo "Creating container $CONTAINER..."
        docker run -d \
            --name "$CONTAINER" \
            -p "$SMTP_PORT:1025" \
            -p "$UI_PORT:8025" \
            "$IMAGE" >/dev/null
    fi
    echo "Mailpit running (SMTP $SMTP_PORT, UI http://localhost:$UI_PORT)"
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

do_status() {
    if container_running; then
        echo "$CONTAINER is running (SMTP $SMTP_PORT, UI $UI_PORT)"
    elif container_exists; then
        echo "$CONTAINER exists but is stopped"
    else
        echo "$CONTAINER does not exist"
    fi
}

case "${1:-}" in
    start)  do_start ;;
    stop)   do_stop "${2:-}" ;;
    status) do_status ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac
