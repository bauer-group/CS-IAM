# ===============================================================================
# BAUER GROUP Zitadel - OIDC/IAM Provider Image
# ===============================================================================
# Thin, sovereign re-publish of the official Zitadel image under BAUER GROUP
# control (ghcr.io/bauer-group/cs-iam/zitadel) so the stack stays operable even
# if the upstream registry path changes, is paywalled, or is retired.
#
# Adds:
#   - The secret-free BAUER GROUP default config baked in (defaults.yaml +
#     steps.yaml at /zitadel/config) so the stack does not depend on host
#     bind-mounts; override by bind-mounting your own files over those paths
#   - OCI + BAUER GROUP metadata
#   - A stable, owned image path the compose files pull from
#
# Build context = repo root (so config/ is reachable):
#   docker build -f src/zitadel/Dockerfile -t cs-iam/zitadel .
#
# Emergency fork path: swap BASE_ZITADEL_IMAGE to an internal fork build — every
# other layer in this stack (compose, config, sidecars) keeps working unchanged.
#
# PostgreSQL 18 requires Zitadel >= v4.11.0 (partitioned-table fix).
#
# Documentation: https://github.com/bauer-group/CS-IAM
# ===============================================================================

# ---------------------------------------------------------------------------
# Build Arguments
# ---------------------------------------------------------------------------
# Pinned minor (avoids a surprise major jump). The base-image monitor rebuilds
# when this tag's digest moves; Dependabot proposes tag bumps.
ARG BASE_ZITADEL_IMAGE=ghcr.io/zitadel/zitadel
ARG BASE_ZITADEL_VERSION=v4.15.0

# ---------------------------------------------------------------------------
# Base Image
# ---------------------------------------------------------------------------
FROM ${BASE_ZITADEL_IMAGE}:${BASE_ZITADEL_VERSION}

# Re-declare after FROM so they're available for LABEL substitution.
ARG BASE_ZITADEL_IMAGE
ARG BASE_ZITADEL_VERSION

# ---------------------------------------------------------------------------
# Metadata Labels (Legacy)
# ---------------------------------------------------------------------------
LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"

# ---------------------------------------------------------------------------
# OCI Image Spec Labels
# https://github.com/opencontainers/image-spec/blob/main/annotations.md
# ---------------------------------------------------------------------------
LABEL org.opencontainers.image.title="Zitadel"
LABEL org.opencontainers.image.description="Zitadel OIDC/IAM provider - BAUER GROUP Edition (Entra federation, IaC provisioning, directory sync)"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.licenses="AGPL-3.0-only"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.url="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.documentation="https://github.com/bauer-group/CS-IAM#readme"
LABEL org.opencontainers.image.base.name="${BASE_ZITADEL_IMAGE}:${BASE_ZITADEL_VERSION}"
LABEL org.opencontainers.image.version="0.1.3"

# ---------------------------------------------------------------------------
# Baked-in default configuration (secret-free)
# ---------------------------------------------------------------------------
# Bake the DefaultInstance + FirstInstance config into the image so the stack
# does not rely on host bind-mounts, which are fragile (a missing host path
# silently becomes an empty dir; SELinux/Windows path quirks bite). The compose
# command points at these paths; override at runtime by bind-mounting your own
# files over them. NO secrets are baked — the admin password and all credentials
# arrive through ZITADEL_* env vars at runtime.
COPY config/zitadel/defaults.yaml /zitadel/config/defaults.yaml
COPY config/zitadel/steps.yaml /zitadel/config/steps.yaml

# Inherit ENTRYPOINT, CMD, EXPOSE, USER (zitadel, uid 1000) and WORKDIR from the
# base image — no behavioural change beyond the baked config above.
