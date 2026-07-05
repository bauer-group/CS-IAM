# =============================================================================
# Login policies (per-org overrides of the instance default)
# =============================================================================
# Two org-level login policies live here:
#   1. workforce_autoredirect — BAUER GROUP: Entra-only auto-redirect (gated).
#   2. external               — External Users: LINKS the customer IdPs into the
#      org's login so they actually appear as buttons, and (chosen behaviour)
#      auto-redirects when exactly one external IdP is configured.
#
# WHY the external policy is required: org-level IdPs (idps_external.tf) are only
# provider *templates* — Zitadel shows an IdP on the login ONLY when it is linked
# into the effective login policy (the `idps` list). Without this policy the
# external IdPs would exist but never render. (The login screen derives its IdP
# set + auto-redirect from the login policy of the ORG CONTEXT the auth request
# resolves to — so external apps must also request the org scope; see
# output.external_login_org_scope and docs/identity-providers.md.)
# =============================================================================

# =============================================================================
# Workforce auto-redirect login policy (BAUER GROUP org) — PROD, gated
# =============================================================================
# When the workforce should sign in ONLY via Entra (no local password), this
# per-org login policy disables username/password and pins the org's single IdP
# (Entra), so the Login v2 auto-redirects straight to Entra instead of showing a
# login form. The break-glass "System Admins" org keeps local password login
# (the instance-default policy), so an admin can always get in at
# id-admin.example.com even when the workforce is Entra-only.
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

# =============================================================================
# External (customer) login policy — links the customer IdPs, gated on count
# =============================================================================
# Created ONLY when at least one external IdP is configured. The cardinality is
# known at plan time (it follows the count/for_each of the IdP resources, not
# their generated ids), so `count` and the single-IdP branch are plan-safe.
#
#   0 external IdPs → no policy → external org keeps the instance-default
#                     password login (local + demo accounts still work).
#   1 external IdP  → user_login = false → Login v2 AUTO-REDIRECTS to it
#                     (chosen behaviour; note this disables local external
#                     password accounts, incl. the demo user, while active).
#   ≥2 external IdPs → user_login = true → chooser: local password + buttons.
# =============================================================================
locals {
  external_idp_ids = concat(
    zitadel_org_idp_azure_ad.external_entra[*].id,
    zitadel_org_idp_google.external_google[*].id,
    [for v in zitadel_org_idp_oauth.external : v.id],
    [for v in zitadel_org_idp_oidc.external : v.id],
  )
  external_idp_single = length(local.external_idp_ids) == 1
}

resource "zitadel_login_policy" "external" {
  count = length(local.external_idp_ids) > 0 ? 1 : 0

  org_id = zitadel_org.external.id

  # ── Federation flags — the deliberate divergence from the instance default ──
  user_login         = !local.external_idp_single # 1 IdP → false (auto-redirect); ≥2 → true (chooser)
  allow_register     = false                      # no LOCAL self-registration form; social JIT via is_auto_creation on the IdPs
  allow_external_idp = true
  idps               = local.external_idp_ids # THIS is what makes the customer IdPs appear

  # ── Mirror of the instance LoginPolicy (config/zitadel/defaults.yaml) ───────
  force_mfa                = false # external IdPs perform MFA for federated users
  force_mfa_local_only     = true
  hide_password_reset      = local.external_idp_single # nothing to reset when local password is off
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
