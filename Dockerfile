# syntax=docker/dockerfile:1

# ---------- Stage 1: builder ----------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
    
WORKDIR /app
    
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv
    
COPY pyproject.toml uv.lock ./
    
RUN uv sync --frozen --no-dev --no-install-project
    
COPY app ./app
    
# ---------- Stage 2: runtime ----------
FROM python:3.12-slim AS runtime
    
WORKDIR /app
    
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"
    
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app
    
RUN groupadd --system riskradar \
    && useradd --system --gid riskradar --home-dir /app --shell /usr/sbin/nologin riskradar \
    && chown -R riskradar:riskradar /app
    
USER riskradar
    
EXPOSE 8000
    
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]