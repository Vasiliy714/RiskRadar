.PHONY: up up-observability down logs ps clean

up:
	docker compose up -d

up-observability:
	docker compose --profile observability up -d

down:
	docker compose down

down-observability:
	docker compose --profile observability down

logs:
	docker compose logs -f

ps:
	docker compose ps

clean:
	docker compose down -v

.PHONY: migrate migrate-create migrate-down migrate-history migrate-current

migrate:
	uv run alembic upgrade head

migrate-create:
	uv run alembic revision --autogenerate -m "$(MSG)"

migrate-down:
	uv run alembic downgrade -1

migrate-history:
	uv run alembic history --verbose

migrate-current:
	uv run alembic current