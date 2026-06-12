# =============================================================================
# Organisations
# =============================================================================
# Two organisations with different trust levels:
#
#   - "BAUER GROUP"    (internal) — created by FirstInstance (steps.yaml),
#     looked up in projects.tf. Keeps the strict instance defaults (12-char
#     password + MFA); members access all internal apps via the grant model.
#
#   - "External Users" (customers) — created here. Relaxed password policy and
#     access ONLY to apps explicitly granted to it (the external project +
#     grant in projects.tf). Customers authenticate via OIDC against Zitadel
#     and are blocked by default from internal apps (has_project_check + no
#     project grant).
# =============================================================================

resource "zitadel_org" "external" {
  name = var.external_org_name

  # Customer accounts must never be pruned by an unattended plan.
  lifecycle {
    prevent_destroy = true
  }
}

# NOTE: no per-org policy overrides. Password complexity, lockout, session and
# credential lifetimes, branding and SMTP are all configured ONCE at the instance
# level (config/zitadel/defaults.yaml + the SMTP env) and apply to every org.
# This keeps the configuration in one place — no per-tenant "Individualkrämerei".

# ── Internal org (BAUER GROUP) verified domains — for domain discovery ───────
# One tenant, many email domains: each verified domain routes its @domain logins
# to the single Entra IdP (AllowDomainDiscovery). Empty in dev; in prod set
# var.internal_org_domains and verify each via DNS.
resource "zitadel_domain" "internal" {
  for_each = toset(var.internal_org_domains)

  org_id = local.org_id
  name   = each.value
}
