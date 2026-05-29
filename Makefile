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
        bootstrap bootstrap-gcp bootstrap-creds bootstrap-neon bootstrap-secrets \
        build-image deploy \
        dev dev-db-reset db-snapshot mailpit \
        test test-backend test-frontend test-e2e test-mobile-smoke types \
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
	@echo "Cloud bootstrap (idempotent, safe to re-run):"
	@echo "  bootstrap          - End-to-end: GCP project + creds + Neon + secrets"
	@echo "  bootstrap-gcp      - GCP project, APIs, Artifact Registry"
	@echo "  bootstrap-creds    - Service accounts + GitHub Actions secrets"
	@echo "  bootstrap-neon     - Neon project / role / database (prints asyncpg URL)"
	@echo "  bootstrap-secrets  - DATABASE_URL + JWT_SECRET in GCP Secret Manager"
	@echo "  build-image        - Build the deploy container image locally"
	@echo "  deploy             - Build, push, and deploy to Cloud Run (use a tag in CI normally)"
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
	@echo "  test-e2e       - Headless Playwright run of the demo spec (needs make dev)"
	@echo "  test-mobile-smoke - Phone-viewport smoke for /volunteering (needs make dev; skips if not up)"
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

# ── Cloud bootstrap ────────────────────────────────────────────
# Identity (project name, region, SA names, secret names, Neon names) is
# defined in scripts/_project-config.sh — edit there, not here.

bootstrap: check-prereqs bootstrap-gcp bootstrap-creds bootstrap-secrets
	@echo ""
	@echo "Bootstrap complete. Next: tag a release (git tag vX.Y.Z && git push --tags)"
	@echo "  or run 'make deploy' locally for an out-of-band push."

bootstrap-gcp:
	@./scripts/setup-gcp-project

bootstrap-creds:
	@./scripts/set-gcloud-creds-for-deploy

# Prints the asyncpg URL on stdout. Used standalone for ad-hoc inspection;
# `bootstrap-secrets` invokes setup-neon-project itself when it needs the URL.
bootstrap-neon:
	@./scripts/setup-neon-project

bootstrap-secrets:
	@./scripts/setup-secrets

# ── Container build / local deploy ─────────────────────────────
# CI deploys via .github/workflows/deploy.yml on version tags. These
# targets exist for out-of-band pushes from a maintainer's laptop.

# Sourced from scripts/_project-config.sh so the Makefile, scripts, and
# deploy.yml all see the same identity. Override at the command line:
#   make deploy GCP_PROJECT=rtaff-volunteer-call-staging
GCP_PROJECT          ?= $(shell . scripts/_project-config.sh && echo $$GCP_PROJECT_NAME)
GCP_REGION_VAR       ?= $(shell . scripts/_project-config.sh && echo $$GCP_REGION)
GCP_REPOSITORY       := $(shell . scripts/_project-config.sh && echo $$AR_REPO)
SERVICE_NAME_DEPLOY  := $(shell . scripts/_project-config.sh && echo $$SERVICE_NAME)
GCP_IMAGE            := $(GCP_REGION_VAR)-docker.pkg.dev/$(GCP_PROJECT)/$(GCP_REPOSITORY)/$(SERVICE_NAME_DEPLOY)

build-image:
	docker buildx build --platform=linux/amd64 \
	  --build-arg VERSION=$(VERSION) \
	  -t $(GCP_IMAGE):$(DOCKER_TAG) \
	  -t $(GCP_IMAGE):latest \
	  --load .

deploy: build-image
	gcloud auth configure-docker $(GCP_REGION_VAR)-docker.pkg.dev --quiet
	docker push $(GCP_IMAGE):$(DOCKER_TAG)
	docker push $(GCP_IMAGE):latest
	gcloud run deploy $(SERVICE_NAME_DEPLOY) \
	  --image=$(GCP_IMAGE):$(DOCKER_TAG) \
	  --platform=managed \
	  --region=$(GCP_REGION_VAR) \
	  --project=$(GCP_PROJECT) \
	  --allow-unauthenticated \
	  --port=8000 --memory=1Gi --cpu=1 \
	  --min-instances=0 --max-instances=3 \
	  --service-account=volunteer-call-runtime@$(GCP_PROJECT).iam.gserviceaccount.com \
	  --set-secrets=DATABASE_URL=volunteer-call-database-url:latest,JWT_SECRET=volunteer-call-jwt-secret:latest \
	  --set-env-vars=PYTHONUNBUFFERED=1
	@echo "Deployed: $$(gcloud run services describe $(SERVICE_NAME_DEPLOY) --region=$(GCP_REGION_VAR) --project=$(GCP_PROJECT) --format='value(status.url)')"

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
#
# AUTODEMO controls whether the spec stops at each major beat for a
# manual Continue/Cancel click (`AUTODEMO=0`, the default) or replays
# straight through (`AUTODEMO=1`, used for video recording). Override
# on the command line:
#   make demo              # manual stepping
#   make demo AUTODEMO=1   # auto-replay
# Always runs headed — `make demo` is a live walkthrough, not a CI test.
# 20-minute Playwright timeout absorbs long discussion pauses.
AUTODEMO ?= 0

demo:
	cd frontend && AUTODEMO=$(AUTODEMO) pnpm exec playwright test e2e/demo.spec.ts --headed --timeout=1200000

# Headless smoke run of the demo spec. Runs in AUTODEMO=1 (no Continue
# overlay, no headed window) so a refactor that breaks the demo path
# fails CI quickly. Same prerequisites as `make demo`: requires `make
# dev` running in another shell (frontend on 5173, backend on 8001,
# Mailpit on 8025).
test-e2e:
	cd frontend && AUTODEMO=1 pnpm exec playwright test e2e/demo.spec.ts

# Smoke check that /volunteering renders cleanly at iPhone-SE width
# (375x667). Same dev-stack prereqs as test-e2e — backend + frontend +
# Mailpit must be up via `make dev`. When the backend isn't reachable
# the target prints a hint and exits 0 so a routine run is a quiet
# no-op instead of timing out.
test-mobile-smoke:
	@if ! curl -sf http://localhost:$(BACKEND_PORT)/health >/dev/null 2>&1; then \
	  echo "make test-mobile-smoke: backend not reachable at http://localhost:$(BACKEND_PORT)."; \
	  echo "Start the dev stack with 'make dev' in another shell, then re-run."; \
	  exit 0; \
	fi
	cd frontend && pnpm exec playwright test e2e/mobile-smoke.spec.ts

clean:
	make -C backend clean
	rm -rf frontend/node_modules frontend/.svelte-kit frontend/build
