# Migration: Entra ID (direct) → Zitadel

Apps currently talk OIDC **directly** to Entra. We insert Zitadel as the broker
so it becomes the single SSO front-end, **without breaking existing accounts**.

## The key idea — subject-preservation

Apps recognise returning users by the subject they stored. We make Zitadel emit
the **same value** by creating each Zitadel user with **`userId = Entra OID`**.
The app-facing `sub` is then identical to before → **no app changes, no DB
rewrites, no fallback code**. Avatars and extended data are carried over and
kept fresh by `directory-sync`.

> Caveat — Microsoft's OIDC `sub` is *pairwise* (per app registration), not the
> OID. Apps keyed on the `oid` claim or **email** preserve cleanly (e.g. Outline
> with `OIDC_USERNAME_CLAIM=email`). An app that stored Entra's pairwise `sub`
> cannot be kept stable by any broker → one-time email re-link. Run the
> discovery step to find these.

## Step-by-step (app-by-app; small blast radius)

1. **Stand up the stack** with `AZURE_*` set; confirm the Entra IdP, project and
   apps are provisioned (`tofu output`).
2. **Per-app discovery**
   ```bash
   docker compose run --rm directory-sync discover-subject-keys
   ```
   For each app confirm what it keys on (oid / pairwise sub / email).
3. **Verify subject-preservation works**
   ```bash
   docker compose run --rm directory-sync import-users --test-one
   ```
   Confirms Zitadel accepts `userId = <Entra OID UUID>` and the fetched user id
   equals the OID.
4. **Bulk import** the affected users (before cutover):
   ```bash
   docker compose run --rm directory-sync import-users
   ```
   Creates password-less users with `userId = OID`, plus metadata + avatar.
5. **Switch each app's OIDC config** from Entra-direct to Zitadel:
   ```env
   OIDC_ISSUER=https://id.bauer-group.com
   OIDC_CLIENT_ID=<from tofu output>
   OIDC_CLIENT_SECRET=<from tofu output>
   OIDC_SCOPES=openid profile email urn:zitadel:iam:user:metadata
   ```
   First federated login auto-links by email to the imported user → `sub` = OID.
6. **Verify**: log in; the app shows the **existing** account (no duplicate).
   Confirm avatar + extended attributes present.

The cutover **does not stop apps or rewrite their databases**.

## Contingency (pairwise-sub apps only)

If discovery proves an app stored Entra's pairwise `sub`, re-bind those users by
email in that app (one-time), or use that app's own identifier-migration path.

## Rollback

Per app: revert its OIDC env to Entra-direct and restart. Zitadel is middleware
— no Entra-side change is needed; rollback is a config swap in minutes.
