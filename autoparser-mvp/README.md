Autoparser — README

[![Windows Installer](https://github.com/KirillMentalist/autoparser-mvp/actions/workflows/windows-installer.yml/badge.svg)](https://github.com/KirillMentalist/autoparser-mvp/actions/workflows/windows-installer.yml)

**⬇ Download (latest):** https://github.com/KirillMentalist/autoparser-mvp/releases/latest/download/Autoparser-Setup.exe

Полностью автономный парсер мер господдержки с админкой, офлайн‑установщиком для Windows 11 и CI‑сборкой инсталлятора через GitHub Actions.

Содержание

1. Что это

2. Быстрый старт (локально)

3. Админка: что внутри

4. Windows: «одним EXE»

5. Полностью автономный инсталлятор (через GitHub Actions)

6. Как залить в GitHub

7. Структура репозитория

8. Переменные окружения

9. CI/CD

10. Траблшутинг

11. Лицензия

1. Что это

Вводишь регион РФ → система ищет официальные источники, снимает снапшоты, извлекает текст и прогоняет через 8‑этапный конвейер (E1–E7 — анализ Gemini, E8 — генерация ID).

Админка показывает ход задач, payload каждого шага, превью карточек и даёт скачать JSON/TXT.

Для Windows есть офлайн‑инсталлятор (не нужен Python/Docker/PS‑скрипты).

2. Быстрый старт (локально)

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install --with-deps
export GEMINI_API_KEY=...   # ключ из Google AI Studio
export REGION_DEFAULT_CODE=92
# БД/очереди (опционально):
export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/postgres
export REDIS_URL=redis://localhost:6379/0

make dev     # FastAPI на :8000
make worker  # Celery worker (если используете очереди)
# Откройте http://localhost:8000/admin/parser.html

Smoke‑тест без UI:

make pw-install
make smoke  # выполнит run_parser('92')

3. Админка: что внутри

/admin — редактор промптов E1–E8 с превью, обязательными переменными и рендером.

/admin/parser.html — панель парсинга:

Настройки: ввод/сохранение Gemini API Key (локально).

Запуски: статус, прогресс, количество URL.

Шаги: SEARCH → FETCH → CLEAN → E1…E7 → BUILD_ID → SAVE.

Payload: JSON результата любого шага.

Snapshot: просмотр сырого TXT/HTML для FETCH.

Карточка: список созданных msr_intlid, превью и JSON карточки.

4. Windows: «одним EXE»

В репо есть режим single‑exe: локальный поток вместо Celery, БД — SQLite в %LOCALAPPDATA%\Autoparser\autoparser.db, браузер Chromium пакуется рядом в ms-playwright.

Локальная сборка (по желанию):

ops\win\build_win.ps1

Результат:

dist\Autoparser\Autoparser.exe — портативный EXE;

Output\Autoparser-Setup.exe — офлайн‑инсталлятор (если стоит Inno Setup).

Для конечных пользователей рекомендуем вариант через GitHub Actions (см. ниже) — EXE/инсталлятор собираются автоматически.

5. Полностью автономный инсталлятор (через GitHub Actions)

Workflow: .github/workflows/windows-installer.yml

Как получить инсталлятор «Next→Next→Finish»:

Создайте репозиторий на GitHub и запушьте туда этот код (см. раздел ниже).

Откройте вкладку Actions и включите её (Enable workflows), если требуется.

Запустите workflow: Actions → Windows Installer → Run workflow (или просто создайте тег vX.Y.Z).

Через 5–8 минут в Artifacts будут доступны:

Autoparser-Setup.exe — офлайн‑инсталлятор (с Chromium и всем рантаймом);

Autoparser.exe — портативная версия.

Что делает CI:

Ставит зависимости и PyInstaller;

Скачивает Chromium в локальную папку ms-playwright (будет упакован в релиз);

Собирает единый EXE из ops/win/start_app.py;

Пакует всё в Inno Setup → Autoparser-Setup.exe;

Публикует артефакты.

6. Как залить в GitHub

Вариант A — через веб‑интерфейс

Соберите содержимое папки проекта (корень с файлами, не сам ZIP).

На GitHub создайте приватный репозиторий, например autoparser-mvp.

Нажмите Upload files и перетащите все файлы из папки.

Закоммитьте. Зайдите в Actions → включите workflow при необходимости.

Запустите Windows Installer → скачайте артефакты.

Вариант B — через git CLI

# в корне проекта
git init
git branch -M main

cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.venv/
.env
# Build artifacts
/dist/
/build/
/Output/
/ms-playwright/
/data/
*.db
# IDE
.vscode/
.idea/
EOF

git add .
git commit -m "Initial commit: MVP + offline Windows installer workflow"

git remote add origin https://github.com/<user-or-org>/autoparser-mvp.git
git push -u origin main

Запуск сборки по тегу:

git tag v0.1.0
git push origin v0.1.0

7. Структура репозитория

Ключевые директории:

apps/api          # FastAPI, админка, эндпоинты, runner
apps/api/admin    # статические HTML-страницы админки
apps/api/worker   # задачи парсинга (Celery) и impl для локального режима
apps/api/runner.py# переключатель Celery/локальный поток
packages/agents   # Gemini-клиент, поиск, id_builder, prompts loader
packages/scraper  # Playwright, снапшоты, очистка
packages/schemas  # JSON-схемы E1–E7 и валидатор
packages/persistence # SQLAlchemy модели и init БД
config/           # config.json (локальное хранение ключа Gemini для DEV)
ops/win           # старт/сборка EXE и скрипт Inno Setup
.github/workflows # CI для Windows-инсталлятора
prompts/          # файлы промптов E1–E8 (Markdown)

8. Переменные окружения

Минимум для LLM:

GEMINI_API_KEY=<ключ из Google AI Studio>
GEMINI_MODEL=gemini-2.5-pro
GEMINI_TEMPERATURE=0.1

Парсинг/Платформа:

REGION_DEFAULT_CODE=92
PLAYWRIGHT_HEADLESS=true
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/postgres
REDIS_URL=redis://localhost:6379/0

Windows single‑exe (встроено по умолчанию):

LOCAL_SINGLEEXE=1
# SQLite используется автоматически; путь: %LOCALAPPDATA%\Autoparser\autoparser.db

9. CI/CD

Workflow: .github/workflows/windows-installer.yml.

Триггеры: workflow_dispatch (ручной) и push тэгов v*.*.*.

Артефакты: Autoparser-Setup.exe, Autoparser.exe.

(Опционально) можно добавить релиз GitHub Releases и автозаливку инсталлятора в релиз.

10. Траблшутинг

SmartScreen предупреждает при запуске .exe — нужен код‑сигнинг сертификат. Можно подписывать на этапе CI.

Не открывается браузер после установки — откройте вручную: http://127.0.0.1:8000/admin/parser.html.

Gemini JSON-парсинг падает — проверьте ключ в /admin → Настройки; посмотрите payload шага E‑stage.

Playwright не стартует — убедитесь, что в сборке присутствует папка ms-playwright (см. артефакты), либо выполните python -m playwright install при локальном запуске.

Нет результатов — проверьте SEARCH шаг (список URL), домены и критерии «официальности».

11. Лицензия

© 2025. Все права защищены (или укажите вашу лицензию, например MIT/Proprietary).

# Test trigger
