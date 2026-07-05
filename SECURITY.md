# Security Policy

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report vulnerabilities privately via GitHub's
[**Report a vulnerability**](https://github.com/bauer-group/CS-IAM/security/advisories/new)
form (repository **Security** tab → *Report a vulnerability*). This opens a private
advisory visible only to the maintainers and you.

Please include:

- affected component (Zitadel wrapper, login, provisioner, directory-sync,
  database-backup, Terraform, compose) and version/tag,
- a description and, if possible, a minimal reproduction,
- the impact you observed or expect.

We aim to acknowledge a report within **5 business days** and to agree on a
disclosure timeline with you. Please give us a reasonable window to ship a fix
before any public disclosure.

## Scope

This repository is a **deployment/orchestration stack** around
[Zitadel](https://zitadel.com). Vulnerabilities in **Zitadel itself** should be
reported to the [Zitadel project](https://github.com/zitadel/zitadel/security);
issues in the login base image belong to the `ep-zitadel` repository. Report here
anything in *this* repo's configuration, Terraform, container wrappers, sidecar
code (`directory-sync`, `database-backup`), or CI/CD.

## Supported versions

Security fixes target the latest released tag on the default branch. Older tags
are not maintained — pin to a current release.

## Handling secrets

This repository is **secret-free by design**: all credentials are injected at
runtime via environment variables (`.env`, git-ignored). If you believe a secret
was committed, report it privately as above so we can rotate and remediate.
