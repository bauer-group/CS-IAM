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

output "external_org_id" {
  value       = zitadel_org.external.id
  description = "External Users (customer) organisation id."
}

output "external_project_id" {
  value       = zitadel_project.external.id
  description = "Customer-facing project id (granted to the external org)."
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
  value       = { for k, v in zitadel_application_oidc.app : k => v.client_id }
  description = "Per-app OIDC client_id."
}

output "app_client_secrets" {
  value       = { for k, v in zitadel_application_oidc.app : k => v.client_secret }
  sensitive   = true
  description = "Per-app OIDC client_secret (sensitive)."
}
