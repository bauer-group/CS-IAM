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
  description = "Name of the org created by FirstInstance (used to look up org_id)."
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

variable "external_password_min_length" {
  type        = number
  default     = 8
  description = "Minimum password length for the external org (relaxed from the strict instance default)."
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
  description = "Entra tenant id."
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
