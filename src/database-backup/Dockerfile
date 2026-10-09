# =============================================================================
# IAM Database-Backup — meta image on the central BackupHelper engine
# =============================================================================
# Thin wrapper: FROM the central BackupHelper engine + IAM/Zitadel OCI labels.
# All backup logic (pg_dump, retention, manifest, S3, notifications, restore
# CLI) lives in ghcr.io/bauer-group/cs-backuphelper/backuphelper, which ships
# the postgres 18 client (matching the Zitadel server), a non-root user, tini
# and a functional healthcheck. See docs/migration.md in that repo.
#
# The compose files back up the Zitadel database with the engine's `postgres`
# source, whose restore copes with Zitadel's partitioned cache tables since
# BackupHelper 1.9.0. In 0.17.29 to 0.17.31 a CS-IAM plugin,
# `zitadel-postgres`, did that; its name stays registered as an alias of the
# engine's postgres source (pyproject.toml, no code of its own) for compose
# files that still use it.
#
# The machinekey and tfstate volumes are backed up with the engine's own
# `filesystem` source; the compose files configure all three sources.
#
# Multi-stage with a pytest gate: if the tests fail against this engine version
# (no partitioned-table restore, alias missing), the image cannot be assembled
# (the test stage is a hard dependency).
# =============================================================================
FROM ghcr.io/bauer-group/cs-backuphelper/backuphelper:latest AS engine

# ---------------------------------------------------------------------------
# Test stage — the engine this image is built on, with the alias installed
# ---------------------------------------------------------------------------
FROM engine AS test
USER root
WORKDIR /plugin
COPY pyproject.toml ./
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
LABEL org.opencontainers.image.description="Backup sidecar for the Zitadel stack: database, machine key and OpenTofu state - BAUER GROUP Edition"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.url="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.documentation="https://github.com/bauer-group/CS-IAM#readme"
LABEL org.opencontainers.image.version="0.17.32"

# ---------------------------------------------------------------------------
# Alias zitadel-postgres (an entry point, so it must be pip-installed)
# ---------------------------------------------------------------------------
USER root
COPY pyproject.toml /opt/cs-iam-backup/
RUN pip install --no-cache-dir /opt/cs-iam-backup \
    && rm -rf /opt/cs-iam-backup
# Hard dependency on the test stage passing (the gate).
COPY --from=test /plugin/pyproject.toml /tmp/_gate
RUN rm /tmp/_gate
USER backup

# Inherit ENTRYPOINT, ENV, WORKDIR, HEALTHCHECK from the base image.
