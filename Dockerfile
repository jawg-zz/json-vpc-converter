# ============================================================================
# Stage 1 — Build dependencies
# ============================================================================
FROM python:3.13-slim AS builder

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml requirements.txt ./
RUN uv venv /venv && \
    . /venv/bin/activate && \
    uv pip install --no-cache -r requirements.txt

# ============================================================================
# Stage 2 — Runtime (distroless-slim, non-root)
# ============================================================================
FROM python:3.13-slim

# Create non-root user
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

WORKDIR /app

COPY --from=builder /venv /venv
COPY . .

RUN chown -R app:app /app

USER app

ENV PATH="/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=production

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
