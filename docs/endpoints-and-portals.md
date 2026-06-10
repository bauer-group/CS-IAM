# Endpoints & portals — what's reachable where

One domain serves everything in production (`https://<IAM_HOSTNAME>`),
**path-routed** by Traefik/Coolify: `/ui/v2/login` → the login container,
everything else → the Zitadel core. This page lists each portal and endpoint.

## Human portals (open in a browser)

| Portal | Prod | Dev | Who / what |
|--------|------|-----|------------|
| **Console** — self-service + admin | `https://<IAM_HOSTNAME>/ui/console` | `http://<IAM_DEV_HOSTNAME>:8080/ui/console` | **Every user** manages their own profile, password, MFA/passkeys, sessions and sees their authorizations. **Admins** additionally manage orgs, projects, apps, users, roles/grants, policies, branding. First admin: `admin@bauer-group.com` / `ZITADEL_ADMIN_PASSWORD`. |
| **Login v2** — the sign-in flow | `https://<IAM_HOSTNAME>/ui/v2/login` | `http://localhost:<IAM_LOGIN_PORT>/ui/v2/login` | Sign-in, registration, password reset, MFA/passkey setup *during login*. Apps redirect here — you don't browse it directly. |

> **Console vs Login v2:** Login v2 is the *door* (authentication). The Console
> is the *dashboard* (self-management for users, full management for admins) —
> it's one Console, scoped by the signed-in user's permissions, not a separate
> admin tool. See [users-roles-groups.md](users-roles-groups.md) (self-service)
> and [console-guide.md](console-guide.md) (what lives where + code sync).

## OIDC / OAuth endpoints (for your apps)

Point your OIDC library at the **issuer** + **discovery** — it auto-configures
the rest. Full integration guide: [applications-oidc.md](applications-oidc.md).

| Purpose | Path (relative to the issuer) |
|---------|-------------------------------|
| **Issuer** | `https://<IAM_HOSTNAME>` |
| **Discovery** (use this) | `/.well-known/openid-configuration` |
| Authorize | `/oauth/v2/authorize` |
| Token | `/oauth/v2/token` |
| UserInfo | `/oidc/v1/userinfo` |
| JWKS (signing keys) | `/oauth/v2/keys` |
| End session (RP-logout) | `/oidc/v1/end_session` |
| Introspect / Revoke | `/oauth/v2/introspect` · `/oauth/v2/revoke` |
| **IdP callback** (register at external IdPs) | `/idps/callback` |

## Admin / automation APIs

| API | Base path | Used by |
|-----|-----------|---------|
| Assets (logo, icon, font, avatars) | `/assets/v1/…` | `zitadel-brand`, `directory-sync` |
| Management / Admin / Auth / System | `/management/v1`, `/admin/v1`, `/auth/v1`, `/system/v1` | the Terraform provider, scripts |
| Resource APIs (v2) | `/v2/users`, `/v2/…` | `directory-sync`, integrations |

## Operations

| | Path |
|---|---|
| Liveness | `/debug/healthz` |
| Readiness | `/debug/ready` |

The `provisioner` and `directory-sync` gate their startup on the **discovery**
endpoint (`/.well-known/openid-configuration`) returning 200, plus the
machine-key file existing — see [installation.md](installation.md).

## Access topology (prod / dev / internal)

- **Prod (Traefik / Coolify):** one host, `https://<IAM_HOSTNAME>`, TLS at the
  proxy, **h2c** to the core. Path split: `/ui/v2/login` → login container
  (priority), all else → core (`:8080`).
- **Dev:** core on `http://localhost:8080` (Console + issuer + APIs); login on a
  **separate host port** `http://localhost:<IAM_LOGIN_PORT>` (default 3000).
  Browse via `<IAM_DEV_HOSTNAME>` (e.g. `zitadel.localhost`, which resolves to
  loopback) so the browser URL matches the issuer.
- **Internal (compose network):** the login service calls the core at
  `http://zitadel:8080` (with a `Host:<IAM_HOSTNAME>` header override in prod);
  `provisioner`/`directory-sync` use the public issuer URL. **End users only ever
  need the public domain.**

## Who goes where (quick guide)

| You are… | Go to |
|---|---|
| an **end user** managing yourself (password, MFA, sessions) | Console — `/ui/console` |
| an **end user** signing in to an app | the app sends you to Login v2 (don't visit it directly) |
| an **admin** managing the IAM | Console — `/ui/console` |
| a **developer** wiring an app as an OIDC client | issuer + `/.well-known/openid-configuration` → [applications-oidc.md](applications-oidc.md) |
| setting up an **external IdP** | register redirect `/idps/callback` → [identity-providers.md](identity-providers.md) |
