.PHONY: lint test format

lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest --cov=tf_cost --cov-report=term-missing --cov-fail-under=80
