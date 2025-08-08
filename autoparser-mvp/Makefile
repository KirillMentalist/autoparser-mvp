# Использование: `make <target>`
# Подсказка: `make help`

SHELL := /bin/bash
DC ?= docker compose
API ?= apps/api

.PHONY: help
help: ## Показать доступные команды
	@grep -E '^[a-zA-Z_\-]+:.*?##' Makefile | sed -e 's/:.*##/\t– /' | sort

# --- Локальный запуск (без Docker) ---
.PHONY: dev
dev: ## Локальный run API (uvicorn)
	uvicorn $(API).main:app --reload --host 0.0.0.0 --port 8000

.PHONY: worker
worker: ## Локальный run Celery worker
	celery -A apps.api.worker.app:celery_app worker -l info

.PHONY: migrate
migrate: ## Alembic upgrade head (локально)
	alembic upgrade head

.PHONY: revision
revision: ## Alembic автогенерация миграции; MESSAGE="..."
	alembic revision --autogenerate -m "$(MESSAGE)"

.PHONY: lint
lint: ## Линтеры (ruff + mypy при желании)
	ruff check . || true
	ruff format .

.PHONY: test
test: ## Тесты (pytest)
	pytest -q

# --- Docker Compose ---
.PHONY: dc-up
dc-up: ## Поднять контейнеры (build+up -d)
	$(DC) -f ops/docker-compose.yml up -d --build

.PHONY: dc-down
dc-down: ## Остановить и удалить контейнеры
	$(DC) -f ops/docker-compose.yml down

.PHONY: dc-logs
dc-logs: ## Логи api/worker
	$(DC) -f ops/docker-compose.yml logs -f api worker

.PHONY: dc-sh-api
dc-sh-api: ## Шелл в контейнер api
	$(DC) -f ops/docker-compose.yml exec api bash || true

.PHONY: dc-sh-worker
dc-sh-worker: ## Шелл в контейнер worker
	$(DC) -f ops/docker-compose.yml exec worker bash || true

.PHONY: dc-migrate
dc-migrate: ## Alembic upgrade внутри контейнера api
	$(DC) -f ops/docker-compose.yml exec api alembic upgrade head

.PHONY: dc-revision
dc-revision: ## Alembic revision внутри контейнера api; MESSAGE="..."
	$(DC) -f ops/docker-compose.yml exec api alembic revision --autogenerate -m "$(MESSAGE)"

# --- Утилиты ---
.PHONY: seed
seed: ## Начальное наполнение (пример)
	python -m scripts.seed

.PHONY: fmt
fmt: ## Форматирование кода (ruff)
	ruff format .


.PHONY: pw-install
pw-install: ## Установить браузеры Playwright (локально)
	python -m playwright install --with-deps

.PHONY: smoke
smoke: ## Локальный smoke-тест парсера (region=92)
	python -c "from apps.api.worker.app import run_parser; print(run_parser('92'))"
