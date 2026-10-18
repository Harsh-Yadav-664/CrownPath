.PHONY: up down logs cli ps seed memory demo ui ping
up:
	docker compose up -d
down:
	docker compose down
logs:
	docker compose logs -f falkordb
ps:
	docker compose ps
cli:
	docker exec -it crownpath-falkordb redis-cli
ping:
	python scripts/ping.py
seed:
	python -m lib.seed_taxonomy --all
memory:
	python -m lib.memory --demo
demo:
	python -m agent.run --crown-jewel asset:db
ui:
	uvicorn ui.app:app --port 8000
