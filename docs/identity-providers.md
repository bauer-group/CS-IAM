# Identity Providers

IdPs are **scoped per organisation**, so each org's login shows only its own
providers:

| Org | Providers |
|-----|-----------|
| **BAUER GROUP** (internal) | Microsoft Entra ID — **single-tenant** (`terraform/idps.tf`) |
| **External Users** (customers) | Entra **multi-tenant**, Google, and **any number** of OAuth2/OIDC providers — Facebook, LINE, WeChat, KakaoTalk, Naver, QQ, Weibo, … (`terraform/idps_external.tf`) |

All IdPs are **opt-in**: nothing is created until its credentials are set. The
redirect/callback URI to register at every provider is
`https://id.bauer-group.com/idps/callback`.

## Microsoft Entra ID (internal, single-tenant)

### 1. App Registration (Azure Portal)

- **App registrations → New registration**
  - Name: `Zitadel SSO`
  - Accounts: this organizational directory only
  - Redirect URI (Web): `https://id.bauer-group.com/idps/callback`
- **Certificates & secrets → New client secret** → copy the value into
  `AZURE_CLIENT_SECRET`.
- **API permissions → Application permissions** (then *Grant admin consent*):
  - `User.Read.All` — profile data for migration + sync
  - `GroupMember.Read.All` — group memberships
  - `ProfilePhoto.Read.All` — avatars
- Note the **Tenant ID** and **Client ID** → `.env`.

### 2. Provisioned by Terraform

`terraform/idps.tf` creates the Entra IdP when `AZURE_CLIENT_ID` is set, with:

- **auto-link by email** + **auto-creation** — federated logins attach to a
  pre-imported user (subject-preservation) or JIT-create otherwise.
- **auto-update** — Zitadel refreshes the core profile from Entra claims on
  every login (freshness layer 3a).

### 3. Login policy interplay

`AllowExternalIDP` + `AllowDomainDiscovery` route corporate-domain users to
Entra. Imported users are password-less → Entra-only. See
[users-roles-groups.md](users-roles-groups.md).

## External-org providers (customer login)

`terraform/idps_external.tf` attaches providers to the **External Users** org.
Two are first-class (native Zitadel templates) — set their `.env` creds:

| Provider | `.env` keys |
|----------|-------------|
| Entra **multi-tenant** | `EXTERNAL_AZURE_CLIENT_ID` / `EXTERNAL_AZURE_CLIENT_SECRET` |
| Google | `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` |

### Any number of OAuth2 / OIDC providers (data-driven)

Everything else is added **without new Terraform** through two JSON-map env
vars — `EXTERNAL_OAUTH_IDPS` (generic OAuth2) and `EXTERNAL_OIDC_IDPS` (generic
OIDC). Add a provider = add a map entry. The JSON carries client secrets, so
keep `.env` at `chmod 600`.

**OIDC catalog** (`EXTERNAL_OIDC_IDPS`) — only `issuer` + creds needed:

| Provider | `issuer` | scopes |
|----------|----------|--------|
| LINE | `https://access.line.me` | `openid profile email` |
| KakaoTalk | `https://kauth.kakao.com` | `openid account_email profile` |

**OAuth2 catalog** (`EXTERNAL_OAUTH_IDPS`) — `authorization_endpoint` /
`token_endpoint` / `user_endpoint` / `id_attribute`:

| Provider | authorization / token / user endpoints | `id_attribute` |
|----------|----------------------------------------|----------------|
| Facebook | `…/v21.0/dialog/oauth` · `graph…/v21.0/oauth/access_token` · `graph…/me?fields=id,name,email` | `id` |
| Naver | `nid.naver.com/oauth2.0/authorize` · `…/token` · `openapi.naver.com/v1/nid/me` | `response.id` |
| WeChat | `open.weixin.qq.com/connect/qrconnect` · `api.weixin.qq.com/sns/oauth2/access_token` · `…/sns/userinfo` | `openid` |

A fuller copy-paste JSON example is in `terraform/terraform.tfvars.example`.

> **Caveats (honest):** WeChat and Naver are **not** spec-compliant OAuth2 —
> WeChat uses `appid`/`secret` params + returns `openid`; Naver wraps the user
> in a `response` object. They may need attribute mapping via an Action or a
> normalising proxy. **Viber** offers no consumer OAuth login, so it can't be
> an IdP. LINE/KakaoTalk/Facebook/Google/Entra work cleanly.

> Provider attribute names are verified against the pinned `zitadel/zitadel`
> provider; `tofu validate` (CI) flags any drift.
