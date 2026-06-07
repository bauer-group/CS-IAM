# =============================================================================
# Identity Providers — internal organisation
# =============================================================================
# Microsoft Entra ID (single-tenant) for INTERNAL company users, scoped to the
# BAUER GROUP org so it appears only on the internal login — never the customer
# one. Created only when AZURE_CLIENT_ID is set, so a standalone stack (no
# federation) still provisions cleanly.
#
# Auto-linking by email + auto-creation attach a federated login to a
# pre-imported user (subject-preservation: userId = Entra OID). Auto-update
# refreshes the core profile from Entra claims on every login (freshness §3a).
#
# External-org IdPs (Entra multi-tenant, Google, and any number of social /
# Asian providers) live in idps_external.tf.
# =============================================================================

resource "zitadel_org_idp_azure_ad" "entra" {
  # Require BOTH id and secret — a half-config would be rejected by Zitadel and
  # abort the whole provision, so skip gracefully instead.
  count = var.azure_client_id != "" && var.azure_client_secret != "" ? 1 : 0

  org_id        = local.org_id
  name          = "Microsoft / Entra ID"
  client_id     = var.azure_client_id
  client_secret = var.azure_client_secret
  scopes        = ["openid", "profile", "email", "User.Read"]

  # Single tenant — only our own Entra directory. tenant_id and tenant_type are
  # mutually exclusive in Zitadel: pin the specific tenant when given, otherwise
  # restrict to work/school accounts (ORGANISATIONS).
  tenant_id   = var.azure_tenant_id != "" ? var.azure_tenant_id : null
  tenant_type = var.azure_tenant_id != "" ? null : "AZURE_AD_TENANT_TYPE_ORGANISATIONS"

  email_verified      = true
  is_linking_allowed  = true
  is_creation_allowed = true
  is_auto_creation    = true
  is_auto_update      = true
  auto_linking        = "AUTO_LINKING_OPTION_EMAIL"
}
