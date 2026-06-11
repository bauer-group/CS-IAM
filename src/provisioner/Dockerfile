# ===============================================================================
# BAUER GROUP IAM Provisioner - OpenTofu IaC Runner
# ===============================================================================
# One-shot container that applies ./terraform against Zitadel on stack-up: the
# Infrastructure-as-Code layer for identity providers, the project, OIDC apps,
# the native role catalog and break-glass grants.
#
# Non-destructive by design: the entrypoint runs `tofu plan` and applies ONLY
# additive/in-place changes — any destroy/replace aborts with an alert, so
# resources created in the Zitadel UI (not in Terraform state) are never pruned.
#
# NOTE: the official ghcr.io/opentofu/opentofu image carries an
# `ONBUILD RUN exit 1` guard to forbid using it as a base; we therefore stage
# the `tofu` binary in and run on a plain Alpine base.
#
# Build context = repo root (the image bundles ./terraform):
#   docker build -f src/provisioner/Dockerfile -t cs-iam/provisioner .
#
# Documentation: https://github.com/bauer-group/CS-IAM
# ===============================================================================

# ---------------------------------------------------------------------------
# Build Arguments
# ---------------------------------------------------------------------------
ARG ALPINE_VERSION=3.23
ARG OPENTOFU_VERSION=1.12.0

# ---------------------------------------------------------------------------
# Stage 1: fetch the pinned OpenTofu binary
# ---------------------------------------------------------------------------
FROM alpine:${ALPINE_VERSION} AS tofu
ARG OPENTOFU_VERSION
RUN apk add --no-cache curl unzip ca-certificates \
    && curl -fsSL -o /tmp/tofu.zip \
        "https://github.com/opentofu/opentofu/releases/download/v${OPENTOFU_VERSION}/tofu_${OPENTOFU_VERSION}_linux_amd64.zip" \
    && unzip /tmp/tofu.zip tofu -d /usr/local/bin \
    && chmod +x /usr/local/bin/tofu \
    && /usr/local/bin/tofu version

# ---------------------------------------------------------------------------
# Stage 2: runtime
# ---------------------------------------------------------------------------
FROM alpine:${ALPINE_VERSION}

# ---------------------------------------------------------------------------
# Metadata Labels (Legacy)
# ---------------------------------------------------------------------------
LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"

# ---------------------------------------------------------------------------
# OCI Image Spec Labels
# ---------------------------------------------------------------------------
LABEL org.opencontainers.image.title="IAM Provisioner"
LABEL org.opencontainers.image.description="One-shot, non-destructive OpenTofu IaC provisioning for Zitadel - BAUER GROUP Edition"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.url="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.documentation="https://github.com/bauer-group/CS-IAM#readme"
LABEL org.opencontainers.image.version="0.12.2"

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
# bash  - the guarded-apply entrypoint        curl - Zitadel readiness probe
# jq    - destructive-plan detection          ca-certificates - TLS to the issuer
RUN apk add --no-cache bash curl jq ca-certificates tzdata

# ---------------------------------------------------------------------------
# Application (tofu binary + Terraform + guarded entrypoint)
# ---------------------------------------------------------------------------
COPY --from=tofu /usr/local/bin/tofu /usr/local/bin/tofu
WORKDIR /workspace
COPY terraform/ ./terraform/
COPY src/provisioner/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# ---------------------------------------------------------------------------
# Entrypoint (guarded, non-destructive apply)
# ---------------------------------------------------------------------------
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
