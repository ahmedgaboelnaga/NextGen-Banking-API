.PHONY: build up down down-v makemigrations migrate history current-migration downgrade inspect-network psql i18n-compile i18n-extract i18n-update

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

# I18n/Translation commands (run locally, not in Docker)
i18n-compile:
	@echo "Compiling translation files..."
	uv run python scripts/compile_translations.py

i18n-extract:
	@echo "Extracting messages from source code..."
	uv run pybabel extract -F babel.cfg -o backend/app/locales/messages.pot .

i18n-update:
	@echo "Updating translation files with new messages..."
	@for lang in en ar fr es; do \
		uv run pybabel update -i backend/app/locales/messages.pot -d backend/app/locales -l $$lang --ignore-obsolete; \
	done

# Complete i18n workflow: extract → update → compile
i18n-refresh:
	@echo "Running complete i18n refresh..."
	@$(MAKE) i18n-extract
	@$(MAKE) i18n-update
	@$(MAKE) i18n-compile
	@echo "✓ Translation files updated! Now edit .po files and run 'make i18n-compile' again."
