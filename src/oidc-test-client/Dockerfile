# ===============================================================================
# BAUER GROUP IAM - OIDC test client (dev/test only)
# ===============================================================================
# A tiny confidential OIDC client that runs the real auth-code + PKCE flow against
# the IAM and validates the ID token (the demo user's roles). NOT a stack
# component — built locally via the `test` compose profile, not published.
#
#   docker compose -f docker-compose.development.yml --profile test up oidc-test-client
#
# The pytest gate (stage 2) doubles as the automated role-validation test basis.
# ===============================================================================

FROM python:3.14-alpine AS builder
RUN apk add --no-cache build-base libffi-dev openssl-dev
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Test gate: the role-validation logic is unit-tested; build fails if red ────
FROM python:3.14-alpine AS test
WORKDIR /app
COPY --from=builder /install /usr/local
RUN pip install --no-cache-dir pytest
COPY app.py .
COPY tests/ ./tests/
RUN python -m pytest tests/ -q

FROM python:3.14-alpine AS prod
RUN apk add --no-cache tini
COPY --from=builder /install /usr/local
# The test stage is a hard dependency of the build.
COPY --from=test /app/app.py /tmp/_tested
WORKDIR /app
COPY app.py .
RUN adduser -S -D -u 1002 -h /app appoidc
USER appoidc
EXPOSE 8888
ENTRYPOINT ["/sbin/tini", "--", "python", "app.py"]
