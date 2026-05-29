# Deployment

The deployed app runs on Cloud Run, fronted by Cloud Run's managed URL,
with Postgres on Neon (free tier). The container is built from the root
`Dockerfile` (multi-stage: SvelteKit frontend + Python backend; frontend
assets embedded in the backend Python package). Releases are tag-driven
GitHub Actions (`.github/workflows/deploy.yml`); a maintainer can also
deploy out-of-band with `make deploy`.

## Identity

All deploy-identity values (GCP project name, region, service name, SA
names, Secret Manager names, Neon project name) live in
`scripts/_project-config.sh`. Edit there to rename or move; everything
else (scripts, Makefile, `deploy.yml`) reads from that file or has its
values checked against it by `make check-prereqs`.

Override at invocation time by exporting (`GCP_PROJECT_NAME=...
make bootstrap`) — useful for spinning up a scratch or staging project.

## Prerequisites

`make check-prereqs` enforces these:

- `gcloud` (authenticated, active project = `rtaff-volunteer-call`)
- `gh` (authenticated, repo access — used to push GCP_SA_KEY/GCP_PROJECT secrets)
- `neonctl` (authenticated via `neonctl auth` — used by `setup-neon-project`)
- `docker`, `uv`, `pnpm`, `node>=18`, `python>=3.11`

## One-time bootstrap

From a fresh machine (with the prerequisites above), one command takes
you to a deployable state:

```
make bootstrap
```

Each stage is idempotent — re-running prints "already exists / no change"
messages and exits 0. Individual stages are also runnable on their own:

| Target | What it does | Underlying script |
|---|---|---|
| `make bootstrap-gcp` | GCP project, billing, APIs, Artifact Registry | `scripts/setup-gcp-project` |
| `make bootstrap-creds` | Deploy SA, runtime SA, IAM roles, `gh secret set` | `scripts/set-gcloud-creds-for-deploy` |
| `make bootstrap-neon` | Neon project / role / database (prints asyncpg URL) | `scripts/setup-neon-project` |
| `make bootstrap-secrets` | `volunteer-call-database-url` + `volunteer-call-jwt-secret` in GCP Secret Manager; binds secretAccessor on runtime SA | `scripts/setup-secrets` |

`bootstrap-secrets` invokes `bootstrap-neon` internally when the DB URL
secret is missing — running `bootstrap-neon` separately is only useful
for inspection.

## Secrets

| Secret | Source | Rotated by |
|---|---|---|
| GitHub: `GCP_SA_KEY` | `gcloud iam service-accounts keys create` against the deploy SA | `make bootstrap-creds --new` (delete + recreate everything) |
| GitHub: `GCP_PROJECT` | `_project-config.sh` `GCP_PROJECT_NAME` | `make bootstrap-creds` |
| Secret Manager: `volunteer-call-database-url` | `scripts/setup-neon-project` output (asyncpg-flavored) | `./scripts/setup-secrets --refresh-db` |
| Secret Manager: `volunteer-call-jwt-secret` | `openssl rand -hex 32` | `./scripts/setup-secrets --rotate-jwt` |

Cloud Run reads the two Secret Manager secrets via `--set-secrets` at
deploy time; `deploy.yml` and `make deploy` both pin to `:latest`, so
rotation takes effect on the next deploy.

## Deploy

Normal flow: tag a release.

```
git tag v0.1.2
git push --tags
```

`.github/workflows/deploy.yml` runs CI, builds the image, pushes to
both ghcr.io and GCP Artifact Registry, deploys to Cloud Run.

Out-of-band flow: `make deploy` from a maintainer's machine. Builds for
`linux/amd64`, pushes to GCP only, deploys the same way.

## What the .howto files cover

`docs/GCP_SETUP.howto`, `docs/NEON_SQL.howto`, and `docs/CLOUD_SQL.howto`
were the original manual walkthroughs. The bootstrap scripts above are
now the canonical path — read the howto only when you need to know what
a script is doing under the hood (e.g. why the asyncpg URL strips
`channel_binding=require`, or how to move from Neon to Cloud SQL).

`docs/CLOUD_RUN_WARMER.howto` covers cold-start mitigation and is
independent of the bootstrap flow.
