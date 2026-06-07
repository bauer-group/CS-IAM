# =============================================================================
# Grants (break-glass / admin only)
# =============================================================================
# Dynamic per-user grants derived from Entra group membership are owned by
# zitadel-sync (namespaced with var.role_prefix) — NOT declared here, so the
# two never fight over the same objects.
#
# Use this file only for a small, stable set of break-glass authorizations that
# must survive even if the sync is down. Example (uncomment + set the user id):
#
#   resource "zitadel_user_grant" "breakglass_admin" {
#     org_id     = local.org_id
#     project_id = zitadel_project.main.id
#     user_id    = var.breakglass_user_id
#     role_keys  = ["admin"]
#   }
#
# Left intentionally empty by default.
# =============================================================================
