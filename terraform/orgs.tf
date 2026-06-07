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

# Org-level password policy override for the customer org. Internal accounts are
# unaffected — they keep the strict 12-char instance default. Relaxed length for
# customer usability; complexity (upper/lower/number) is retained, symbols are
# optional. Note: org-level policy resources fully replace the instance default
# for this org, so all has_* flags must be set explicitly.
resource "zitadel_password_complexity_policy" "external" {
  org_id        = zitadel_org.external.id
  min_length    = var.external_password_min_length
  has_uppercase = true
  has_lowercase = true
  has_number    = true
  has_symbol    = false
}
