# =============================================================================
# State backend
# =============================================================================
# Default: local state on the `tfstate` volume (mounted at /tfstate in the
# provision container). State carries rendered secrets (OIDC client secrets) —
# the volume is private and *.tfstate is git-ignored.
#
# For a team / multi-host setup, switch to a remote S3 backend (e.g. the
# BAUER GROUP MinIO) by replacing the block below and re-running `tofu init
# -migrate-state`:
#
#   terraform {
#     backend "s3" {
#       endpoints                   = { s3 = "https://s3.bauer-group.com" }
#       bucket                      = "iam-tfstate"
#       key                         = "cs-iam/terraform.tfstate"
#       region                      = "eu-central-1"
#       use_path_style              = true
#       skip_credentials_validation = true
#       skip_region_validation      = true
#       skip_requesting_account_id  = true
#       skip_metadata_api_check     = true
#       # access_key / secret_key via AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
#     }
#   }
# =============================================================================

terraform {
  backend "local" {
    path = "/tfstate/terraform.tfstate"
  }
}
