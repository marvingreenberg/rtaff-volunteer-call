# Stage 1: Build frontend static files
FROM node:20-alpine AS frontend-builder
RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

# Stage 2: Build and run backend with embedded frontend
FROM python:3.14-slim

ARG VERSION=0.0.0
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${VERSION}

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY backend/src/ ./src/
COPY backend/pyproject.toml backend/alembic.ini ./
RUN uv pip install --system --no-cache-dir .

# Copy built frontend into the installed package's static directory.
# The package lives in site-packages, not /app/src, so we resolve its path
# at build time and copy the assets there.
COPY --from=frontend-builder /frontend/build/ /tmp/fe-build/
RUN STATIC_DIR=$(python -c "import volunteer_call_api, pathlib; print(pathlib.Path(volunteer_call_api.__file__).parent / 'static')") \
    && mkdir -p "$STATIC_DIR" \
    && cp -r /tmp/fe-build/. "$STATIC_DIR/" \
    && rm -rf /tmp/fe-build

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn volunteer_call_api.main:app --host 0.0.0.0 --port 8000"]
