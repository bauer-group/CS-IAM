# =============================================================================
# Zitadel — BAUER GROUP Edition
# =============================================================================
# Sovereign re-publish of the upstream Zitadel image. We rebuild the official
# image under BAUER GROUP control (ghcr.io/bauer-group/cs-iam/zitadel) so the
# stack stays operable even if the upstream registry path changes.
#
# Today this is a thin pass-through: the upstream image is the FROM base and
# only OCI metadata + BAUER GROUP labels are layered on. Functional behaviour
# is identical to upstream — same ENTRYPOINT/CMD/EXPOSE/USER.
#
# Tomorrow (emergency path): swap BASE_ZITADEL_IMAGE to a build from a private
# fork — every other layer in this stack keeps working unchanged.
#
# Upstream:
#   - Image: https://github.com/zitadel/zitadel/pkgs/container/zitadel
#   - Code:  https://github.com/zitadel/zitadel
#   - Docs:  https://zitadel.com/docs
#
# PostgreSQL 18 requires Zitadel >= v4.11.0 (partitioned-table fix).
# =============================================================================

ARG BASE_ZITADEL_IMAGE=ghcr.io/zitadel/zitadel
ARG BASE_ZITADEL_VERSION=v4.15.0

FROM ${BASE_ZITADEL_IMAGE}:${BASE_ZITADEL_VERSION}

# Re-declare ARGs after FROM so they're available for LABEL substitution.
ARG BASE_ZITADEL_IMAGE
ARG BASE_ZITADEL_VERSION

LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.title="Zitadel"
LABEL org.opencontainers.image.description="Zitadel OIDC/IAM provider (BAUER GROUP Edition)"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.licenses="AGPL-3.0-only"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.url="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.documentation="https://github.com/bauer-group/CS-IAM#readme"
LABEL org.opencontainers.image.base.name="${BASE_ZITADEL_IMAGE}:${BASE_ZITADEL_VERSION}"
LABEL com.bauer-group.image.component="application"
LABEL com.bauer-group.image.stack="iam"
LABEL org.opencontainers.image.version="0.1.0"

# No customizations — re-publish upstream unchanged. Inherit ENTRYPOINT, CMD,
# EXPOSE, USER, WORKDIR from the Zitadel base image.
