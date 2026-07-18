# =============================================================================
# IAM Database-Backup — meta image on the central BackupHelper engine
# =============================================================================
# Thin wrapper: FROM the central BackupHelper engine + IAM/Zitadel OCI labels.
# All backup logic (pg_dump, retention, manifest, S3, notifications, restore
# CLI) lives in ghcr.io/bauer-group/cs-backuphelper/backuphelper, which ships
# the postgres 18 client (matching the Zitadel server), a non-root user, tini
# and a functional healthcheck. See docs/migration.md in that repo.
# =============================================================================
FROM ghcr.io/bauer-group/cs-backuphelper/backuphelper:latest

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
LABEL org.opencontainers.image.version="0.17.5"

# Inherit ENTRYPOINT, USER, ENV, HEALTHCHECK from the base image.
