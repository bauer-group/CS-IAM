# =============================================================================
# Demo login (illustrative) — makes `demo-app` actually loginable end-to-end
# =============================================================================
# A demo human user + a grant so the demo OIDC app (shipped via the
# APP_REDIRECT_URIS default) is a complete, working example — not just visible.
# Internal tier (BAUER GROUP project). Created only when DEMO_USER_PASSWORD is
# set (it is, by default, in .env.example).
#
# Login: demo@bauer-group.com / DEMO_USER_PASSWORD. MFA is set up on first login
# (ForceMFALocalOnly). Remove for a clean prod: clear DEMO_USER_PASSWORD and drop
# demo-app from APP_REDIRECT_URIS, then `tofu state rm` the demo resources — the
# non-destructive provisioner won't auto-destroy them. See docs/applications-oidc.md.
# =============================================================================

resource "zitadel_human_user" "demo" {
  count = var.demo_user_password != "" ? 1 : 0

  org_id            = local.org_id
  user_name         = "demo"
  first_name        = "Demo"
  last_name         = "User"
  email             = "demo@bauer-group.com"
  is_email_verified = true

  initial_password             = var.demo_user_password
  initial_skip_password_change = true
}

resource "zitadel_user_grant" "demo" {
  count = var.demo_user_password != "" ? 1 : 0

  org_id     = local.org_id
  project_id = zitadel_project.main.id
  user_id    = zitadel_human_user.demo[0].id
  role_keys  = ["user"]
}
