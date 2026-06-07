# =============================================================================
# OIDC applications
# =============================================================================
# One zitadel_application_oidc per entry in var.app_redirect_uris (JSON).
# Zitadel generates the client_id/secret — surfaced via outputs.tf, never
# pre-shared. Apps request the metadata scope so synced extended attributes
# (job_title, department, fax, …) appear in their tokens.
#
# Per-app `audience` selects which project (= access tier) the app lives in:
#   "internal" (default) → the BAUER GROUP project (internal users only)
#   "external"           → the External Apps project (granted to customers)
# All apps are owned by the internal org; externals reach the external ones via
# the project grant in projects.tf.
# =============================================================================

resource "zitadel_application_oidc" "app" {
  for_each = { for a in local.apps : a.name => a }

  org_id = local.org_id
  project_id = (
    try(each.value.audience, "internal") == "external"
    ? zitadel_project.external.id
    : zitadel_project.main.id
  )
  name = each.key

  redirect_uris             = each.value.redirect_uris
  post_logout_redirect_uris = try(each.value.post_logout_redirect_uris, [])

  response_types   = ["OIDC_RESPONSE_TYPE_CODE"]
  grant_types      = ["OIDC_GRANT_TYPE_AUTHORIZATION_CODE", "OIDC_GRANT_TYPE_REFRESH_TOKEN"]
  app_type         = "OIDC_APP_TYPE_WEB"
  auth_method_type = "OIDC_AUTH_METHOD_TYPE_BASIC"
  version          = "OIDC_VERSION_1_0"

  access_token_type           = "OIDC_TOKEN_TYPE_BEARER"
  access_token_role_assertion = true
  id_token_role_assertion     = true
  id_token_userinfo_assertion = true

  dev_mode = false
}
