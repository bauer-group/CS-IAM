# Zitadel — BAUER GROUP Edition

A **thin, sovereign re-publish** of the upstream Zitadel image under
`ghcr.io/bauer-group/cs-iam/zitadel`.

## Why a wrapper?

The stack should keep working even if the upstream registry path changes, gets
paywalled, or is retired. By re-publishing the image under BAUER GROUP control
we own the path our compose files pull from. Today the image is a **byte-for-byte
pass-through** — `FROM ghcr.io/zitadel/zitadel:<version>` plus OCI/BAUER GROUP
labels. No behavioural change.

## Build

```bash
docker build -t cs-iam/zitadel:test ./src/zitadel
# pin a different upstream version:
docker build \
  --build-arg BASE_ZITADEL_VERSION=v4.15.0 \
  -t cs-iam/zitadel:test ./src/zitadel
```

## Emergency fork path

If we ever need to patch Zitadel, point the base at an internal fork without
touching the rest of the stack:

```bash
docker build \
  --build-arg BASE_ZITADEL_IMAGE=ghcr.io/bauer-group/zitadel-fork \
  --build-arg BASE_ZITADEL_VERSION=patched-4.15.0 \
  -t cs-iam/zitadel:test ./src/zitadel
```

## Notes

- **PostgreSQL 18** requires Zitadel **≥ v4.11.0**.
- Zitadel speaks **HTTP/2 cleartext (h2c)** internally — the Traefik service
  needs `loadbalancer.server.scheme=h2c`.
- License: Zitadel is **AGPL-3.0** since v3. Internal self-hosting without SaaS
  redistribution is unproblematic.
