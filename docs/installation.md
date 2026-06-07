# Installation

Three deployment variants share one `.env` and the native config in
`config/zitadel/`.

## Prerequisites

- Docker + Docker Compose v2 (`docker compose version`)
- For production: a Traefik (or Coolify) reverse proxy on the external network,
  and public DNS for `IAM_HOSTNAME`.
- For the Entra federation/sync: an Entra **App Registration** (see
  [identity-providers.md](identity-providers.md)).

## 1. Generate secrets

```bash
python scripts/generate-env.py        # writes .env with fresh secrets
```

This fills `ZITADEL_MASTERKEY` (32 chars), `ZITADEL_DB_PASSWORD` and a complex
`ZITADEL_ADMIN_PASSWORD`. Then edit `.env`:

- `IAM_HOSTNAME` — production issuer (e.g. `id.bauer-group.com`)
- `AZURE_TENANT_ID` / `AZURE_CLIENT_ID` / `AZURE_CLIENT_SECRET` — optional; leave
  blank for a standalone stack (no federation/sync).
- `APP_REDIRECT_URIS` — JSON list of OIDC apps to provision (can stay `[]`).

## 2a. Development

```bash
docker compose -f docker-compose.development.yml up -d --build
```

- Console + issuer: `http://zitadel.localhost:8080` (resolves to loopback in the
  browser and to the container internally — keeps the OIDC issuer consistent).
- Login: `admin@bauer-group.com` / `ZITADEL_ADMIN_PASSWORD`.

## 2b. Production — Traefik

DNS `IAM_HOSTNAME` → host. Traefik on the `${PROXY_NETWORK}` network with a
`letsencrypt` cert resolver and `web` / `websecure` entrypoints.

```bash
docker compose -f docker-compose.traefik.yml up -d
```

Zitadel speaks **h2c** — the compose already sets
`loadbalancer.server.scheme=h2c` (without it Traefik returns 502).

## 2c. Production — Coolify

Import `docker-compose.coolify.yml`, set the env in the Coolify dashboard, and
bind the domain to the `zitadel` service (target port 8080, HTTP2/h2c enabled).

## 3. Bootstrap order (automatic)

`zitadel-db` (healthy) → `zitadel` (writes the machine key, runs FirstInstance)
→ `zitadel-provision` (OpenTofu applies IdPs/projects/apps) → `zitadel-sync`.
The provision + sync containers poll Zitadel readiness + the machine-key file
themselves (Zitadel has no in-container healthcheck — distroless image).

## 4. First checks

```bash
curl https://id.bauer-group.com/.well-known/openid-configuration
docker compose -f docker-compose.traefik.yml logs zitadel-provision
cd terraform && tofu output app_client_ids   # generated OIDC client ids
```

See [configuration.md](configuration.md) for every setting.
