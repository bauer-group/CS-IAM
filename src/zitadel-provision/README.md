# zitadel-provision

One-shot **OpenTofu** init container that applies `../../terraform` against
Zitadel on stack-up — the "Infrastructure as Code" layer for IdPs, the project,
OIDC apps and the role catalog.

## Non-destructive by design

This is the key safety property. The entrypoint:

1. waits for the FirstInstance machine key + Zitadel readiness,
2. `tofu init` + `tofu plan -detailed-exitcode`,
3. if the plan contains **any** `delete`/replace action → **aborts** and prints
   the plan instead of applying (an unattended destroy never runs),
4. otherwise applies the additive/in-place plan.

Combined with `prevent_destroy` on the project and `ignore_changes` for
UI-tunable fields, this guarantees:

- **Resources created in the Zitadel UI that are not in Terraform are never
  touched** — they are not in state, so Terraform ignores them.
- A config/state drift that *would* delete a managed resource is surfaced for a
  human, not executed.

## Run manually

The same Terraform is runnable from the host:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill in
tofu init
tofu plan
tofu apply
tofu output -raw app_client_secrets
```

## State

Local backend on the `tfstate` volume by default (`/tfstate/terraform.tfstate`).
For teams, switch to an S3/MinIO backend — see `terraform/backend.tf`.
State carries OIDC client secrets; the volume is private and `*.tfstate` is
git-ignored.
