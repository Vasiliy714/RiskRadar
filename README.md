# RiskRadar

RiskRadar - API-сервис для анализа рисков эмитентов. Проект хранит данные об
эмитентах и документах, загружает документы в RAG-индекс, выполняет гибридный
поиск по фрагментам и готовит основу для LLM-аналитики с наблюдаемостью.

## Возможности

- Управление эмитентами через REST API.
- Загрузка текстовых, HTML и PDF-документов с разбиением на чанки.
- Индексация документов в Qdrant с dense- и sparse-векторами.
- Гибридный поиск по документам эмитента с цитатами.
- Поддержка LLM-провайдеров `mock`, `DeepSeek`, `GigaChat` и маршрутизатора с fallback.
- Circuit breaker, метрики Prometheus, request id и readiness-проверки.

## Технологии

- Python 3.12
- FastAPI и Uvicorn
- SQLAlchemy AsyncIO, asyncpg и Alembic
- PostgreSQL, Redis, Qdrant
- Pydantic v2 и pydantic-settings
- Prometheus, Grafana
- pytest, ruff, mypy

## Структура проекта

- `app/main.py` - создание FastAPI-приложения, middleware и жизненный цикл клиентов.
- `app/api/` - HTTP-эндпоинты health, metrics и API v1.
- `app/core/` - конфигурация, подключение к БД, Redis, Qdrant и общие зависимости.
- `app/db/` - SQLAlchemy-модели и перечисления домена.
- `app/repositories/` - слой доступа к данным.
- `app/rag/` - парсинг документов, нормализация, чанкинг, ingestion, индексация и поиск.
- `app/llm/` - LLM-клиенты, router, circuit breaker, структурированные ответы и embeddings.
- `app/observability/` - метрики и request id.
- `app/schemas/` - Pydantic-схемы API.
- `alembic/` - миграции базы данных.
- `deploy/` - конфигурация Prometheus и Grafana.
- `tests/` - unit и integration-тесты.

## Быстрый старт

Установите Python 3.12, Docker и `uv`. Затем подготовьте окружение:

```powershell
copy .env.example .env
uv sync
```

Поднимите инфраструктуру:

```powershell
docker compose up -d postgres redis qdrant
```

Примените миграции:

```powershell
uv run alembic upgrade head
```

Запустите API:

```powershell
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

После запуска доступны:

- `GET /healthz` - базовая проверка процесса.
- `GET /readyz` - проверка PostgreSQL, Redis и Qdrant.
- `GET /metrics` - метрики Prometheus.
- `GET /docs` - Swagger UI.

## Основные API

Эндпоинты версии v1 находятся под префиксом `/api/v1`.

- `GET /api/v1/issuers` - список эмитентов.
- `POST /api/v1/issuers` - создание эмитента.
- `GET /api/v1/issuers/{code}` - получение эмитента по коду.
- `DELETE /api/v1/issuers/{code}` - удаление эмитента.
- `POST /api/v1/documents/ingest` - загрузка документа из текста.
- `POST /api/v1/documents/ingest/upload` - загрузка документа из тела запроса.
- `GET /api/v1/issuers/{code}/search?q=...` - поиск по проиндексированным документам.

## Конфигурация

Настройки читаются из `.env`. Для локальной разработки по умолчанию используется
`APP_LLM_PROVIDER=mock`, поэтому реальные ключи LLM не обязательны.

Полезные переменные:

- `APP_LLM_PROVIDER` - `mock`, `gigachat`, `deepseek` или `router`.
- `APP_EMBEDDINGS_PROVIDER` - `mock`, `local` или `gigachat`.
- `APP_RAG_CHUNK_SIZE` и `APP_RAG_CHUNK_OVERLAP` - параметры чанкинга.
- `APP_RAG_HYBRID_ENABLED` - включает dense+sparse-поиск в Qdrant.
- `DEEPSEEK_API_KEY` - ключ DeepSeek.
- `GIGACHAT_AUTH_KEY` - OAuth-ключ GigaChat.
- `GIGACHAT_CA_BUNDLE` - путь к CA bundle для production-проверки TLS.

## Наблюдаемость

Для Prometheus и Grafana используйте профиль `observability`:

```powershell
docker compose --profile observability up -d prometheus grafana
```

Prometheus будет доступен на `http://localhost:9090`, Grafana - на
`http://localhost:3000`.

## Проверки

Запуск тестов:

```powershell
uv run pytest
```

Линтинг и типизация:

```powershell
uv run ruff check .
uv run mypy app tests
```

Integration-тесты помечены маркером `integration` и по умолчанию исключены
настройкой `pytest`.
