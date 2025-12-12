.PHONY: dev test lint

# Run FastAPI development server with reload
dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
test:
	python3 -m pytest -q

# Run linter (format check and lint check)
lint:
	python3 -m ruff format --check .
	python3 -m ruff check .

