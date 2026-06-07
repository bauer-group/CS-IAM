# =============================================================================
# Organisation lookup + project
# =============================================================================
# The org is created by FirstInstance (steps.yaml); we look it up by name to
# get its id for org-scoped resources. The project holds the OIDC apps and the
# role catalog, with authorization-on-auth enabled so only users holding a role
# grant may log into the project's apps (goal d).
# =============================================================================

# NOTE: data-source/resource attribute names target the zitadel/zitadel v2
# provider. `tofu validate` (CI) will flag any drift on a provider bump.
data "zitadel_orgs" "bauer" {
  name        = var.org_name
  name_method = "TEXT_QUERY_METHOD_EQUALS"
}

locals {
  org_id = one(data.zitadel_orgs.bauer.ids)
  apps   = jsondecode(var.app_redirect_uris)
}

resource "zitadel_project" "main" {
  org_id = local.org_id
  name   = var.project_name

  # Assert roles into tokens and require a project grant to authenticate —
  # this is the app-login gate driven by Entra-group → role mapping.
  project_role_assertion = true
  project_role_check     = true
  has_project_check      = true

  private_labeling_setting = "PRIVATE_LABELING_SETTING_ENFORCE_PROJECT_RESOURCE_OWNER_POLICY"

  # Belt-and-braces: even if a future plan proposed a destroy, refuse it.
  lifecycle {
    prevent_destroy = true
  }
}
