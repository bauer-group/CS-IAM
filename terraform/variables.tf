# =============================================================================
# Input variables
# =============================================================================
# Set via TF_VAR_* environment variables (injected by the compose file) or a
# terraform.tfvars file (see terraform.tfvars.example).
# =============================================================================

# ── Connection ───────────────────────────────────────────────────────────────
variable "zitadel_domain" {
  type        = string
  description = "Zitadel external domain (the OIDC issuer host)."
}

variable "zitadel_port" {
  type        = string
  default     = "443"
  description = "Zitadel port (443 behind Traefik, 8080 in dev)."
}

variable "zitadel_insecure" {
  type        = bool
  default     = false
  description = "Use plain HTTP (true in dev, false behind TLS)."
}

variable "zitadel_jwt_profile_file" {
  type        = string
  default     = "/data/machinekey/iam-admin.json"
  description = "Path to the FirstInstance machine key (JSON) used for auth."
}

# ── Organisation / project ───────────────────────────────────────────────────
variable "org_name" {
  type        = string
  default     = "BAUER GROUP"
  description = "Name of the workforce org created in Terraform (zitadel_org.bauer = local.org_id)."
}

variable "project_name" {
  type        = string
  default     = "BAUER GROUP"
  description = "Zitadel project that holds the apps + role catalog."
}

variable "role_prefix" {
  type        = string
  default     = "entra:"
  description = "Namespace prefix for Entra-synced roles (kept distinct from native)."
}

variable "project_roles" {
  type        = list(string)
  default     = ["user", "admin"]
  description = "Native (Terraform-owned) project role catalog. Synced Entra roles are owned by directory-sync and carry role_prefix."
}

# ── External (customer) organisation ──────────────────────────────────────────
# A second org for customers/externals. They authenticate via OIDC against
# Zitadel but, unlike internal users, may access ONLY the apps explicitly granted
# to this org (the external project below) — never internal apps.
variable "external_org_name" {
  type        = string
  default     = "External Users"
  description = "Name of the second org holding customer/external accounts."
}

# Internal (BAUER GROUP) org email domains for DOMAIN DISCOVERY: each verified
# domain routes its @domain logins to the single Entra IdP. One tenant, many
# domains. NOT used to build loginnames (UserLoginMustBeDomain=false → loginname
# is the user's real email). Empty in dev (no Entra). In prod set the list AND
# verify each via DNS (ValidateOrgDomains is on). Set via TF_VAR_internal_org_domains.
variable "internal_org_domains" {
  type        = list(string)
  default     = []
  description = "Verified email domains of the BAUER GROUP org for domain discovery (e.g. [\"bauer-group.com\",\"de.bauer-group.com\",\"us.bauer-group.com\"])."
}

variable "external_project_name" {
  type        = string
  default     = "External Apps"
  description = "Project holding customer-facing apps; granted to the external org so its users authenticate only to these."
}

# ── Microsoft Entra ID (upstream IdP) ────────────────────────────────────────
variable "azure_client_id" {
  type        = string
  default     = ""
  description = "Entra app registration client id. Empty = skip the Entra IdP (standalone stack)."
}

variable "azure_client_secret" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Entra app registration client secret."
}

variable "azure_tenant_id" {
  type        = string
  default     = ""
  description = "Entra tenant id (internal, single-tenant)."
}

variable "enable_workforce_autoredirect" {
  type        = bool
  default     = true
  description = <<-EOT
    PROD switch (default ON): the BAUER GROUP workforce org is Entra-only — no
    local password, Login v2 auto-redirects straight to Entra. GATED on
    azure_client_id, so it activates ONLY once Entra is configured: dev (no Entra)
    is unaffected and never locked out. Set false ONLY to temporarily allow
    workforce local password login during a migration. The break-glass System
    Admins org always keeps local login at id-admin.bauer-group.com.
  EOT
}

# ── External-org identity providers (all optional; empty client id = skip) ─────
# Attached to the External Users org only (org_idp_* in idps_external.tf), so
# they appear on the customer login but never the internal one. The stack
# provisions cleanly with none configured.
variable "external_azure_client_id" {
  type        = string
  default     = ""
  description = "Multi-tenant Entra app client id for the external org (empty = skip)."
}
variable "external_azure_client_secret" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Multi-tenant Entra client secret for the external org."
}
variable "external_google_client_id" {
  type        = string
  default     = ""
  description = "Google OAuth client id for the external org (empty = skip)."
}
variable "external_google_client_secret" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Google OAuth client secret for the external org."
}
# Generic OAuth2 / OIDC providers (data-driven — add any number without new TF).
# Each is a JSON map keyed by a slug; the value carries name, credentials and
# endpoints. Use OAuth2 for providers like Facebook, WeChat, Naver, QQ, Weibo;
# OIDC for OpenID-compliant ones like LINE, KakaoTalk. A ready-to-use catalog of
# endpoints lives in terraform.tfvars.example + docs/identity-providers.md.
# NOTE: these JSON blobs carry client secrets — keep .env at chmod 600.
variable "external_oauth_idps" {
  type        = string
  default     = "{}"
  description = <<-EOT
    JSON map of generic OAuth2 IdPs for the external org, e.g.
    {"facebook":{"name":"Facebook","client_id":"…","client_secret":"…",
    "authorization_endpoint":"…","token_endpoint":"…","user_endpoint":"…",
    "id_attribute":"id","scopes":["email","public_profile"]}}
  EOT
}
variable "external_oidc_idps" {
  type        = string
  default     = "{}"
  description = <<-EOT
    JSON map of generic OIDC IdPs for the external org, e.g.
    {"line":{"name":"LINE","client_id":"…","client_secret":"…",
    "issuer":"https://access.line.me","scopes":["openid","profile","email"]}}
  EOT
}

# ── Applications ─────────────────────────────────────────────────────────────
# JSON string (from env) describing the OIDC apps to create. Parsed via
# jsondecode() in applications.tf to avoid TF_VAR complex-type quirks.
# Shape: [{ "name": "outline", "redirect_uris": ["https://.../auth/oidc.callback"] }]
variable "app_redirect_uris" {
  type        = string
  default     = "[]"
  description = "JSON array of {name, redirect_uris[]} OIDC application definitions."
}

variable "demo_user_password" {
  type        = string
  default     = ""
  sensitive   = true
  description = "Password for the illustrative demo user (demo.tf). Empty = no demo user/grant created. Set via DEMO_USER_PASSWORD."
}
