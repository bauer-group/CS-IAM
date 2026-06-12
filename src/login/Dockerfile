# ===============================================================================
# BAUER GROUP IAM Login - branding overlay
# ===============================================================================
# Thin custom build ON TOP of the EP-Zitadel base login image. It does NOT
# rebuild the app — it only overlays deployment branding assets onto the served
# /app/public tree (favicon, app icons, background images, decorative SVGs).
#
# Layering:
#   ghcr.io/bauer-group/ep-zitadel/zitadel-login  (base: per-IdP brand logos)
#     └── this image: + BAUER GROUP static assets  ->  ghcr.io/bauer-group/cs-iam/login
#
# The MAIN page logo is NOT set here — it comes from Zitadel's LabelPolicy
# (Assets API / Console -> Branding) at runtime, so it needs no rebuild.
#
# Drop assets into branding/public/<path> to override the upstream asset of the
# same path (e.g. branding/public/favicon/favicon.ico,
# branding/public/images/background.jpg referenced via NEXT_PUBLIC_THEME_*).
#
# Build context = src/login:
#   docker build -t cs-iam/login src/login
#
# Documentation: https://github.com/bauer-group/CS-IAM
# ===============================================================================

# Floats on the EP-Zitadel base `latest` (matches the sibling stacks + the core
# wrapper). The base-image monitor watches `zitadel-login:latest`'s digest and
# rebuilds the overlay when EP publishes a new login image. CI builds with this
# default (it passes no build-arg); compose overrides it from LOGIN_BASE_VERSION
# in .env. Override with a fixed tag (--build-arg LOGIN_BASE_VERSION=4.15.1) for
# a reproducible pin.
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
LABEL org.opencontainers.image.description="BAUER GROUP login branding overlay on the EP-Zitadel Login v2 base"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-IAM"
LABEL org.opencontainers.image.base.name="${LOGIN_BASE_IMAGE}:${LOGIN_BASE_VERSION}"
LABEL org.opencontainers.image.version="0.0.0"

# ---------------------------------------------------------------------------
# Branding overlay
# ---------------------------------------------------------------------------
# Everything under branding/public is merged onto /app/public; same-path files
# replace the upstream asset. Empty by default (passthrough) until you add yours.
COPY branding/public/ /app/public/

# ---------------------------------------------------------------------------
# Centre the language / theme switcher
# ---------------------------------------------------------------------------
# Upstream right-aligns the footer switcher (`justify-end` + `md:max-w-full`),
# which on wide screens pushes it far to the right ("verschoben"). The source
# fix is in the EP-Zitadel fork (apps/login layout.tsx → justify-center); this
# patches the compiled className literal in the standalone bundle so the fix is
# applied without rebuilding Next.js. Idempotent — a no-op once the base image
# already ships the centred class.
USER root
RUN find /app/apps/login/.next/server -type f -name '*.js' -exec \
      sed -i 's/justify-end space-x-4 px-4 py-4 md:max-w-full md:px-8/justify-center space-x-4 px-4 py-4 md:px-8/g' {} +
USER nextjs

# Inherit ENTRYPOINT, ENV, HEALTHCHECK from the base image.
