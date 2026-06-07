# Identity Providers

Zitadel federates to one or more upstream IdPs. Entra ID is the primary; more
can be added as code.

## Microsoft Entra ID

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

## Adding Google / GitHub / Facebook (goal h)

Add the matching resource to `terraform/idps.tf` and the credentials to `.env` +
`terraform/variables.tf`. A Google stub is included (commented). Each gets the
same auto-link/auto-update behaviour. Redirect URI pattern:
`https://id.bauer-group.com/idps/callback`.

> Verify exact provider attribute names against the pinned `zitadel/zitadel`
> provider version — `tofu validate` (CI) flags drift.
