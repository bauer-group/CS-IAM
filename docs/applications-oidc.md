# Connecting your applications (OIDC clients)

How to onboard your own apps as OIDC clients — to the **internal** (`BAUER GROUP`)
or **external** (customer) tier — as code. Zitadel mints the credentials; you
never pre-share a secret.

## Two access tiers — which users can sign in

| Tier (`audience`) | Project | Who can authenticate |
|---|---|---|
| `internal` (default) | `BAUER GROUP` | internal users (federated + local) only |
| `external` | `External Apps` (granted to the External org) | customer accounts you grant a role to |

Every project runs `has_project_check = true`: a token is issued **only** to a
user who holds a grant with a role in that project. The internal project is never
granted to the external org, so the tiers can't cross. Full gating model:
[users-roles-groups.md](users-roles-groups.md).

> **Live example shipped — fully loginable & isolated.** Out of the box you get a
> complete, self-contained demo in its OWN project (`terraform/demo.tf`): project
> **`pDemo`** with roles **`rUser` / `rManager` / `rAdministrator`**, the OIDC app
> **`Demo`** (`demo.app.bauer-group.com`), and a demo user **`demo@bauer-group.com`**
> granted **`rUser` + `rManager` in `pDemo` only** — so it can use the `Demo` app
> and nothing else (cleanly isolated from the BAUER GROUP / External Apps
> projects; production-safe). Enabled by `DEMO_USER_PASSWORD`; MFA is set up on
> first login. App creds: `tofu output demo_app_client_id` /
> `tofu output -raw demo_app_client_secret`.
>
> **Remove for a clean prod:** clear `DEMO_USER_PASSWORD`, then `tofu state rm` the
> demo resources — the non-destructive provisioner won't auto-destroy them.

## Onboard an app — 4 steps

### 1. Declare the client (as code)

Add an entry to `APP_REDIRECT_URIS` (env, JSON) **or** edit
`terraform/applications.tf`. Per-entry fields: `name`, `redirect_uris[]`,
optional `post_logout_redirect_uris[]`, and `audience` (`"internal"` default, or
`"external"`):

```json
APP_REDIRECT_URIS=[
  {"name":"intranet","redirect_uris":["https://intranet.bauer-group.com/auth/callback"]},
  {"name":"partner-portal","audience":"external",
   "redirect_uris":["https://partners.example.com/auth/oidc.callback"],
   "post_logout_redirect_uris":["https://partners.example.com/"]}
]
```

Here `intranet` lands in the internal `BAUER GROUP` project; `partner-portal`
lands in the customer `External Apps` project.

### 2. Apply

The `provisioner` applies it automatically on the next deploy (non-destructive —
it never prunes UI-made resources). Or run it from the CLI:

```bash
cd terraform && tofu apply
```

### 3. Read the generated credentials

Zitadel generates the `client_id` + `client_secret` per app — read them back:

```bash
cd terraform
tofu output app_client_ids                 # { "intranet": "...", "partner-portal": "..." }
tofu output -raw app_client_secrets        # JSON map (sensitive)
```

Wire each app's `client_id` / `client_secret` into that app's own config or
secret manager. Never commit them.

### 4. Grant users access (role gating)

Because of `has_project_check`, a user must hold a **grant** to sign in:

- **Internal apps:** grant native roles (the `terraform/roles.tf` catalog) or let
  `directory-sync` map Entra groups → namespaced `entra:` roles + grants.
- **External apps:** grant a role in the `External Apps` project to the customer
  account (Console, Terraform, or your own flow).

See [users-roles-groups.md](users-roles-groups.md) for roles, grants and the
self-service model.

## Visual alternative — the Console (web admin)

Yes, you can create the same apps **click-by-click** in the Zitadel Console
(`https://<IAM_HOSTNAME>`, sign in as the admin):

1. Pick the org → **Projects** → open `BAUER GROUP` (internal) or `External Apps`
   (external). Choosing the project is the visual equivalent of the `audience` field.
2. **New Application** → OIDC → *Web* (or *User Agent* / *Native* with PKCE for a
   public client) → enter the redirect URI(s) → create. The Console then shows the
   generated `client_id` / `client_secret`.
3. **Authorizations** → grant the user a role in that project so they can sign in
   (`has_project_check` still applies — no grant, no token).

