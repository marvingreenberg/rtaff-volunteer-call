FROM python:3.14-slim

WORKDIR /app

# Install system dependencies for weasyprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*


# Copy source code and config
COPY src/ ./src/
COPY pyproject.toml alembic.ini ./
RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "volunteer_call_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
