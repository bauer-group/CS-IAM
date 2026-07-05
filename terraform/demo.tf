# =============================================================================
# Demo setup (illustrative, production-safe, fully self-contained & isolated)
# =============================================================================
# A complete demo living in the ISOLATED "External Users" org (a separate
# tenant) — its own project "pDemo", roles, one OIDC app "Demo", and a demo user
# granted rUser + rManager in pDemo only. It demonstrates real multi-tenant
# isolation: the demo user is in the external tenant and is gated per project
# (has_project_check) to the "Demo" app only — it cannot touch the internal
# BAUER GROUP tenant or its apps.
#
# Everything here is gated on DEMO_USER_PASSWORD (empty = nothing created).
# Login: demo@external.example.com / DEMO_USER_PASSWORD (MFA on first login).
# App creds: `tofu output demo_app_client_id` / `-raw demo_app_client_secret`.
# Remove for a clean prod: clear DEMO_USER_PASSWORD, then `tofu state rm` the demo
# resources (the non-destructive provisioner won't auto-destroy them).
# =============================================================================

locals {
  # nonsensitive(): we only expose the boolean "is a demo password set" (needed
  # for count/for_each), never the password value itself.
  demo_enabled = nonsensitive(var.demo_user_password != "")
  demo_roles   = ["rUser", "rManager", "rAdministrator"]
}

# ── Isolated demo project ─────────────────────────────────────────────────────
resource "zitadel_project" "demo" {
  count = local.demo_enabled ? 1 : 0

  org_id                 = zitadel_org.external.id
  name                   = "pDemo"
  project_role_assertion = true
  project_role_check     = true
  has_project_check      = true
}

# ── Demo role catalog: rUser / rManager / rAdministrator ──────────────────────
resource "zitadel_project_role" "demo" {
  for_each = local.demo_enabled ? toset(local.demo_roles) : toset([])

  org_id       = zitadel_org.external.id
  project_id   = zitadel_project.demo[0].id
  role_key     = each.value
  display_name = each.value
  group        = "demo"
}

# ── Demo OIDC application "Demo" (in pDemo) ────────────────────────────────────
resource "zitadel_application_oidc" "demo" {
  count = local.demo_enabled ? 1 : 0

  org_id     = zitadel_org.external.id
  project_id = zitadel_project.demo[0].id
  name       = "Demo"

  # demo.app.example.com = a real app you'd put behind it; localhost:8888 =
  # the in-stack OIDC test client (tests/oidc-test-client, dev `test` profile).
  redirect_uris             = ["https://demo.app.example.com/auth/callback", "http://localhost:8888/callback"]
  post_logout_redirect_uris = ["https://demo.app.example.com/", "http://localhost:8888/"]

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

# ── Demo user + grant (rUser + rManager in pDemo only) ────────────────────────
resource "zitadel_human_user" "demo" {
  count = local.demo_enabled ? 1 : 0

  org_id            = zitadel_org.external.id
  user_name         = "demo@external.example.com" # = loginname (UserLoginMustBeDomain=false)
  first_name        = "Demo"
  last_name         = "User"
  email             = "demo@external.example.com"
  is_email_verified = true

  initial_password             = var.demo_user_password
  initial_skip_password_change = true
}

resource "zitadel_user_grant" "demo" {
  count = local.demo_enabled ? 1 : 0

  org_id     = zitadel_org.external.id
  project_id = zitadel_project.demo[0].id
  user_id    = zitadel_human_user.demo[0].id
  role_keys  = ["rUser", "rManager"]

  # Roles must exist before they can be granted.
  depends_on = [zitadel_project_role.demo]
}
