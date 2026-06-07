# Troubleshooting

## 502 from Traefik to Zitadel

Zitadel speaks **HTTP/2 cleartext (h2c)**. The Traefik service label must set
`loadbalancer.server.scheme=h2c` (it does in `docker-compose.traefik.yml`).
Without it every request is 502.

## Postgres `SQLSTATE 0A000` / "partitioned tables cannot be unlogged"

PostgreSQL 18 needs **Zitadel ≥ v4.11.0**. Bump `ZITADEL_VERSION`.

## `provisioner` exits with "machine key not present"

The FirstInstance key is written by `zitadel` during initial setup. Check
`docker compose logs zitadel` for setup completion; ensure the `machinekey`
volume is shared (rw on zitadel, ro on provision/sync). Increase
`PROVISION_WAIT_TIMEOUT` on a slow first boot.

## `provisioner` aborts on a destructive plan

By design — it refuses unattended destroy/replace to protect managed and
UI-made resources. Review and apply manually:
`cd terraform && tofu plan && tofu apply`.

## Provider/JWT "audience" or token errors

The automation containers must reach Zitadel at the **same URL as its issuer**.
- dev: `IAM_DEV_HOSTNAME=zitadel.localhost` (alias resolves both in browser and
  containers).
- prod: provision/sync are on the `proxy` network and use `https://IAM_HOSTNAME`.
A mismatch (e.g. pointing at `http://zitadel:8080` while the issuer is the public
HTTPS host) fails JWT audience validation.

## Federated login creates a duplicate user

Subject-preservation requires the user be imported with `userId = OID` (or the
Entra IdP set to auto-link by email). Run `import-users` before cutover and
confirm the IdP has auto-linking enabled (`terraform/idps.tf`).

## UUID `userId` rejected on import

Run `import-users --test-one` first. If Zitadel rejects the UUID id on the
deployed version, fall back to email-based matching for that app (see
[migration.md](migration.md) contingency).

## Avatar / fax / phone not updating

Those aren't in the OIDC token, so login-time JIT won't carry them — the
`directory-sync` delta job does (every `SYNC_PROFILES_INTERVAL`). Check
`docker compose logs directory-sync` and that Graph `ProfilePhoto.Read.All` /
`User.Read.All` are admin-consented.

## Sync idle / "AZURE_* not configured"

`directory-sync` idles without Entra credentials (standalone mode). Set
`AZURE_TENANT_ID/CLIENT_ID/CLIENT_SECRET` to enable it.

## Zitadel API path errors from sync

The sync targets the v2 (users) + v1 (management) APIs. If an endpoint 404s on
your Zitadel version, check the version's API reference and open an issue —
paths are validated in the integration smoke test.
