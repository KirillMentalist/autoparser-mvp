# Автопарсер мер поддержки — MVP

Минимальный каркас для бэкенда (FastAPI + Celery + Redis + PostgreSQL + Playwright) и пакетов агентов.

## Быстрый старт (Docker)
1) Скопируйте `ops/.env.example` в `ops/.env` и заполните переменные.  
2) `make dc-up` — собрать и запустить контейнеры.  
3) `make dc-logs` — смотреть логи api/worker.  
4) Открыть API: `http://localhost:8000/docs`.

## Локальный старт (без Docker)
- Создайте виртуальное окружение, установите зависимости: `pip install -r requirements.txt`
- Запустите API: `make dev`
- Запустите воркер: `make worker`

## Структура
См. `repo/` раздел в ТЗ (канвас). В этом каркасе уже есть:
- FastAPI `apps/api/main.py`
- Celery worker `apps/api/worker/app.py`
- Пакеты `packages/agents`, `packages/scraper`, `packages/schemas`, `packages/persistence`
- Шаблоны JSON-схем E1–E7 и справочники (заглушки `dtr24.json`, `dtr25.json`, `geodir.json`)
- `Makefile`, `ops/docker-compose.yml`, `.env.example`

## Лицензия
MIT (на ваше усмотрение)
