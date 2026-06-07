# =============================================================================
# OpenTofu / Terraform — provider configuration
# =============================================================================
# Manages the Zitadel resources that are NOT expressible in defaults.yaml /
# steps.yaml: identity providers, the project, OIDC applications, the project
# role catalog and break-glass grants. Run by the provisioner init
# container (or an operator via `tofu` CLI from this directory).
#
# Auth: the FirstInstance machine key written to /data/machinekey/iam-admin.json.
# =============================================================================

terraform {
  required_version = ">= 1.6"
  required_providers {
    zitadel = {
      source  = "zitadel/zitadel"
      version = "~> 2.0"
    }
  }
}

provider "zitadel" {
  domain           = var.zitadel_domain
  insecure         = var.zitadel_insecure
  port             = var.zitadel_port
  jwt_profile_file = var.zitadel_jwt_profile_file
}
