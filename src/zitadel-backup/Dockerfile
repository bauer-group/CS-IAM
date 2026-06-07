# =============================================================================
# zitadel-backup — PostgreSQL snapshot sidecar
# =============================================================================
# Multi-stage build with an integrated pytest gate.
#   docker build -t cs-iam/zitadel-backup .
# pg_client major version is pinned to match the Zitadel Postgres server.
# =============================================================================

ARG PG_CLIENT_VERSION=18

# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.14-alpine AS builder
RUN apk add --no-cache build-base libffi-dev
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: test ───────────────────────────────────────────────────────────
FROM python:3.14-alpine AS test
ARG PG_CLIENT_VERSION
RUN apk add --no-cache build-base libffi-dev "postgresql${PG_CLIENT_VERSION}-client"
WORKDIR /app
COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt
COPY src/ ./src/
COPY tests/ ./tests/
COPY pytest.ini ./
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN env -i HOME="$HOME" PATH="$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
        pytest tests/ -v --tb=short

# ── Stage 3: production ─────────────────────────────────────────────────────
FROM python:3.14-alpine AS prod
ARG PG_CLIENT_VERSION

LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.title="Zitadel Backup"
LABEL org.opencontainers.image.description="PostgreSQL snapshot sidecar for the Zitadel stack (BAUER GROUP Edition)"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL com.bauer-group.image.component="backup"
LABEL com.bauer-group.image.stack="iam"
LABEL org.opencontainers.image.version="0.1.0"

RUN apk add --no-cache "postgresql${PG_CLIENT_VERSION}-client" tini tzdata ca-certificates procps \
    && addgroup -g 1001 -S backup \
    && adduser -S -D -u 1001 -G backup -h /home/backup backup

COPY --from=builder /install /usr/local
COPY --from=test /app/pytest.ini /tmp/_test_passed
RUN rm /tmp/_test_passed

WORKDIR /app
COPY --chown=backup:backup src/ ./src/

ENV PYTHONPATH=/app/src PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN mkdir -p /data && chown backup:backup /data
VOLUME ["/data"]
USER backup

HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD pgrep -f "python.*main.py" || exit 1

ENTRYPOINT ["/sbin/tini", "--", "python", "src/main.py"]

# Usage:
#   (default)  scheduler daemon
#   --now      single snapshot
#   cli <create|list|verify|restore|prune>
