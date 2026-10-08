# =============================================================================
# IAM Database-Backup — meta image on the central BackupHelper engine
# =============================================================================
# Thin wrapper: FROM the central BackupHelper engine + IAM/Zitadel OCI labels.
# All backup logic (pg_dump, retention, manifest, S3, notifications, restore
# CLI) lives in ghcr.io/bauer-group/cs-backuphelper/backuphelper, which ships
# the postgres 18 client (matching the Zitadel server), a non-root user, tini
# and a functional healthcheck. See docs/migration.md in that repo.
#
# One plugin on top (iam_backup/, an engine Source plugin): the
# `zitadel-postgres` source — the engine's postgres source with a restore that
# copes with Zitadel's partitioned cache tables, which the engine's
# `pg_restore --clean` cannot restore over. See iam_backup/zitadel_postgres.py.
#
# Multi-stage with a pytest gate: if the plugin tests fail against this engine
# version, the image cannot be assembled (the test stage is a hard dependency).
# =============================================================================
FROM ghcr.io/bauer-group/cs-backuphelper/backuphelper:latest AS engine

# ---------------------------------------------------------------------------
# Test stage — plugin tests against the engine this image is built on
# ---------------------------------------------------------------------------
FROM engine AS test
USER root
WORKDIR /plugin
COPY pyproject.toml ./
COPY iam_backup/ ./iam_backup/
COPY tests/ ./tests/
RUN pip install --no-cache-dir ".[test]" \
    && pytest -q -p no:cacheprovider tests/

# ---------------------------------------------------------------------------
# Production stage
# ---------------------------------------------------------------------------
FROM engine

# ---------------------------------------------------------------------------
# Metadata Labels
# ---------------------------------------------------------------------------
LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"

LABEL org.opencontainers.image.title="IAM Database-Backup"
LABEL org.opencontainers.image.description="PostgreSQL snapshot sidecar for the Zitadel stack - BAUER GROUP Edition"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.url="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.documentation="https://github.com/bauer-group/CS-IAM#readme"
LABEL org.opencontainers.image.version="0.17.29"

# ---------------------------------------------------------------------------
# Plugin (registered through its entry point, so it must be pip-installed)
# ---------------------------------------------------------------------------
USER root
COPY pyproject.toml /opt/cs-iam-backup/
COPY iam_backup/ /opt/cs-iam-backup/iam_backup/
RUN pip install --no-cache-dir /opt/cs-iam-backup \
    && rm -rf /opt/cs-iam-backup
# Hard dependency on the test stage passing (the gate).
COPY --from=test /plugin/pyproject.toml /tmp/_gate
RUN rm /tmp/_gate
USER backup

# Inherit ENTRYPOINT, ENV, WORKDIR, HEALTHCHECK from the base image.
