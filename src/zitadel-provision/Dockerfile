# =============================================================================
# zitadel-provision — OpenTofu IaC runner (one-shot, non-destructive)
# =============================================================================
# Bundles ./terraform and applies it against Zitadel on stack-up. The
# entrypoint refuses unattended destroy/replace (see entrypoint.sh).
#
# BUILD CONTEXT = repo root (it needs ./terraform):
#   docker build -f src/zitadel-provision/Dockerfile -t cs-iam/zitadel-provision .
# =============================================================================

ARG OPENTOFU_VERSION=1.10
FROM ghcr.io/opentofu/opentofu:${OPENTOFU_VERSION}

# opentofu image is Alpine-based — add the tools the entrypoint needs.
USER root
RUN apk add --no-cache bash curl jq ca-certificates tzdata

LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.title="Zitadel Provision (OpenTofu)"
LABEL org.opencontainers.image.description="One-shot, non-destructive IaC provisioning for Zitadel (BAUER GROUP Edition)"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL com.bauer-group.image.component="provision"
LABEL com.bauer-group.image.stack="iam"
LABEL org.opencontainers.image.version="0.1.0"

WORKDIR /workspace
COPY terraform/ ./terraform/
COPY src/zitadel-provision/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Override the upstream `tofu` entrypoint with the guarded runner.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
