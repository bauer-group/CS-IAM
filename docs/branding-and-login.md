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

## Logo, icon & font (automated — IaC)

The light/dark **logo**, **icon** and optional **font** are binary `LabelPolicy`
assets (stored in Postgres, served at runtime — not config tokens, and not
something the Terraform provider can upload). They are branded **automatically**
by the one-shot **`zitadel-brand`** service:

- Assets live in the repo at **`src/directory-sync/branding/`** (`logo-light.*`,
  `logo-dark.*`, `icon.*`, optional `icon-dark.*` / `font.*`) and are baked into
  the toolkit image at `/app/branding`.
- On deploy (after `provisioner`), `zitadel-brand` runs the toolkit's `brand`
  command: it uploads each present asset via the **Assets API**
  (`/assets/v1/instance/policy/label/{logo,logo/dark,icon,icon/dark,font}`) using
  the FirstInstance machine key, then **activates** the policy
  (`/admin/v1/policies/label/_activate`). Idempotent — re-runs simply re-upload.
- Toggle with `BRANDING_ENABLED` (default `true`). Swap the files (or bind-mount
  over `/app/branding`) to rebrand; colours come from `defaults.yaml`.

> **Manual fallback:** with `BRANDING_ENABLED=false`, upload the same assets once
> via **Console → Branding** (persists in the DB across redeploys), then *Activate*.

## Login v2 (the `login` service)

- Enabled on the instance via `ZITADEL_DEFAULTINSTANCE_FEATURES_LOGINV2_REQUIRED`
  + `ZITADEL_OIDC_DEFAULTLOGINURLV2` (set in the compose files).
- Served at **`/ui/v2/login`** (same domain via Traefik in prod, host port
  `IAM_LOGIN_PORT` in dev) by a **two-layer image**: the EP-Zitadel fork base
  (`LOGIN_BASE_IMAGE`/`LOGIN_BASE_VERSION` — per-IdP brand logos) + the CS-IAM
  branding overlay (`src/login` → `ghcr.io/bauer-group/cs-iam/login`,
  `LOGIN_IMAGE`/`LOGIN_VERSION`). See "Custom branding overlay" below.
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

## IdP provider button logos — real logos for generic providers

| Provider type | Button on the login |
|---------------|---------------------|
| **Native** (Microsoft/Entra, Google, GitHub, GitLab, Apple) | real brand logo (upstream) |
| **Generic** OAuth2/OIDC (Facebook, LINE, WeChat, KakaoTalk, X, TikTok, Naver, QQ, Weibo, VK, Zalo) | **real brand logo** (our fork) |
| Unknown / other generic | name-only fallback (unchanged) |

Upstream Login v2 renders generic OAuth2/OIDC providers as name-only buttons.
Our fork adds the real brand glyphs (matched by IdP display name via
`simple-icons`). LinkedIn is name-only — `simple-icons` removed that icon.

### The fork — `bauer-group/EP-Zitadel`

`apps/login` is a pnpm + nx monorepo app (`@zitadel/login` + `@zitadel/client`
+ `@zitadel/proto`, Next.js standalone, buf proto codegen). Building it needs
the full workspace, so we maintain a **fork of zitadel/zitadel**:

- `main` tracks upstream; `production` (default) = our customization
  (`apps/login/src/components/idps/sign-in-with-generic.tsx` + `simple-icons`).
- CI (`.github/workflows/cs-iam-login.yml`) builds `cs-iam-login.Dockerfile`
  (self-contained multi-stage) and publishes
  **`ghcr.io/bauer-group/ep-zitadel/zitadel-login`** (`4.15.1`/`stable`/`latest`).
  `production` is a rolling **"release tag + our one-file patch"** line (based on
  the `cs-iam-login.base-version` tag, not on upstream `main`), so its large
  ahead/behind count vs `main` is the tag↔main divergence — cosmetic, not drift.
- `feature/idp-brand-logos` holds the clean, upstream-PR-quality change (component
  + unit test, no infra), based on upstream **`main`** so a PR shows only our 4-file
  change — the candidate we can offer back to zitadel.
- `upstream-bump.yml` (daily + dispatch) is the **automatic maintenance**: it
  detects new zitadel releases, re-applies the branding on the new tag, **builds +
  publishes** the refreshed base image, and only then force-rolls `production` to
  it (build-as-gate — a release that breaks our patch fails the build and nothing
  is adopted), publishing `…/zitadel-login:latest` (+ the version tag).

CS-IAM **floats on `latest`** for both layers, like the sibling stacks: the core
wrapper (`src/zitadel`, `BASE_ZITADEL_VERSION=latest`) tracks `zitadel:latest`, and
the overlay (`src/login`, `LOGIN_BASE_VERSION=latest`) tracks
`ep-zitadel-login:latest`. The **base-image monitor** watches the digest of each
`latest` tag and triggers a `chore(deps)` rebuild when it moves — so when upstream
releases (core) or the EP bump publishes (login), CS-IAM rebuilds automatically.
Pin a fixed tag in `.env` only if you need a reproducible freeze.

Only the core `zitadel` image stays official (wrapped by `src/zitadel`); we do
not rebuild the Go core.

## Custom branding overlay (favicon / icons / backgrounds)

`src/login` is a thin image **`FROM` the EP-Zitadel base** that overlays static
assets onto the served `/app/public` tree → `ghcr.io/bauer-group/cs-iam/login`
(the image the `login` service actually runs). Drop assets into
`src/login/branding/public/<path>` to override the same-path upstream asset:

- `branding/public/favicon/…` — browser tab + app icons (**branded**: the
  BAUER GROUP square logo, generated at all sizes + `site.webmanifest`).
- `branding/public/images/login-background.jpg` — the login-page background
  (brand-black + subtle logo watermark), wired via `LOGIN_BACKGROUND_IMAGE` →
  `NEXT_PUBLIC_THEME_BACKGROUND_IMAGE`. Set `LOGIN_BACKGROUND_IMAGE=` (empty) for none.

The **main logo/icon/font are NOT here** — they're runtime `LabelPolicy` assets
uploaded automatically by `zitadel-brand` (see "Logo, icon & font" above), and
**colours** come from `defaults.yaml`. The overlay is only for instance-wide
**static** files (favicon, background) that are identical for every org.
No-rebuild alternative: bind-mount custom assets over `/app/public/...` at runtime.
See `src/login/branding/README.md`.

## Branding at a glance — which asset lives where

| Asset | Mechanism | Source in repo |
|-------|-----------|----------------|
| Colours (light/dark) | `LabelPolicy` in `defaults.yaml` (baked, applied at setup) | `config/zitadel/defaults.yaml` |
| Main logo (light/dark) + icon + font | Assets API, auto-uploaded by `zitadel-brand` | `src/directory-sync/branding/` |
| Favicon / tab + PWA icons | overlay (static, baked into `cs-iam/login`) | `src/login/branding/public/favicon/` |
| Login-page background | overlay + `LOGIN_BACKGROUND_IMAGE` | `src/login/branding/public/images/` |
| Per-IdP provider button logos | the EP-Zitadel fork (app code) | `bauer-group/EP-Zitadel` |
