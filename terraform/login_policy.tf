# =============================================================================
# Workforce auto-redirect login policy (BAUER GROUP org) — PROD, gated
# =============================================================================
# When the workforce should sign in ONLY via Entra (no local password), this
# per-org login policy disables username/password and pins the org's single IdP
# (Entra), so the Login v2 auto-redirects straight to Entra instead of showing a
# login form. The break-glass "System Admins" org keeps local password login
# (the instance-default policy), so an admin can always get in at
# id-admin.bauer-group.com even when the workforce is Entra-only.
#
# GATED: created only when enable_workforce_autoredirect = true AND Entra is
# configured (azure_client_id set, so zitadel_org_idp_azure_ad.entra exists). In
# dev (no Entra) it is never created, so the workforce org is never locked out.
# Wire Entra first, verify federated login, THEN flip the flag in prod.
#
# Everything EXCEPT the auth-method flags MIRRORS the instance LoginPolicy
# (config/zitadel/defaults.yaml) — the workforce keeps the system-wide session
# lifetimes and MFA catalogue ("keine Individualkrämereien"). It diverges ONLY on
# what is the whole point of the workforce tenant: IdP-only federation. Keep the
# two in sync when the instance LoginPolicy changes.
# =============================================================================

resource "zitadel_login_policy" "workforce_autoredirect" {
  count = var.enable_workforce_autoredirect && var.azure_client_id != "" ? 1 : 0

  org_id = local.org_id

  # ── Federation flags — the deliberate divergence from the instance default ──
  user_login         = false # NO local password — this is what forces the Entra path
  allow_register     = false
  allow_external_idp = true
  idps               = [zitadel_org_idp_azure_ad.entra[0].id] # single IdP -> auto-redirect

  # ── Mirror of the instance LoginPolicy (config/zitadel/defaults.yaml) ───────
  force_mfa                = false # Entra performs MFA for federated users
  force_mfa_local_only     = true
  hide_password_reset      = true # no local password to reset on this org
  ignore_unknown_usernames = true
  allow_domain_discovery   = true
  disable_login_with_email = false
  disable_login_with_phone = true
  passwordless_type        = "PASSWORDLESS_TYPE_ALLOWED"
  default_redirect_uri     = ""

  password_check_lifetime       = "2160h0m0s" # 90d
  external_login_check_lifetime = "2160h0m0s" # 90d
  mfa_init_skip_lifetime        = "2160h0m0s" # 90d
  second_factor_check_lifetime  = "720h0m0s"  # 30d
  multi_factor_check_lifetime   = "720h0m0s"  # 30d

  second_factors = ["SECOND_FACTOR_TYPE_OTP", "SECOND_FACTOR_TYPE_U2F"]
  multi_factors  = ["MULTI_FACTOR_TYPE_U2F_WITH_VERIFICATION"]
}
