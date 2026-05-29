#!/usr/bin/env bash
# Shared helpers for setup scripts. Sourced; do not execute.

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

errors=0
warnings=0

pass() { echo -e "${GREEN}  ✓${NC} $1"; }
warn() { echo -e "${YELLOW}  ⚠${NC} $1"; warnings=$((warnings + 1)); }
fail() { echo -e "${RED}  ✗${NC} $1"; errors=$((errors + 1)); }

# Idempotent IAM helpers — copied from fqf's set-gcloud-creds-for-deploy.

# Caller must have $PROJECT set.

sa_exists() {
    gcloud iam service-accounts describe "$1" --project="$PROJECT" &>/dev/null
}

has_project_role() {
    local email=$1 role=$2
    gcloud projects get-iam-policy "$PROJECT" \
        --flatten="bindings[].members" \
        --filter="bindings.role=${role} AND bindings.members=serviceAccount:${email}" \
        --format="value(bindings.role)" 2>/dev/null | grep -q .
}

grant_project_role() {
    local email=$1 role=$2
    if has_project_role "$email" "$role"; then
        echo "  ${role} — already bound"
    else
        echo "  Granting ${role}..."
        gcloud projects add-iam-policy-binding "$PROJECT" \
            --member="serviceAccount:${email}" \
            --role="$role" \
            --quiet &>/dev/null
    fi
}

has_repo_role() {
    local email=$1 repo=$2 role=$3
    gcloud artifacts repositories get-iam-policy "$repo" \
        --location="$GCP_REGION" \
        --project="$PROJECT" \
        --flatten="bindings[].members" \
        --filter="bindings.role=${role} AND bindings.members=serviceAccount:${email}" \
        --format="value(bindings.role)" 2>/dev/null | grep -q .
}

grant_repo_role() {
    local email=$1 repo=$2 role=$3
    if has_repo_role "$email" "$repo" "$role"; then
        echo "  ${role} on ${repo} — already bound"
    else
        echo "  Granting ${role} on ${repo}..."
        gcloud artifacts repositories add-iam-policy-binding "$repo" \
            --location="$GCP_REGION" \
            --project="$PROJECT" \
            --member="serviceAccount:${email}" \
            --role="$role" \
            --quiet &>/dev/null
    fi
}

has_secret_role() {
    local email=$1 secret=$2 role=$3
    gcloud secrets get-iam-policy "$secret" \
        --project="$PROJECT" \
        --flatten="bindings[].members" \
        --filter="bindings.role=${role} AND bindings.members=serviceAccount:${email}" \
        --format="value(bindings.role)" 2>/dev/null | grep -q .
}

grant_secret_role() {
    local email=$1 secret=$2 role=$3
    if has_secret_role "$email" "$secret" "$role"; then
        echo "  ${role} on ${secret} — already bound"
    else
        echo "  Granting ${role} on ${secret}..."
        gcloud secrets add-iam-policy-binding "$secret" \
            --project="$PROJECT" \
            --member="serviceAccount:${email}" \
            --role="$role" \
            --quiet &>/dev/null
    fi
}

# Resolve PROJECT from gcloud config, fail if unset.
require_active_gcp_project() {
    PROJECT=$(gcloud config get-value project 2>/dev/null || true)
    if [[ -z "$PROJECT" ]]; then
        echo "ERROR: No GCP project set. Run: gcloud config set project ${GCP_PROJECT_NAME}" >&2
        exit 1
    fi
    if [[ "$PROJECT" != "$GCP_PROJECT_NAME" ]]; then
        echo "ERROR: Active GCP project '${PROJECT}' does not match expected '${GCP_PROJECT_NAME}'." >&2
        echo "Run: gcloud config set project ${GCP_PROJECT_NAME}" >&2
        exit 1
    fi
}
