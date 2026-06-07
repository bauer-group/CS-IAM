# =============================================================================
# Identity Providers (upstream federation)
# =============================================================================
# Entra ID is created only when AZURE_CLIENT_ID is set, so a standalone stack
# (no federation) provisions cleanly. Add Google / GitHub / Facebook here later
# with the corresponding zitadel_idp_* resources (goal h).
#
# Auto-linking by email + auto-creation attach a federated login to a
# pre-imported user (subject-preservation: userId = Entra OID). Auto-update
# refreshes the core profile from Entra claims on every login (freshness §3a).
# =============================================================================

resource "zitadel_idp_azure_ad" "entra" {
  count = var.azure_client_id != "" ? 1 : 0

  name          = "Microsoft / Entra ID"
  client_id     = var.azure_client_id
  client_secret = var.azure_client_secret
  scopes        = ["openid", "profile", "email", "User.Read"]

  # Restrict to our single tenant.
  tenant_type = "AZURE_AD_TENANT_TYPE_ORGANISATIONS"
  tenant_id   = var.azure_tenant_id

  email_verified = true

  # Federation behaviour:
  #   - auto-creation     JIT-create users that were not pre-imported
  #   - auto-update       refresh the profile from Entra claims on every login
  #   - auto_linking EMAIL attach a federated login to a pre-imported user
  is_linking_allowed  = true
  is_creation_allowed = true
  is_auto_creation    = true
  is_auto_update      = true
  auto_linking        = "AUTO_LINKING_OPTION_EMAIL"
}

# Example — add Google later (uncomment + provide credentials):
# resource "zitadel_idp_google" "google" {
#   count         = var.google_client_id != "" ? 1 : 0
#   name          = "Google"
#   client_id     = var.google_client_id
#   client_secret = var.google_client_secret
#   scopes        = ["openid", "profile", "email"]
#   is_linking_allowed  = true
#   is_creation_allowed = true
#   is_auto_creation    = true
#   is_auto_update      = true
# }
