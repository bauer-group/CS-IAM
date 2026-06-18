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
| Google | `EXTERNAL_GOOGLE_CLIENT_ID` / `EXTERNAL_GOOGLE_CLIENT_SECRET` |

Zitadel also has **native templates** for GitHub, GitLab and Apple — these can
be wired as first-class resources exactly like Google (`org_idp_github` etc.)
when needed; ask and they're a two-line add.

### How the customer login is actually shown (two things must line up)

An org-level IdP is only a **provider template** — Zitadel renders it on the
login **only** when two conditions hold together:

1. **The IdP is linked into the External org's login policy.** Done by
   `zitadel_login_policy.external` (`terraform/login_policy.tf`), which lists all
   configured external IdPs in its `idps`. Without this link the providers exist
   but never appear as buttons.
2. **The auth request resolves to the External org context.** The login derives
   its IdP set + branding from the login policy of the **org context**. A
   customer app must therefore request the org scope
   `urn:zitadel:iam:org:id:{externalOrgId}` (read the ready-made value from
   `tofu output external_login_org_scope`). Without it the request falls back to
   the **instance-default** policy — password form only, **no** external IdP
   buttons. Domain discovery only helps for *verified* domains, so it does **not**
   cover consumer emails (gmail.com, outlook.com, …) — the scope is required for
   B2C. See [applications-oidc.md](applications-oidc.md).

### Auto-redirect vs chooser (driven by IdP count)

The External policy adapts to how many external IdPs are configured:

| Configured external IdPs | `user_login` | Customer sees |
|--------------------------|--------------|----------------|
| **0** | *(no policy created)* | instance-default password login (local + demo accounts) |
| **1** | `false` | **auto-redirect** straight to that IdP (no form) |
| **≥2** | `true` | chooser: local password **+** all IdP buttons |

Auto-redirect for a single IdP is exactly Zitadel's rule (one linked IdP **and**
local password off). Trade-off to know: while a **single** external IdP is
active, local external password accounts (including the demo user) cannot log in
— that is the deliberate B2C behaviour. Add a second IdP, or run with none, to
keep local external logins.

### Self-registration nuance

`AllowRegister: false` disables only the **local** username/password registration
*form*. The external IdPs set `is_auto_creation = true`, so a first-time social
login **JIT-creates** an external account (B2C self-onboarding) and `auto_linking`
by email attaches further providers to the same account. This never affects
internal access: a JIT-created identity lands in the **External Users** org with
no grant on the internal project (`has_project_check`), so it can never reach
internal apps regardless of how it authenticated.

> **Security acceptance test (run once with a real IdP before go-live):** sign in
> with a Google/Microsoft account whose email is `…@bauer-group.com` via the
> **customer** login. It MUST create a **new External Users** account with no
> internal access — it must NOT link to or authenticate as the workforce user in
> the BAUER GROUP org. (`auto_linking` is expected to be org-scoped; prove it.)

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
| LinkedIn | `https://www.linkedin.com/oauth` | `openid profile email` |

**OAuth2 catalog** (`EXTERNAL_OAUTH_IDPS`) — `authorization_endpoint` /
`token_endpoint` / `user_endpoint` / `id_attribute`:

| Provider | authorization / token / user endpoints | `id_attribute` |
|----------|----------------------------------------|----------------|
| Facebook | `…/v21.0/dialog/oauth` · `graph…/v21.0/oauth/access_token` · `graph…/me?fields=id,name,email` | `id` |
| Naver | `nid.naver.com/oauth2.0/authorize` · `…/token` · `openapi.naver.com/v1/nid/me` | `response.id` |
| WeChat | `open.weixin.qq.com/connect/qrconnect` · `api.weixin.qq.com/sns/oauth2/access_token` · `…/sns/userinfo` | `openid` |
| X (Twitter) | `twitter.com/i/oauth2/authorize` · `api.twitter.com/2/oauth2/token` · `api.twitter.com/2/users/me` | `data.id` (set `use_pkce:true`) |
| TikTok | `tiktok.com/v2/auth/authorize/` · `open.tiktokapis.com/v2/oauth/token/` · `open.tiktokapis.com/v2/user/info/` | `data.user.open_id` |

A fuller copy-paste JSON example is in `terraform/terraform.tfvars.example`.

> **Caveats (honest):**
> - **Clean** (standards-based): Entra, Google, **GitHub**, **LinkedIn** (OIDC),
>   LINE, KakaoTalk, Facebook.
> - **Quirky** (work, but may need an attribute-mapping Action): **X/Twitter**
>   (requires PKCE; id is nested `data.id`), **TikTok** (uses `client_key` not
>   `client_id`; nested id), WeChat (`appid`/`secret` params + `openid`), Naver
>   (`response`-wrapped user). Treat as generic OAuth2 + a small shim if needed.
> - **Further Asian/social** addable the same way (confirm current endpoints at
>   the provider): VK / VK ID, Zalo, QQ, Weibo.
> - **NOT usable as a login IdP** (no consumer OAuth/OIDC, or messaging/review
>   only): WhatsApp, Viber, Telegram (only a non-standard Login Widget),
>   Instagram & Threads (login goes through Facebook/Meta, not standalone),
>   Medium, Xing (public OAuth retired), and the review platforms — Kununu,
>   Glassdoor, Trustpilot, Clutch, Google Reviews.

> Provider attribute names are verified against the pinned `zitadel/zitadel`
> provider; `tofu validate` (CI) flags any drift.
