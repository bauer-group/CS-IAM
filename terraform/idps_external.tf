# =============================================================================
# Identity Providers — external (customer) organisation
# =============================================================================
# All scoped to the External Users org, so they appear ONLY on the customer
# login. Two first-class providers (Entra multi-tenant, Google) plus a fully
# data-driven layer for any number of OAuth2 / OIDC providers — Facebook,
# LINE, WeChat, KakaoTalk, Naver, QQ, Weibo, … — added via the
# external_oauth_idps / external_oidc_idps JSON maps (no new Terraform needed).
# A copy-paste endpoint catalog lives in terraform.tfvars.example.
# Every provider is opt-in: nothing is created until its credentials are set.
# =============================================================================

locals {
  # Tolerate an empty env var (compose passes "" when unset) → treat as no IdPs.
  oauth_idps = jsondecode(var.external_oauth_idps != "" ? var.external_oauth_idps : "{}")
  oidc_idps  = jsondecode(var.external_oidc_idps != "" ? var.external_oidc_idps : "{}")
}

# ── Microsoft Entra ID — multi-tenant (any work/school + personal accounts) ──
resource "zitadel_org_idp_azure_ad" "external_entra" {
  count = var.external_azure_client_id != "" && var.external_azure_client_secret != "" ? 1 : 0

  org_id        = zitadel_org.external.id
  name          = "Microsoft account"
  client_id     = var.external_azure_client_id
  client_secret = var.external_azure_client_secret
  scopes        = ["openid", "profile", "email"]

  # COMMON = any Entra tenant + personal Microsoft accounts.
  tenant_type = "AZURE_AD_TENANT_TYPE_COMMON"

  email_verified      = true
  is_linking_allowed  = true
  is_creation_allowed = true
  is_auto_creation    = true
  is_auto_update      = true
  auto_linking        = "AUTO_LINKING_OPTION_EMAIL"
}

# ── Google ───────────────────────────────────────────────────────────────────
resource "zitadel_org_idp_google" "external_google" {
  count = var.google_client_id != "" && var.google_client_secret != "" ? 1 : 0

  org_id        = zitadel_org.external.id
  name          = "Google"
  client_id     = var.google_client_id
  client_secret = var.google_client_secret
  scopes        = ["openid", "profile", "email"]

  is_linking_allowed  = true
  is_creation_allowed = true
  is_auto_creation    = true
  is_auto_update      = true
  auto_linking        = "AUTO_LINKING_OPTION_EMAIL"
}

# ── Generic OAuth2 providers (Facebook, WeChat, Naver, QQ, Weibo, …) ─────────
resource "zitadel_org_idp_oauth" "external" {
  for_each = local.oauth_idps

  org_id        = zitadel_org.external.id
  name          = each.value.name
  client_id     = each.value.client_id
  client_secret = each.value.client_secret

  authorization_endpoint = each.value.authorization_endpoint
  token_endpoint         = each.value.token_endpoint
  user_endpoint          = each.value.user_endpoint
  id_attribute           = each.value.id_attribute
  scopes                 = try(each.value.scopes, [])
  use_pkce               = try(each.value.use_pkce, false)

  is_linking_allowed  = true
  is_creation_allowed = true
  is_auto_creation    = true
  is_auto_update      = true
  auto_linking        = "AUTO_LINKING_OPTION_EMAIL"
}

# ── Generic OIDC providers (LINE, KakaoTalk, …) ──────────────────────────────
resource "zitadel_org_idp_oidc" "external" {
  for_each = local.oidc_idps

  org_id        = zitadel_org.external.id
  name          = each.value.name
  client_id     = each.value.client_id
  client_secret = each.value.client_secret
  issuer        = each.value.issuer
  scopes        = try(each.value.scopes, ["openid", "profile", "email"])

  is_id_token_mapping = try(each.value.is_id_token_mapping, true)
  is_linking_allowed  = true
  is_creation_allowed = true
  is_auto_creation    = true
  is_auto_update      = true
}
