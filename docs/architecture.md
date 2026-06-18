# Architecture (the big picture)

One page that ties the moving parts together: **one instance, one host, three
organisations, three user populations**. Detail lives in the per-topic guides
linked at the bottom — this page is the map, not the territory.

## One instance, one host, path-routed

There is a **single Zitadel instance** behind a **single hostname**, reverse-proxied
by Traefik. Everything is path-routed on that one origin — there are no separate
admin/console/api/login hosts.

| Host | Where |
|------|-------|
| `id.bauer-group.com` | production issuer (`ZITADEL_EXTERNALDOMAIN`) |
| `iam.bauer-group.test` | development issuer (self-signed) |

| Path | Routed to |
|------|-----------|
| `…/ui/v2/login` | the **Login v2** container (`login`, port 3000) |
| `…/idps/callback` | external-IdP return (handled by core) |
| everything else (`/ui/console`, `/oidc/v1`, `/oauth/v2`, `/management/v1`, …) | **Zitadel core** (`zitadel`, h2c 8080) |

The issuer is always HTTPS (`ZITADEL_EXTERNALSECURE=true`); the proxy terminates
TLS and `X-Forwarded-Proto`/`CUSTOM_REQUEST_HEADERS` keep the scheme end-to-end.
See [endpoints-and-portals.md](endpoints-and-portals.md).

## Three organisations = three user populations

All three live in the **one** instance. Login routing is by **email domain
discovery** (`AllowDomainDiscovery`): the entered email's domain selects the org
and its IdP.

| Org | Created by | Who | Authentication |
|-----|-----------|-----|----------------|
| **System Admins** | FirstInstance (`config/zitadel/steps.yaml`) | break-glass admins + the `iam-admin` automation user | **local** password + MFA, **never** federated |
| **BAUER GROUP** | Terraform `zitadel_org.bauer` (`terraform/projects.tf`) | workforce / employees | **Entra ID** (auto-redirect in prod), local fallback in dev |
| **External Users** | Terraform `zitadel_org.external` (`terraform/orgs.tf`) | customers / B2B / partners | Entra multi-tenant, Google, social (opt-in) |

### System Admins (break-glass)
The instance's first org. The human admin logs in as
`admin@id-admin.bauer-group.com` and the headless `iam-admin` machine user runs
Terraform + directory-sync. **`id-admin.bauer-group.com` is a verified _domain_,
not a separate host** — because it is **not** one of the workforce domains, domain
discovery routes it to this local org and it can never be swept into the workforce
Entra auto-redirect. That is the password fallback that keeps admins in even when
the workforce org is Entra-only.

### BAUER GROUP (workforce)
The Terraform-created workforce tenant. In production it is **Entra-only**: when
`enable_workforce_autoredirect = true` (default) **and** Entra credentials are set,
the per-org login policy drops local password and Login v2 **auto-redirects** to
Entra (`terraform/login_policy.tf`, `idps.tf`). The corporate email domains
(`INTERNAL_ORG_DOMAINS`, e.g. `bauer-group.com`, `de.bauer-group.com`,
`us.bauer-group.com`) are verified on this org so `@domain` logins discover it and
route to Entra. **Discovery is exact — no wildcards:** `bauer-group.com` does
**not** cover `us.bauer-group.com`, so every active domain/subdomain must be
listed (and be a verified domain in the Entra tenant). A login name like
`ab@us.bauer-group.com` only routes to Entra when `us.bauer-group.com` is in the
list. Federated
users are password-less; profiles, avatars and **Entra groups → namespaced
`entra:` roles + grants** are kept current by [directory-sync](directory-sync.md).
Subject is preserved (`sub` = Entra OID) for zero-touch [migration](migration.md).

### External Users (customers)
The Terraform-created customer tenant. IdPs are attached **to this org only**:
Entra multi-tenant, Google, and a data-driven social catalog (OAuth2/OIDC) — all
opt-in via env (`terraform/idps_external.tf`) and **linked into this org's login
policy** (`zitadel_login_policy.external`) so they render as buttons; a _single_
configured IdP auto-redirects, ≥2 show a chooser. Customer apps must request the
org scope `urn:zitadel:iam:org:id:{externalOrgId}` (`tofu output
external_login_org_scope`) to reach this login context — otherwise they fall back
to the instance-default password form. **No _local_ self-registration**
(`AllowRegister: false`), but social logins **JIT-create** an external account
(`is_auto_creation`); either way the account lands here with no internal grant.
See the demo: `demo@external.bauer-group.com` in project `pDemo`
(`terraform/demo.tf`) and [identity-providers.md](identity-providers.md).

## Access model (how isolation is enforced)

Every project has `has_project_check = true` → a token is issued **only** to a user
who holds a **grant** in that project.

- Internal apps live in the **BAUER GROUP project**, which is **never granted** to
  External Users → customers cannot authenticate to internal apps.
- Customer apps live in the **External Apps project**, granted to External Users.
- Each app picks its tier with the per-app `audience` field (`"internal"` default,
  or `"external"`). See [applications-oidc.md](applications-oidc.md) and
  [users-roles-groups.md](users-roles-groups.md).

## Provisioned as code (three layers)

1. **Native config** — `config/zitadel/{defaults,steps}.yaml`: instance policies
   (password 12 + lockout, `ForceMFALocalOnly`, domain discovery), branding, SMTP,
   FirstInstance **System Admins** org + admin + `iam-admin` SA.
2. **Terraform** (`terraform/`, run by the non-destructive `provisioner` init
   container) — the BAUER GROUP + External Users orgs, IdPs, projects, OIDC apps,
   role catalog, grants, login policy. See [provisioning-terraform.md](provisioning-terraform.md).
3. **directory-sync** (Python) — Entra → Zitadel: profile/avatar/metadata delta +
   groups → roles/grants. Login-time JIT refresh is native to Zitadel.

## Images & deployment

| Image | Build |
|-------|-------|
| `cs-iam/zitadel` | thin wrapper on upstream `ghcr.io/zitadel/zitadel` (bakes config only) |
| `cs-iam/login` | branding overlay on `ghcr.io/bauer-group/ep-zitadel/zitadel-login` (EP-Zitadel fork; the login UI, 29 languages, runtime LabelPolicy branding) |
| `cs-iam/{provisioner,directory-sync,database-backup}` | the sidecars |

Three compose variants — `docker-compose.development.yml` (Traefik dev),
`docker-compose.traefik.yml` (prod), `docker-compose.coolify.yml` — share the same
services and env model. Releases are cut by `docker-release.yml` (semantic-release)
on push to `main`; `check-base-images.yml` rebuilds when an upstream base moves.

## Map of detail docs

- [endpoints-and-portals.md](endpoints-and-portals.md) — every URL/portal
- [users-roles-groups.md](users-roles-groups.md) — orgs, account types, grant model
- [identity-providers.md](identity-providers.md) — per-org IdPs
- [directory-sync.md](directory-sync.md) — Entra → Zitadel freshness
- [applications-oidc.md](applications-oidc.md) — connecting apps (internal/external)
- [provisioning-terraform.md](provisioning-terraform.md) — IaC layer
- [configuration.md](configuration.md) — `.env` + native config reference
