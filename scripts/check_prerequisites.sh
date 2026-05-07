#!/usr/bin/env bash
# Checks that required development tools are installed and meet minimum
# version requirements, plus a couple of project-specific warnings (active
# GCP project, fswatch for schema-watching).
set -euo pipefail

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=11
REQUIRED_NODE_MAJOR=18

# Substring the active GCP project id must contain. The deploy
# SERVICE_NAME is "volunteer-call"; valid project ids include
# "volunteer-call-prod", "rtaff-volunteer-call", "volunteer-call-dev",
# etc. (the bare "volunteer-call" id is globally taken in GCP).
EXPECTED_GCP_PROJECT_SUBSTRING="volunteer-call"

errors=0
warnings=0

pass() { echo -e "${GREEN}  ✓${NC} $1"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $1"; warnings=$((warnings + 1)); }
fail() { echo -e "${RED}  ✗${NC} $1"; errors=$((errors + 1)); }

echo "Checking prerequisites..."
echo ""

# Python 3.11+
if command -v python3 &>/dev/null; then
    py_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    py_major=$(echo "$py_version" | cut -d. -f1)
    py_minor=$(echo "$py_version" | cut -d. -f2)
    if [[ "$py_major" -ge "$REQUIRED_PYTHON_MAJOR" && "$py_minor" -ge "$REQUIRED_PYTHON_MINOR" ]]; then
        pass "Python $py_version"
    else
        fail "Python $py_version found — ${REQUIRED_PYTHON_MAJOR}.${REQUIRED_PYTHON_MINOR}+ required"
    fi
else
    fail "Python 3 not found"
fi

# uv
if command -v uv &>/dev/null; then
    pass "uv $(uv --version | awk '{print $2}')"
else
    fail "uv not found — install from https://docs.astral.sh/uv/"
fi

# Node.js 18+
if command -v node &>/dev/null; then
    node_version=$(node --version | sed 's/v//')
    node_major=$(echo "$node_version" | cut -d. -f1)
    if [[ "$node_major" -ge "$REQUIRED_NODE_MAJOR" ]]; then
        pass "Node.js v$node_version"
    else
        fail "Node.js v$node_version found — v${REQUIRED_NODE_MAJOR}+ required"
    fi
else
    fail "Node.js not found — install from https://nodejs.org"
fi

# pnpm
if command -v pnpm &>/dev/null; then
    pass "pnpm $(pnpm --version)"
else
    fail "pnpm not found — install with: npm install -g pnpm"
fi

# Docker (required for the dev Postgres + Mailpit containers)
if command -v docker &>/dev/null; then
    pass "Docker $(docker --version | awk '{print $3}' | tr -d ',')"
else
    warn "Docker not found — needed for the local dev DB (scripts/dev-db.sh) and Mailpit (scripts/dev-mailpit.sh), and for 'make build-image' / cloud deploys"
fi

# fswatch (optional — enables schema-watching reseed in scripts/dev-db.sh)
if command -v fswatch &>/dev/null; then
    pass "fswatch (for scripts/dev-db.sh schema watching)"
else
    warn "fswatch not found — schema-file watching disabled in 'make dev'. Install: brew install fswatch (macOS) or apt install fswatch"
fi

# gcloud CLI (optional — needed for deploy)
if command -v gcloud &>/dev/null; then
    pass "gcloud $(gcloud --version 2>/dev/null | head -1 | awk '{print $4}')"

    gcp_project=$(gcloud config get-value project 2>/dev/null || true)
    if [[ -z "$gcp_project" ]]; then
        warn "No active GCP project — run: gcloud config set project rtaff-${EXPECTED_GCP_PROJECT_SUBSTRING}"
    elif [[ "$gcp_project" != *"$EXPECTED_GCP_PROJECT_SUBSTRING"* ]]; then
        fail "Active GCP project '${gcp_project}' does not contain '${EXPECTED_GCP_PROJECT_SUBSTRING}'"
        fail "  This is almost certainly a sibling project (e.g. rtaff). Run: gcloud config set project <something-volunteer-call-something>"
    else
        pass "Active GCP project: ${gcp_project}"
    fi
else
    warn "gcloud CLI not found — needed for 'make deploy' and the docs/*.howto walkthroughs"
    warn "  Install from https://cloud.google.com/sdk/docs/install"
fi

echo ""
if [[ "$errors" -gt 0 ]]; then
    echo -e "${RED}Prerequisites check failed — $errors error(s) must be resolved before setup.${NC}"
    exit 1
elif [[ "$warnings" -gt 0 ]]; then
    echo -e "${YELLOW}Prerequisites check passed with $warnings warning(s) — optional tools missing or misconfigured.${NC}"
else
    echo -e "${GREEN}All prerequisites satisfied.${NC}"
fi
