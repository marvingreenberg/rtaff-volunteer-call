#!/usr/bin/env bash
# Single source of truth for deployment identity. Every setup script
# (check_prerequisites.sh, setup-gcp-project, set-gcloud-creds-for-deploy,
# setup-neon-project, setup-secrets) sources this file so renaming the
# service or moving regions touches one place.
#
# The values here must match the env block in .github/workflows/deploy.yml;
# check_prerequisites.sh verifies the match.
#
# Override GCP_PROJECT_NAME or NEON_PROJECT_NAME by exporting before
# invoking — useful for staging/scratch projects without editing this file.

export SERVICE_NAME="volunteer-call-api"
export GCP_PROJECT_NAME="${GCP_PROJECT_NAME:-rtaff-volunteer-call}"
export GCP_REGION="${GCP_REGION:-us-central1}"
export AR_REPO="container-images"

export DEPLOY_SA_NAME="github-deploy"
export RUNTIME_SA_NAME="volunteer-call-runtime"

export NEON_PROJECT_NAME="${NEON_PROJECT_NAME:-volunteer-call}"
export NEON_REGION="${NEON_REGION:-aws-us-east-2}"
export NEON_ROLE_NAME="volunteer_call_user"
export NEON_DB_NAME="volunteer_call"

export DB_SECRET_NAME="volunteer-call-database-url"
export JWT_SECRET_NAME="volunteer-call-jwt-secret"
