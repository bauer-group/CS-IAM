# Login branding overlay

Drop deployment-specific static assets here. Everything under
`branding/public/` is copied onto the login image's served `/app/public` tree
(`COPY branding/public/ /app/public/`), so a file at the same path **replaces**
the upstream asset. Empty by default = passthrough (the base image's assets).

## What goes where

| Drop here | Overrides / purpose |
|-----------|---------------------|
| `branding/public/favicon/favicon.ico` + the PNG set | Browser tab + app icons (`favicon-16/32`, `apple-touch-icon`, `android-chrome-*`, `mstile-*`, `site.webmanifest`) |
| `branding/public/favicon.ico` | Root favicon |
| `branding/public/images/<name>.{jpg,png,svg}` | Background images — reference via `NEXT_PUBLIC_THEME_BACKGROUND_IMAGE=/images/<name>.jpg` in `.env` |
| `branding/public/zitadel-logo-light.svg` / `zitadel-logo-dark.svg` | Decorative logos bundled in the base (not the main login logo) |

## The main login logo + colors are NOT set here

- **Logo** (the big one on the login card) comes from Zitadel's **LabelPolicy**
  (`Console → Branding`, or the Assets API) at **runtime** — upload light/dark
  logos there; no rebuild needed.
- **Colors** come from the instance `LabelPolicy` (`config/zitadel/defaults.yaml`).
- **Layout/roundness/spacing/appearance** come from `LOGIN_THEME_*` env.

So this overlay is specifically for **favicon, app icons, and background/static
images** — the assets that aren't runtime-configurable.

## Alternative (no rebuild): runtime volume mount

Instead of baking, you can mount custom assets over the path at runtime:

```yaml
login:
  volumes:
    - ./my-branding/favicon:/app/public/favicon:ro
```

The baked overlay (this dir) is the reproducible, image-pinned option.
