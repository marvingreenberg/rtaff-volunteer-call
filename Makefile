VERSION     := $(shell git describe --tags --always 2>/dev/null | sed 's/^v//; s/-\([0-9]*\)-g\(.*\)/.dev\1+g\2/' || echo "0.0.0")
DOCKER_TAG  := $(shell echo "$(VERSION)" | sed 's/+.*//')

SERVICE_NAME   := volunteer-call

# Dev ports — single source of truth, exported to scripts and child processes.
FRONTEND_PORT   ?= 5173
BACKEND_PORT    ?= 8001
DB_PORT         ?= 5432
SMTP_PORT       ?= 1025
MAILPIT_UI_PORT ?= 8025
export DB_PORT SMTP_PORT MAILPIT_UI_PORT

DEMO_MODE ?= false
export DEMO_MODE

.PHONY: help check-prereqs setup setup-backend setup-frontend \
        dev dev-db-reset db-snapshot mailpit \
        test test-backend test-frontend types \
        lint lint-be lint-fe format format-be format-fe \
        demo build clean

help:
	@echo "Available targets:"
	@echo "  check-prereqs  - Verify dev prerequisites (python, uv, node, pnpm, docker, gcloud)"
	@echo "  setup          - Set up all components (runs check-prereqs first)"
	@echo "  setup-backend  - Set up backend Python environment"
	@echo "  setup-frontend - Install frontend dependencies"
	@echo "  lint           - Run all linters (API + UI)"
	@echo ""
	@echo "Development:"
	@echo "  dev            - Start Mailpit + DB + backend + frontend (Ctrl+C stops all)"
	@echo "  dev-db-reset   - Destroy DB volume and start fresh"
	@echo "                   (override seed with SEED=path/to/file.sql)"
	@echo "  db-snapshot    - Dump current DB to a .sql file"
	@echo "                   (FILE=path/to/output.sql; pair with dev-db-reset SEED=...)"
	@echo "  mailpit        - Start Mailpit email viewer (UI at http://localhost:$(MAILPIT_UI_PORT))"
	@echo ""
	@echo "Testing:"
	@echo "  test           - Run all tests"
	@echo "  test-backend   - Run backend tests"
	@echo "  test-frontend  - Run frontend tests"
	@echo ""
	@echo "Other:"
	@echo "  types          - Generate TypeScript types from OpenAPI"
	@echo "  clean          - Clean all build artifacts"

check-prereqs:
	@./scripts/check_prerequisites.sh

setup: check-prereqs setup-backend setup-frontend

setup-backend:
	make -C backend setup

setup-frontend:
	cd frontend && pnpm install

dev-db-reset:
	@SEED="$(SEED)" scripts/dev-db.sh reset

db-snapshot:
	@if [ -z "$(FILE)" ]; then \
	  echo "Usage: make db-snapshot FILE=path/to/output.sql"; \
	  exit 2; \
	fi
	@scripts/dev-db.sh snapshot "$(FILE)"

mailpit:
	@scripts/dev-mailpit.sh start

dev:
	@scripts/dev-mailpit.sh start
	@scripts/dev-db.sh start
	@APP_URL="http://localhost:$(FRONTEND_PORT)"; \
	  PIDS=""; \
	  cleanup() { \
	    [ -n "$$PIDS" ] && kill $$PIDS 2>/dev/null; \
	    wait 2>/dev/null; \
	    scripts/dev-db.sh stop -q; \
	    scripts/dev-mailpit.sh stop -q; \
	  }; \
	  trap cleanup EXIT; \
	  scripts/dev-db.sh watch & PIDS="$$PIDS $$!"; \
	  ( cd backend && SMTP_PORT=$(SMTP_PORT) APP_BASE_URL=$$APP_URL CORS_ORIGIN=$$APP_URL \
	      uv run uvicorn volunteer_call_api.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT) ) & PIDS="$$PIDS $$!"; \
	  ( cd frontend && pnpm run dev -- --port $(FRONTEND_PORT) ) & PIDS="$$PIDS $$!"; \
	  for i in 1 2 3 4 5 6 7 8 9 10; do curl -sf http://localhost:$(BACKEND_PORT)/health >/dev/null 2>&1 && break; sleep 1; done; \
	  curl -sf http://localhost:$(BACKEND_PORT)/health >/dev/null 2>&1 || { echo "ERROR: API server failed to start"; exit 1; }; \
	  for i in 1 2 3 4 5 6 7 8 9 10; do curl -s $$APP_URL >/dev/null 2>&1 && break; sleep 1; done; \
	  echo "App: $$APP_URL  |  API: http://localhost:$(BACKEND_PORT)  |  Mailpit: http://localhost:$(MAILPIT_UI_PORT)"; \
	  wait

lint: lint-be lint-fe

format: format-be format-fe

lint-be:
	make -C backend lint

lint-fe:
	cd frontend && pnpm lint && pnpm format:check && pnpm run check

format-be:
	make -C backend format

format-fe:
	cd frontend && pnpm lint:fix && pnpm format

test: test-backend test-frontend

test-backend:
	make -C backend test

test-frontend:
	cd frontend && pnpm exec vitest run

types:
	cd frontend && pnpm run generate-types

# Records a video walkthrough of the full volunteer-call flow following
# Demo.md. Assumes `make dev` is running in another shell (frontend on
# 5173, backend on 8001, Mailpit on 8025). Output lands in
# frontend/test-results/demo/.
demo:
	cd frontend && pnpm exec playwright test e2e/demo.spec.ts

clean:
	make -C backend clean
	rm -rf frontend/node_modules frontend/.svelte-kit frontend/build
