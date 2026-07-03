# syntax=docker/dockerfile:1.7

# ── Builder ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
COPY configs ./configs

RUN pip install --upgrade pip build && \
    pip wheel --wheel-dir /wheels .

# ── Runtime ──────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN groupadd --system trade && useradd --system --gid trade --home /app trade

WORKDIR /app
COPY --from=builder /wheels /wheels
COPY configs ./configs

RUN pip install --no-index --find-links=/wheels nautilus-trade && \
    rm -rf /wheels

USER trade

ENV TRADE_ENV=research \
    CATALOG_PATH=/data/catalog

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD trade info >/dev/null 2>&1 || exit 1

ENTRYPOINT ["trade"]
CMD ["info"]