**Safe, but not IaC.** The non-destructive provisioner **never deletes UI-made
resources** (they aren't in its Terraform state), so a Console app keeps working
across deploys. But it is **drift**: not version-controlled, it won't reappear on
a fresh deploy, and its secret isn't in `tofu output`. Use the Console for quick
prototypes; **codify the keepers in Terraform** (`APP_REDIRECT_URIS` /
`applications.tf`) so the source of truth stays complete. Either way, Console apps
are captured by the Postgres backup.

## Client-side OIDC configuration (what your app needs)

| Setting | Value |
|---|---|
| **Issuer** | `https://<IAM_HOSTNAME>` (dev: `http://localhost:8080`) |
| **Discovery** | `<issuer>/.well-known/openid-configuration` — point your OIDC library here; it auto-configures every endpoint |
| **client_id / client_secret** | from step 3 |
| **Redirect URI** | must exactly match one you declared |
| **Flow** | Authorization Code (+ PKCE); confidential web client (HTTP Basic) by default |
| **Scopes** | `openid profile email offline_access urn:zitadel:iam:user:metadata` |

**Key claims in the token:**
- `sub` — the stable user id (= the Entra OID for migrated users — subject-preservation, so app accounts stay stable).
- `email`, `given_name`, `family_name`.
- **Roles** — asserted into the ID **and** access tokens (role assertion is on), claim `urn:zitadel:iam:org:project:roles`. Gate features on these.
- **Extended attributes** (job title, department, fax, …) — via the `urn:zitadel:iam:user:metadata` scope (synced from Entra).

For reference (all discoverable via the document above): `…/oauth/v2/authorize`,
`…/oauth/v2/token`, `…/oidc/v1/userinfo`, `…/oauth/v2/keys`,
`…/oidc/v1/end_session`. Prefer discovery over hard-coding these.

## Test the OIDC flow (with a hosted test client)

No client is bundled — use a purpose-built **hosted OIDC test client** to run the
real auth-code flow against the IAM and inspect the issued tokens:
**openidconnect.net** (Auth0 OIDC Playground) · **oauth.tools** (Curity) ·
**oidcdebugger.com**.

Quick run against the shipped **Demo** app:

1. **Allow the tester's redirect URI** on the app — add its callback (e.g.
   `https://openidconnect.net/callback` or `https://oidcdebugger.com/debug`) to
   the Demo app's `redirect_uris` in `terraform/demo.tf` (codified), or add it
   temporarily in the Console (project `pDemo` → app `Demo` → Redirect URIs).
2. **Get the credentials:** `cd terraform && tofu output demo_app_client_id` +
   `tofu output -raw demo_app_client_secret`.
3. In the tester set **Discovery** = `https://<IAM_HOSTNAME>/.well-known/openid-configuration`,
   the **client_id/secret**, **scopes** `openid profile email offline_access urn:zitadel:iam:user:metadata`,
   flow **Authorization Code (+ PKCE)**.
4. Run it → sign in as **`demo@bauer-group.com` / `DEMO_USER_PASSWORD`** (set up
   MFA on first login) → the tester returns the **ID + access token**.
5. **Verify:** decode the token (the tester does, or paste into jwt.io) → check
   `sub`, `email`, and the roles claim **`urn:zitadel:iam:org:project:roles`**
   contains `rUser` + `rManager` (and **not** `rAdministrator`) — proving the
   grant + role assertion + isolation all work.

> Hosted tools need a **reachable issuer** (your deployed domain). For purely
> **local dev** the issuer hostname must resolve identically for the browser and
> the backend (which a hosted tool can't), so test the flow after deploy — or ask
> for the in-stack client below.

**In-stack option (on request):** a small **dev-profile OIDC client container**
wired to the Demo app, so `docker compose --profile test up` gives a one-click
local round-trip that prints the decoded ID/access token + roles. Say the word
and it's added.

## App types (web / SPA / native)

The default (`terraform/applications.tf`) creates **confidential web** clients
(`client_secret` + auth-code). For a public client — SPA (browser) or native
(mobile/desktop) — use **PKCE without a secret**: in `applications.tf` set
`auth_method_type = "OIDC_AUTH_METHOD_TYPE_NONE"` and `app_type` to
`OIDC_APP_TYPE_USER_AGENT` (SPA) or `OIDC_APP_TYPE_NATIVE`. (The JSON shortcut
covers the common web case; public clients are a small TF edit.)

## See also

- [users-roles-groups.md](users-roles-groups.md) — trust tiers, role/grant gating, self-service
- [provisioning-terraform.md](provisioning-terraform.md) — IaC, state, the non-destructive guard
- [identity-providers.md](identity-providers.md) — which login methods each org offers
