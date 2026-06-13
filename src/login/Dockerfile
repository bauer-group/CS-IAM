# ===============================================================================
# BAUER GROUP IAM Login - namespace re-tag
# ===============================================================================
# A thin re-tag of the EP-Zitadel base login image under the cs-iam namespace
# (matches the sibling stacks + the core wrapper) plus OCI labels. It does NOT
# rebuild the app and bakes NO assets.
#
# ALL BAUER GROUP branding is RUNTIME, from Zitadel's LabelPolicy (Assets API /
# Console -> Branding), so it needs no image rebuild:
#   * main page logo  -> LabelPolicy logo  (light/dark)
#   * browser favicon -> LabelPolicy icon  (the login emits it via
#                        generateMetadata; EP-Zitadel feature/favicon-from-branding)
# The build-time login UI fixes (centred switcher, per-IdP brand logos) live in
# the base image (EP-Zitadel feature branches -> production). There is
# intentionally NO baked favicon and NO login background.
#
# Layering:
#   ghcr.io/bauer-group/ep-zitadel/zitadel-login  (base: switcher + per-IdP logos)
#     └── this image: + OCI labels  ->  ghcr.io/bauer-group/cs-iam/login
#
# Build context = src/login:
#   docker build -t cs-iam/login src/login
#
# Documentation: https://github.com/bauer-group/CS-IAM
# ===============================================================================

# Floats on the EP-Zitadel base `latest` (matches the sibling stacks). The
# base-image monitor watches `zitadel-login:latest`'s digest and rebuilds when EP
# publishes a new login image. CI builds with this default; compose overrides it
# from LOGIN_BASE_VERSION in .env (pinned to a release for reproducibility).
ARG LOGIN_BASE_IMAGE=ghcr.io/bauer-group/ep-zitadel/zitadel-login
ARG LOGIN_BASE_VERSION=latest

FROM ${LOGIN_BASE_IMAGE}:${LOGIN_BASE_VERSION}

ARG LOGIN_BASE_IMAGE
ARG LOGIN_BASE_VERSION

# ---------------------------------------------------------------------------
# Metadata Labels
# ---------------------------------------------------------------------------
LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.title="IAM Login"
LABEL org.opencontainers.image.description="BAUER GROUP cs-iam re-tag of the EP-Zitadel Login v2 base (runtime LabelPolicy branding)"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.base.name="${LOGIN_BASE_IMAGE}:${LOGIN_BASE_VERSION}"
LABEL org.opencontainers.image.version="0.0.0"

# Inherit ENTRYPOINT, USER (nextjs), ENV, HEALTHCHECK from the base image.
