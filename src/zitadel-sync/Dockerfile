# =============================================================================
# zitadel-sync — directory-sync sidecar (Graph delta → Zitadel)
# =============================================================================
# Multi-stage build with an integrated pytest gate: if tests fail, the prod
# image cannot be assembled.
#   docker build -t cs-iam/zitadel-sync .
# =============================================================================

# ── Stage 1: builder ────────────────────────────────────────────────────────
FROM python:3.14-alpine AS builder
RUN apk add --no-cache build-base libffi-dev openssl-dev
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: test (build fails if tests fail) ───────────────────────────────
FROM python:3.14-alpine AS test
RUN apk add --no-cache build-base libffi-dev openssl-dev
WORKDIR /app
COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt
COPY src/ ./src/
COPY tests/ ./tests/
COPY pytest.ini ./
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# env -i clears build args so they don't leak into Pydantic Settings during tests.
RUN env -i HOME="$HOME" PATH="$PATH" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
        pytest tests/ -v --tb=short

# ── Stage 3: production ─────────────────────────────────────────────────────
FROM python:3.14-alpine AS prod

LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.title="Zitadel Sync"
LABEL org.opencontainers.image.description="Entra → Zitadel directory-sync (profiles, avatar, groups→roles) — BAUER GROUP Edition"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL com.bauer-group.image.component="sync"
LABEL com.bauer-group.image.stack="iam"
LABEL org.opencontainers.image.version="0.1.0"

RUN apk add --no-cache tini tzdata ca-certificates procps \
    && addgroup -g 1001 -S sync \
    && adduser -S -D -u 1001 -G sync -h /home/sync sync

COPY --from=builder /install /usr/local
# Make the test stage a hard dependency of prod.
COPY --from=test /app/pytest.ini /tmp/_test_passed
RUN rm /tmp/_test_passed

WORKDIR /app
COPY --chown=sync:sync src/ ./src/

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN mkdir -p /data && chown sync:sync /data
VOLUME ["/data"]
USER sync

HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
    CMD pgrep -f "python.*main.py" || exit 1

ENTRYPOINT ["/sbin/tini", "--", "python", "src/main.py"]

# Usage:
#   (default)                       run the scheduler (profiles + groups)
#   import-users [--test-one]       one-shot migration import (userId = Entra OID)
#   sync-profiles | sync-groups     one-shot single job
#   discover-subject-keys           migration cutover helper
