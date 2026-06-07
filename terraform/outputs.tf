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
  value       = try(zitadel_idp_azure_ad.entra[0].id, null)
  description = "Instance IdP id for Entra (null when federation is disabled)."
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
