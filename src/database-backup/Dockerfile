# ===============================================================================
# BAUER GROUP IAM Database-Backup - PostgreSQL Snapshot Sidecar
# ===============================================================================
# Snapshots the Zitadel PostgreSQL database with pg_dump, bundles it into a
# deterministic tar.gz + manifest (sha256), applies retention, and optionally
# uploads off-site to any S3-compatible target. Cron/interval scheduled, with
# email / webhook / Microsoft Teams alerts and a restore CLI.
#
# Multi-stage build with an integrated pytest gate (test stage gates prod).
#   docker build -t cs-iam/database-backup src/database-backup
#
# pg_client major is pinned to match the Zitadel Postgres server.
#
# Documentation: https://github.com/bauer-group/CS-IAM
# ===============================================================================

# ---------------------------------------------------------------------------
# Build Arguments
# ---------------------------------------------------------------------------
ARG PG_CLIENT_VERSION=18

# ---------------------------------------------------------------------------
# Stage 1: Builder - resolve Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.14-alpine AS builder
RUN apk add --no-cache build-base libffi-dev
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Test - pytest gate (build fails if tests fail)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Stage 3: Production - minimal runtime
# ---------------------------------------------------------------------------
FROM python:3.14-alpine AS prod
ARG PG_CLIENT_VERSION

# ---------------------------------------------------------------------------
# Metadata Labels (Legacy)
# ---------------------------------------------------------------------------
LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"

# ---------------------------------------------------------------------------
# OCI Image Spec Labels
# ---------------------------------------------------------------------------
LABEL org.opencontainers.image.title="IAM Database-Backup"
LABEL org.opencontainers.image.description="PostgreSQL snapshot sidecar for the Zitadel stack - BAUER GROUP Edition"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.url="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.documentation="https://github.com/bauer-group/CS-IAM#readme"
LABEL org.opencontainers.image.version="0.5.1"

# ---------------------------------------------------------------------------
# Runtime Dependencies + Non-root User
# ---------------------------------------------------------------------------
RUN apk add --no-cache "postgresql${PG_CLIENT_VERSION}-client" tini tzdata ca-certificates procps \
    && addgroup -g 1000 backup \
    && adduser -u 1000 -G backup -h /app -D backup

COPY --from=builder /install /usr/local
COPY --from=test /app/pytest.ini /tmp/_test_passed
RUN rm /tmp/_test_passed

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
WORKDIR /app
COPY --chown=backup:backup src/ ./src/
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN mkdir -p /data && chown backup:backup /data
VOLUME ["/data"]
USER backup

# ---------------------------------------------------------------------------
# Health Check (the scheduler process stays alive in daemon mode)
# ---------------------------------------------------------------------------
HEALTHCHECK --interval=60s --timeout=10s --start-period=15s --retries=3 \
    CMD pgrep -f "python.*main.py" || exit 1

# ---------------------------------------------------------------------------
# Entrypoint (tini -> clean signal handling for the scheduler)
# ---------------------------------------------------------------------------
ENTRYPOINT ["/sbin/tini", "--", "python", "src/main.py"]

# Usage:
#   (default)  scheduler daemon
#   --now      single snapshot
#   cli <create|list|verify|restore|prune>
