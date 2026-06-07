# =============================================================================
# Project role catalog (Terraform-owned)
# =============================================================================
# These are the NATIVE roles managed as code. Entra-group-derived roles are
# created dynamically by directory-sync and carry var.role_prefix (e.g. "entra:")
# so the two sets never overlap — Terraform never touches synced roles and the
# sync never touches these. See the ownership boundary in the README.
# =============================================================================

resource "zitadel_project_role" "catalog" {
  for_each = toset(var.project_roles)

  org_id       = local.org_id
  project_id   = zitadel_project.main.id
  role_key     = each.value
  display_name = each.value
  group        = "native"
}

# Same catalog on the customer project, so the project grant to the External
# Users org can hand these roles to external users.
resource "zitadel_project_role" "external_catalog" {
  for_each = toset(var.project_roles)

  org_id       = local.org_id
  project_id   = zitadel_project.external.id
  role_key     = each.value
  display_name = each.value
  group        = "native"
}
