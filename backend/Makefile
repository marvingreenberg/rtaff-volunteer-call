.PHONY: help setup test lint format dev clean

help:
	@echo "Available targets:"
	@echo "  setup   - Create venv and install dependencies"
	@echo "  test    - Run tests with coverage"
	@echo "  lint    - Run linters (black, isort, mypy)"
	@echo "  format  - Format code with black and isort"
	@echo "  dev     - Run development server"
	@echo "  clean   - Remove build artifacts"

setup:
	uv sync

PYTEST_ARGS ?=

test:
	uv run pytest $(PYTEST_ARGS)

lint:
	uv run black --check src tests
	uv run isort --check src tests
	uv run mypy src

format:
	uv run black src tests
	uv run isort src tests

dev:
	uv run uvicorn volunteer_call_api.main:app --reload --host 0.0.0.0 --port 8001

clean:
	rm -rf .venv dist build *.egg-info .coverage htmlcov .pytest_cache .mypy_cache
