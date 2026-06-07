# Branding & Login UI

The stack runs Zitadel's **Login v2** as a dedicated `login` container, branded
to BAUER GROUP. This page covers what's customizable and how.

## Brand colors (done)

Colors live in the instance `LabelPolicy` (`config/zitadel/defaults.yaml`) and
apply to both the Console and the login:

| Token | Light | Dark |
|-------|-------|------|
| Primary | `#FF8500` (orange-500) | `#FB923C` (orange-400) |
| Background | `#FFFFFF` | `#231F1C` (brand-black) |
| Font | `#231F1C` | `#F9F8F6` (brand-light) |
| Warn | `#EF4444` | `#EF4444` |

> Colors apply at instance setup. On an already-running instance, change them in
> the Console (Branding) or via the API — re-running setup is idempotent and
> won't overwrite an existing policy.

## Logo, icon & font

These are **binary assets**, not config tokens — upload them via the Assets API
(or Console → Branding): light/dark logo, favicon/icon, and a custom font. Once
uploaded they flow into the Console and Login v2 automatically.

## Login v2 (the `login` service)

- Enabled on the instance via `ZITADEL_DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED`
  + `ZITADEL_OIDC_DEFAULTLOGINURLV2` (set in the compose files).
- Served by the official `ghcr.io/zitadel/zitadel-login` image (version-matched
  to the core) at **`/ui/v2/login`** — same domain via Traefik in prod, host
  port `IAM_LOGIN_PORT` in dev.
- Auth: reads the FirstInstance machine-key **PAT** from the shared volume
  (`ZITADEL_SERVICE_USER_TOKEN_FILE`); the container blocks until that file
  exists. Runs with gid 1000 to read the group-private key.
- In prod it calls Zitadel internally (`http://zitadel:8080`) with a
  `CUSTOM_REQUEST_HEADERS: Host:<IAM_HOSTNAME>` override so the request resolves
  to the instance.

### Layout & feel (no fork — env only)

`NEXT_PUBLIC_THEME_*` (set per `.env`):

| Var | Options |
|-----|---------|
| `LOGIN_THEME_LAYOUT` | `side-by-side`, `top-to-bottom` |
| `LOGIN_THEME_ROUNDNESS` | `edgy`, `mid`, `full` |
| `LOGIN_THEME_SPACING` | `regular`, `compact` |
| `LOGIN_THEME_APPEARANCE` | `flat`, `material` |

A background image is also supported (`NEXT_PUBLIC_THEME_BACKGROUND_IMAGE`).

## Languages

Login v2 ships ~25 locales (incl. en, de, zh, ja, ko). To **override or add**
texts, use the `SetHostedLoginTranslation` settings API per BCP-47 locale
(`en`, `de`, `fr-CH`, …) at instance or org level (permission `iam.policy.write`).
The translation JSON mirrors the upstream `locales/<lang>.json`.

## IdP provider button logos — native vs generic

| Provider type | Button on the login |
|---------------|---------------------|
| **Native** (Microsoft/Entra, Google, GitHub, GitLab, Apple) | real brand logo (bundled) |
| **Generic** OAuth2/OIDC (Facebook, LINE, WeChat, KakaoTalk, X, TikTok, LinkedIn, Naver, …) | generic icon + the configured name — **no brand logo** |

There is no per-IdP logo field for generic providers, so real logos for the
social/Asian providers require editing the login app's IdP-button rendering.

### Phase 2 — fork for per-IdP logos (planned)

`apps/login` is a **pnpm + turbo monorepo** app (`@zitadel/login` +
`@zitadel/client` + `@zitadel/proto`, Next.js standalone build). To deliver the
generic-provider logos we vendor that subset, add a name/type → logo-asset map
plus the SVGs, build the image **in CI**, and swap `LOGIN_IMAGE` to the built
image. All the wiring above (feature flags, container, Traefik route, PAT,
theming, translations) is reused unchanged — only the image swaps. Trade-off:
an upstream rebase per Zitadel release.
