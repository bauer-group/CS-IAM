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

## Dev login fails: "session expired" mid-login, or "instance not found"

The dev stack serves **one HTTPS origin** via the Traefik `proxy`. Browse
**`https://iam.example.test:8080/ui/console`** (add `127.0.0.1 iam.example.test` to your hosts file
and accept the self-signed cert once). Common symptoms when this isn't set up:

- **`Ihre Sitzung ist abgelaufen` / "session expired" on the MFA or password
  step:** you opened the stack over **plain HTTP**. The Login v2 session cookie
  is `Secure` (baked into the production image), so the browser drops it over
  HTTP and the session is lost mid-login. Use **`https://iam.example.test:8080`** — the
  proxy provides the required HTTPS origin.
- **`unable to set instance using origin …` / "instance not found":** the browser
  `Host` must match the instance domain `iam.example.test`. `localhost` won't
  (and `*.localhost` is forced to 127.0.0.1 inside containers, breaking the
  in-container provisioner/sync). Use the `127.0.0.1 iam.example.test` hosts
  entry and the `iam.example.test` host.
- **Broken/missing login background or favicon:** known limitation — Next.js 16
  bakes the `public/` asset manifest at build time, so the runtime branding
  overlay 404s. Dev defaults to the centred `top-to-bottom` layout (no
  background) until branding moves into the image build.

## Provider/JWT "audience" or token errors

The automation containers must reach Zitadel at the **same host as its issuer**
(the SDK takes the JWT audience from the discovered issuer, so the *host* must
match — the scheme may differ).
- dev: the issuer is `https://iam.example.test:8080` (via the proxy); the
  containers reach the core directly over internal **http** at
  `http://iam.example.test:8080` (a Docker network alias on the core) with
  `ZITADEL_INSECURE=true`. Same host → audience matches even though the connection
  is plain http. The browser uses the `127.0.0.1 iam.example.test` hosts entry
  over HTTPS.
- prod: provision/sync are on the `proxy` network and use `https://IAM_HOSTNAME`.
A real mismatch — pointing at a **different host** than the issuer — fails JWT
audience validation.

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
