# Project: RT-AFF Volunteer Call System

## Architecture

Standalone volunteer call notification system: Python/FastAPI backend + SvelteKit frontend + PostgreSQL. Follows the same architecture patterns as the parent rtaff-workflow project. Single-container deployment (Cloud Run); local dev uses Docker for PostgreSQL only.

### Backend (`backend/src/volunteer_call_api/`)
- **Python 3.11+, FastAPI**, async SQLAlchemy 2.0, asyncpg, Pydantic v2
- Structure: `models/`, `routes/`, `schemas/`, `services/`

### Frontend (`frontend/`)
- **SvelteKit** with Svelte 5, TypeScript
- Structure: `src/routes/`, `src/lib/api/`, `src/lib/components/`, `src/lib/stores/`

### Infrastructure
- **Prerequisites**: `uv` (Python project manager), `pnpm` (frontend), `docker` (PostgreSQL)
- `uv` manages Python venvs, dependency locking (`uv.lock`), and command execution (`uv run`)
- `scripts/dev-db.sh`: manages dev PostgreSQL container (start/stop/seed/reset/watch)
- `Makefile`: dev, dev-db-reset, test, setup, lint, build, deploy, clean targets

## Development Workflow

### Task Execution Process

1. **Branch**: `git checkout -b <feature-branch>` off main
2. **Plan**: Use plan mode for non-trivial changes to design the approach
3. **Implement**: Write code and tests
4. **Test**: Run all tests, fix failures
5. **Commit**: Commit changes to the feature branch
6. **Merge**: Merge feature branch onto main (conflicts resolved by user)
7. **Push**: Push main to origin. Leave local branches in place. Do NOT push feature branches.

### Command Preferences

Use root Makefile targets when working from the project root:
- `make test-backend` / `make test-frontend` / `make test`
- `make lint-be` / `make lint-fe` / `make lint`
- `make format-be` / `make format-fe`

These commands provide "actions" that are also used by the gitactions and the user, so
(1) Using them ensures compatibility with other users of the project
(2) Using them ensures that they are used and kept up to date as the project evolves

Note that this is not a hard and fast rule, but that these targets should be used for final validation before a commit.

### Testing

**Backend**: `make test-backend`
**Frontend**: `make test-frontend`
**All at once**: `make test`

### Linting

**Backend**: `make lint-be` / `make format-be`
**Frontend**: `make lint-fe` / `make format-fe`

### Running

**All-in-one**: `make dev` (DB + backend + frontend; Ctrl+C stops all)
**DB reset**: `make dev-db-reset` (destroy volume and start fresh)

### Git Worktree Policy
- The root repo directory is the user's workspace — never modify files or switch branches there
- Always create a worktree under `.worktrees/` for implementation work: `git worktree add .worktrees/<name> -b <branch> main`
- Each worktree gets its own `.venv` and `node_modules` (do NOT symlink or share these)
- To merge into main: `git worktree add .worktrees/merge-main main`, merge there, remove worktree after
- To push main: `git push origin main` works from any directory without checking out main
- Leave local feature branches in place after merging. Do NOT push feature branches.
