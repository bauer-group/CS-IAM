# ===============================================================================
# BAUER GROUP IAM Directory-Sync - Entra -> Zitadel Sidecar
# ===============================================================================
# Keeps Zitadel users fresh from Microsoft Entra ID:
#   - sync-profiles : Graph /users delta -> extended attributes + avatar
#   - sync-groups   : Entra groups -> namespaced project roles + user grants
#   - import-users  : one-shot migration import (userId = Entra OID)
#
# Multi-stage build with an integrated pytest gate: if the tests fail, the
# production image cannot be assembled (the test stage is a hard dependency).
#
#   docker build -t cs-iam/directory-sync src/directory-sync
#
# Documentation: https://github.com/bauer-group/CS-IAM
# ===============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - resolve Python dependencies
# ---------------------------------------------------------------------------
FROM python:3.14-alpine AS builder
RUN apk add --no-cache build-base libffi-dev openssl-dev
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2: Test - pytest gate (build fails if tests fail)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Stage 3: Production - minimal runtime
# ---------------------------------------------------------------------------
FROM python:3.14-alpine AS prod

# ---------------------------------------------------------------------------
# Metadata Labels (Legacy)
# ---------------------------------------------------------------------------
LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"

# ---------------------------------------------------------------------------
# OCI Image Spec Labels
# ---------------------------------------------------------------------------
LABEL org.opencontainers.image.title="IAM Directory-Sync"
LABEL org.opencontainers.image.description="Entra -> Zitadel directory sync (profiles, avatar, groups -> roles) - BAUER GROUP Edition"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.url="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.documentation="https://github.com/bauer-group/CS-IAM#readme"
LABEL org.opencontainers.image.version="0.1.2"

# ---------------------------------------------------------------------------
# Runtime Dependencies + Non-root User
# ---------------------------------------------------------------------------
# 'sync' is a built-in Alpine user — use a dedicated, collision-free account.
RUN apk add --no-cache tini tzdata ca-certificates procps \
    && addgroup -g 1001 -S appsync \
    && adduser -S -D -u 1001 -G appsync -h /app appsync

# Python packages from the builder; the test stage is a hard build dependency.
COPY --from=builder /install /usr/local
COPY --from=test /app/pytest.ini /tmp/_test_passed
RUN rm /tmp/_test_passed

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
WORKDIR /app
COPY --chown=appsync:appsync src/ ./src/
ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN mkdir -p /data && chown appsync:appsync /data
VOLUME ["/data"]
USER appsync

# ---------------------------------------------------------------------------
# Health Check (the scheduler process stays alive in daemon mode)
# ---------------------------------------------------------------------------
HEALTHCHECK --interval=60s --timeout=10s --start-period=20s --retries=3 \
    CMD pgrep -f "python.*main.py" || exit 1

# ---------------------------------------------------------------------------
# Entrypoint (tini -> clean signal handling for the scheduler)
# ---------------------------------------------------------------------------
ENTRYPOINT ["/sbin/tini", "--", "python", "src/main.py"]

# Usage:
#   (default)                     run the scheduler (sync-profiles + sync-groups)
#   import-users [--test-one]     one-shot migration import (userId = Entra OID)
#   sync-profiles | sync-groups   one-shot single job
#   discover-subject-keys         migration cutover helper
