.PHONY: dev test test_coverage lint format_fix lint_fix

# Development server
# Run FastAPI development server with auto-reload on code changes
# Available at http://localhost:8000
# API docs at http://localhost:8000/docs
dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Testing
# Run test suite with minimal output
test:
	python3 -m pytest -q

# Test coverage
# Run tests with coverage report in terminal and JSON format
# Generates coverage.json file for CI/CD integration
test_coverage:
	python3 -m pytest --cov=app --cov-report=term-missing --cov-report=json

# Code quality
# Check code formatting (without modifying files)
lint:
	python3 -m ruff format --check .
	python3 -m ruff check .

# Format code automatically (fixes formatting issues)
format_fix:
	python3 -m ruff format .

# Fix linting issues automatically (where possible)
lint_fix:
	python3 -m ruff check --fix .

# Database migrations
# Run database migrations to latest version
migrate:
	alembic upgrade head

# Create a new migration revision
# Usage: make revision m="description of changes"
revision:
	alembic revision --autogenerate -m "$(m)"

# Show current migration status
db-status:
	alembic current

# Rollback one migration
db-rollback:
	alembic downgrade -1

# Start database service
db-up:
	docker compose up -d db
