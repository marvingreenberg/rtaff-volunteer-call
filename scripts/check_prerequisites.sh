#!/usr/bin/env bash
# Checks that required development tools are installed and meet minimum
# version requirements, plus project-specific checks (active GCP project
# matches the expected one, deploy.yml is in sync with _project-config.sh,
# fswatch for schema-watching, neonctl for Neon bootstrap).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./_project-config.sh
source "${SCRIPT_DIR}/_project-config.sh"
# shellcheck source=./_lib.sh
source "${SCRIPT_DIR}/_lib.sh"

REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=11
REQUIRED_NODE_MAJOR=18

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

# gcloud CLI (required for deploy / bootstrap)
if command -v gcloud &>/dev/null; then
    pass "gcloud $(gcloud --version 2>/dev/null | head -1 | awk '{print $4}')"

    gcp_project=$(gcloud config get-value project 2>/dev/null || true)
    if [[ -z "$gcp_project" ]]; then
        warn "No active GCP project — run: gcloud config set project ${GCP_PROJECT_NAME}"
    elif [[ "$gcp_project" != "$GCP_PROJECT_NAME" ]]; then
        fail "Active GCP project '${gcp_project}' does not match expected '${GCP_PROJECT_NAME}'"
        fail "  Run: gcloud config set project ${GCP_PROJECT_NAME}"
        fail "  (Override the expected name by exporting GCP_PROJECT_NAME before running.)"
    else
        pass "Active GCP project: ${gcp_project}"
    fi
else
    warn "gcloud CLI not found — needed for 'make bootstrap' / 'make deploy' and the docs/*.howto walkthroughs"
    warn "  Install from https://cloud.google.com/sdk/docs/install"
fi

# gh CLI (required for set-gcloud-creds-for-deploy)
if command -v gh &>/dev/null; then
    pass "gh $(gh --version 2>/dev/null | head -1 | awk '{print $3}')"
else
    warn "gh CLI not found — needed for 'make bootstrap-creds' (pushes GCP_SA_KEY/GCP_PROJECT to GitHub secrets)"
    warn "  Install from https://cli.github.com/"
fi

# neonctl (required for setup-neon-project)
if command -v neonctl &>/dev/null; then
    neonctl_version=$(neonctl --version 2>/dev/null | head -1 | awk '{print $NF}')
    pass "neonctl ${neonctl_version}"
    if neonctl auth status &>/dev/null; then
        pass "neonctl authenticated"
    else
        warn "neonctl not authenticated — run: neonctl auth"
    fi
else
    warn "neonctl not found — needed for 'make bootstrap-neon' (idempotent Neon project setup)"
    warn "  Install with: npm install -g neonctl"
fi

# Sanity check: deploy.yml env values must match _project-config.sh.
DEPLOY_YML="${SCRIPT_DIR}/../.github/workflows/deploy.yml"
if [[ -f "$DEPLOY_YML" ]]; then
    deploy_service_name=$(grep -E '^[[:space:]]+SERVICE_NAME:' "$DEPLOY_YML" | head -1 | awk '{print $2}')
    deploy_region=$(grep -E '^[[:space:]]+GCP_REGION:' "$DEPLOY_YML" | head -1 | awk '{print $2}')
    deploy_repo=$(grep -E '^[[:space:]]+GCP_REPOSITORY:' "$DEPLOY_YML" | head -1 | awk '{print $2}')
    if [[ "$deploy_service_name" == "$SERVICE_NAME" && "$deploy_region" == "$GCP_REGION" && "$deploy_repo" == "$AR_REPO" ]]; then
        pass "deploy.yml matches scripts/_project-config.sh"
    else
        fail "deploy.yml env block out of sync with scripts/_project-config.sh:"
        fail "  SERVICE_NAME:    deploy.yml='${deploy_service_name}' config='${SERVICE_NAME}'"
        fail "  GCP_REGION:      deploy.yml='${deploy_region}' config='${GCP_REGION}'"
        fail "  GCP_REPOSITORY:  deploy.yml='${deploy_repo}' config='${AR_REPO}'"
    fi
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
