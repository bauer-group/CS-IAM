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

- The dev instance domain is **`iam.bauer-group.test`** — a real multi-label name
  so it is a valid WebAuthn rp.id (passkeys/U2F reject single-label names). It is
  a Docker network alias on the core (so the in-container `provisioner`/
  `directory-sync` resolve it *and* it matches the issuer) and resolves to the
  proxy on the host. A Traefik `proxy` terminates TLS (self-signed) and serves
  **one HTTPS origin**, path-routing `/ui/v2/login` to the login and everything
  else to the core. For browser access, add `127.0.0.1 iam.bauer-group.test` to
  your hosts file, then open **`https://iam.bauer-group.test:8080/ui/console`**
  and accept the self-signed cert once.
  > **HTTPS is required in dev**, not optional: the Login v2 session cookie is
  > `Secure` (baked into the production image), so over plain HTTP the browser
  > drops it and the login fails mid-flow with *"session expired"*. The proxy
  > provides the HTTPS origin so the full login (incl. MFA) works locally.
  > `localhost` won't work — the Host must match the instance domain (and
  > `*.localhost` is forced to 127.0.0.1 inside containers).
- Admin login: **`admin@bauer-group.com`** / `ZITADEL_ADMIN_PASSWORD` (the
  username is the verbatim loginname since `UserLoginMustBeDomain=false`). On
  first login you set up MFA (Authenticator app or security key).

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

`database-server` (healthy) → `zitadel` (writes the machine key, runs FirstInstance)
→ `provisioner` (OpenTofu applies IdPs/projects/apps) → `directory-sync`.
The provision + sync containers poll Zitadel readiness + the machine-key file
themselves (Zitadel has no in-container healthcheck — distroless image).

## 4. First checks

```bash
curl https://id.bauer-group.com/.well-known/openid-configuration
docker compose -f docker-compose.traefik.yml logs provisioner
cd terraform && tofu output app_client_ids   # generated OIDC client ids
```

See [configuration.md](configuration.md) for every setting, and
[endpoints-and-portals.md](endpoints-and-portals.md) for every reachable URL
(Console self-service, Login v2, OIDC endpoints, APIs, dev vs prod).
