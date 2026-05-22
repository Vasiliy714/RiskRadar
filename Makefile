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