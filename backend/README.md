# RT-AFF Backend API

FastAPI backend for the RT-AFF Home Repair Program Management System.

## Setup

```bash
make setup    # Create venv and install dependencies
```

## Development

```bash
make dev      # Run development server (requires PostgreSQL)
make test     # Run tests with coverage
make lint     # Run linters (black, ruff, mypy)
```

## API Documentation

With the server running, visit:
- http://localhost:8000/docs - Swagger UI
- http://localhost:8000/redoc - ReDoc
