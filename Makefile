.PHONY: build up down down-v makemigrations migrate history current-migration downgrade inspect-network psql

COMPOSE_FILE ?= development.yml
COMPOSE = docker compose -f $(COMPOSE_FILE)

-include .envs/.env.development
export

build:
	$(COMPOSE) up --build -d --remove-orphans

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

down-v:
	$(COMPOSE) down -v

makemigrations:
	@if [ -z "$(name)" ]; then echo "name is required"; exit 1; fi
	$(COMPOSE) exec -it api alembic revision --autogenerate -m "$(name)"

migrate:
	$(COMPOSE) exec -it api alembic upgrade head

history:
	$(COMPOSE) exec -it api alembic history

current-migration:
	$(COMPOSE) exec -it api alembic current

downgrade:
	@if [ -z "$(version)" ]; then echo "version is required"; exit 1; fi
	$(COMPOSE) exec -it api alembic downgrade $(version)

inspect-network:
	docker network inspect nextgen_local_network

psql:
	$(COMPOSE) exec -it postgres psql -U $(POSTGRES_USER) -d $(POSTGRES_DB)