.PHONY: up down test lint migrate seed
up:
	docker compose up --build
down:
	docker compose down
test:
	docker compose run --rm api pytest -q
lint:
	docker compose run --rm api ruff check .
migrate:
	docker compose run --rm api alembic upgrade head
seed:
	docker compose run --rm api python -m app.seed
