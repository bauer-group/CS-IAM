# =============================================================================
# Outputs
# =============================================================================
# Read the generated OIDC client credentials to wire into each app's .env:
#   tofu output -raw app_client_secrets   (JSON map; secret)
#   tofu output app_client_ids
# =============================================================================

output "project_id" {
  value       = zitadel_project.main.id
  description = "Zitadel project id holding the apps + role catalog."
}

output "org_id" {
  value       = local.org_id
  description = "BAUER GROUP (internal) organisation id."
}

output "internal_login_org_scope" {
  value       = "urn:zitadel:iam:org:id:${local.org_id}"
  description = "OIDC scope an INTERNAL app MAY request to pin the BAUER GROUP org context — with workforce auto-redirect on, users go straight to Entra with no username prompt. Optional: without it, domain discovery still routes @<verified-domain> logins to Entra after the user enters their email."
}

output "external_org_id" {
  value       = zitadel_org.external.id
  description = "External Users (customer) organisation id."
}

output "external_project_id" {
  value       = zitadel_project.external.id
  description = "Customer-facing project id (granted to the external org)."
}

output "external_login_org_scope" {
  value       = "urn:zitadel:iam:org:id:${zitadel_org.external.id}"
  description = "OIDC scope a customer app MUST request so the login resolves to the External Users org context (its IdPs + branding). Without it the app falls back to the instance-default login (password only, no external IdP buttons)."
}

output "entra_idp_id" {
  value       = try(zitadel_org_idp_azure_ad.entra[0].id, null)
  description = "Internal-org Entra IdP id (null when federation is disabled)."
}

output "external_idp_ids" {
  value = {
    entra  = try(zitadel_org_idp_azure_ad.external_entra[0].id, null)
    google = try(zitadel_org_idp_google.external_google[0].id, null)
    oauth  = { for k, v in zitadel_org_idp_oauth.external : k => v.id }
    oidc   = { for k, v in zitadel_org_idp_oidc.external : k => v.id }
  }
  description = "External-org IdP ids per provider (null/empty for disabled ones)."
}

output "app_client_ids" {
  # client_id is non-secret but the provider marks it sensitive — unmark per item
  # so the map can be shown (the secrets stay sensitive in app_client_secrets).
  value       = { for k, v in zitadel_application_oidc.app : k => nonsensitive(v.client_id) }
  description = "Per-app OIDC client_id."
}

output "app_client_secrets" {
  value       = { for k, v in zitadel_application_oidc.app : k => v.client_secret }
  sensitive   = true
  description = "Per-app OIDC client_secret (sensitive)."
}

output "demo_app_client_id" {
  value       = try(nonsensitive(zitadel_application_oidc.demo[0].client_id), null)
  description = "Demo OIDC app client_id (project pDemo; null when DEMO_USER_PASSWORD is unset)."
}

output "demo_app_client_secret" {
  value       = try(zitadel_application_oidc.demo[0].client_secret, null)
  sensitive   = true
  description = "Demo OIDC app client_secret (sensitive)."
}
