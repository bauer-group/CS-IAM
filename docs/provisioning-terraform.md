# Provisioning (OpenTofu / Terraform)

The structural Zitadel resources — identity providers, the project, OIDC
applications, the native role catalog and break-glass grants — are managed as
**code** in `terraform/` and applied by the one-shot `provisioner`
container on stack-up. The same Terraform is runnable from a CLI.

## How it runs (the init container)

On `docker compose up`, `provisioner`:

1. waits for the machine key + Zitadel readiness,
2. `tofu init`,
3. `tofu plan -detailed-exitcode`,
4. **non-destructive guard** — if the plan contains any `delete`/replace it
   **aborts** and prints the plan (never an unattended destroy); otherwise it
   applies the additive/in-place plan.

## Protecting UI-made settings (important)

- Terraform manages **only declared objects**. Anything you create in the
  Zitadel console that is not in `terraform/` is **not in state → never touched
  or pruned**.
- For objects Terraform *does* own, the project has `prevent_destroy`, and the
  init container refuses any destructive plan unattended.
- Fields you intend to tune in the UI can be excluded with `ignore_changes` in
  the relevant resource.

## Run from the CLI

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # fill in
tofu init
tofu plan
tofu apply
tofu output app_client_ids
tofu output -raw app_client_secrets            # JSON map (sensitive)
```

Wire each app's `client_id` / `client_secret` into that app's `.env`.

## Adding an application

Set `APP_REDIRECT_URIS` (env, JSON) or edit `terraform/applications.tf`:

```json
[{"name":"outline","redirect_uris":["https://wiki.example.com/auth/oidc.callback"]}]
```

`tofu apply` (or restart the stack) creates the OIDC client. Read its secret via
`tofu output`.

## Adding an identity provider

Entra is in `terraform/idps.tf` (created when `AZURE_CLIENT_ID` is set). Add
Google/GitHub/Facebook with the matching `zitadel_idp_*` resources (a Google
stub is included, commented).

## State

Local backend on the `tfstate` volume by default. For teams switch to an
S3/MinIO backend (`terraform/backend.tf`) and `tofu init -migrate-state`. State
carries OIDC client secrets — keep it private; `*.tfstate` is git-ignored.

## Ownership boundary vs. sync

Terraform owns the **native role catalog** + break-glass grants. `directory-sync`
owns the **dynamic, namespaced** (`entra:`) roles/grants from Entra groups. The
two sets never overlap.
