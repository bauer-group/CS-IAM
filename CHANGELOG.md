## [0.17.3](https://github.com/bauer-group/CS-IAM/compare/v0.17.2...v0.17.3) (2026-07-10)

## [0.17.2](https://github.com/bauer-group/CS-IAM/compare/v0.17.1...v0.17.2) (2026-07-09)

## [0.17.1](https://github.com/bauer-group/CS-IAM/compare/v0.17.0...v0.17.1) (2026-07-08)

## [0.17.0](https://github.com/bauer-group/CS-IAM/compare/v0.16.0...v0.17.0) (2026-07-07)

### 🚀 Features

* **backup:** migrated database-backup to the central BackupHelper engine ([9415b7d](https://github.com/bauer-group/CS-IAM/commit/9415b7db4b396871d3825af5ce91f9f7a2ecd888))

## [0.16.0](https://github.com/bauer-group/CS-IAM/compare/v0.15.3...v0.16.0) (2026-07-05)

### 🚀 Features

* **backup:** enabled webhook HMAC signing for alert notifications ([817b050](https://github.com/bauer-group/CS-IAM/commit/817b050199ff9a5a151463811e52b7dfd3278c65))

## [0.15.3](https://github.com/bauer-group/CS-IAM/compare/v0.15.2...v0.15.3) (2026-07-05)

### 🐛 Bug Fixes

* **login:** corrected OCI image license label to AGPL-3.0-only ([2c963fc](https://github.com/bauer-group/CS-IAM/commit/2c963fc54ade0da8f041004ffe7f0b2152ecbcce))

## [0.15.2](https://github.com/bauer-group/CS-IAM/compare/v0.15.1...v0.15.2) (2026-06-23)

## [0.15.1](https://github.com/bauer-group/CS-IAM/compare/v0.15.0...v0.15.1) (2026-06-22)

## [0.15.0](https://github.com/bauer-group/CS-IAM/compare/v0.14.2...v0.15.0) (2026-06-18)

### 🚀 Features

* **login:** added internal_login_org_scope for promptless Entra ([eabca6a](https://github.com/bauer-group/CS-IAM/commit/eabca6af3d4e4ccd6f4e378e8531b03a9f2b3cc4))

## [0.14.2](https://github.com/bauer-group/CS-IAM/compare/v0.14.1...v0.14.2) (2026-06-18)

### 🐛 Bug Fixes

* **zitadel:** dropped org-domain DNS challenge, set stack domains ([dc95659](https://github.com/bauer-group/CS-IAM/commit/dc9565976ace624a67113551e4efb46ea3de16ea))

## [0.14.1](https://github.com/bauer-group/CS-IAM/compare/v0.14.0...v0.14.1) (2026-06-18)

### 🐛 Bug Fixes

* **provisioning:** wired internal_org_domains for domain discovery ([42b91ec](https://github.com/bauer-group/CS-IAM/commit/42b91ec75b84f5aeba857045d5e52ff83e548302))

## [0.14.0](https://github.com/bauer-group/CS-IAM/compare/v0.13.3...v0.14.0) (2026-06-18)

### 🚀 Features

* **login:** linked external IdPs into a customer login policy ([a0d7ca3](https://github.com/bauer-group/CS-IAM/commit/a0d7ca3b025ea599f4160d664a9ed07d6a4f9446))

## [0.13.3](https://github.com/bauer-group/CS-IAM/compare/v0.13.2...v0.13.3) (2026-06-18)

## [0.13.2](https://github.com/bauer-group/CS-IAM/compare/v0.13.1...v0.13.2) (2026-06-17)

## [0.13.1](https://github.com/bauer-group/CS-IAM/compare/v0.13.0...v0.13.1) (2026-06-16)

## [0.13.0](https://github.com/bauer-group/CS-IAM/compare/v0.12.5...v0.13.0) (2026-06-13)

### 🚀 Features

* **iam:** break-glass admin org + thinned login overlay ([f75c1ea](https://github.com/bauer-group/CS-IAM/commit/f75c1eaa16ef4ed84c6b2ab64c2f5435ed9aa063))
* **iam:** defaulted workforce Entra auto-redirect to on ([5fa5efb](https://github.com/bauer-group/CS-IAM/commit/5fa5efbcbba6567a1fb17a9ba70a3a9f28f5aebc))
* **iam:** email-UPN loginnames, system-wide config, demo in external tenant ([31cd7ec](https://github.com/bauer-group/CS-IAM/commit/31cd7ece615710abdd383990be4663d5015d76e2))
* **iam:** wired gated Entra-only workforce auto-redirect ([f467186](https://github.com/bauer-group/CS-IAM/commit/f467186b9ca9bd0ef11c69e60b5846758878cc19))

### 🐛 Bug Fixes

* **login:** centred the language/theme switcher (was right-shifted) ([a1322a4](https://github.com/bauer-group/CS-IAM/commit/a1322a4f39f2425ed37fcaf08d62ec01875df861))
* **login:** fixed fresh-boot branding (base pin, ordering, race) ([1a2d942](https://github.com/bauer-group/CS-IAM/commit/1a2d942d2d95ca414efaaabd8e7545ab5a640ea1))

### ♻️ Refactoring

* **compose:** dropped dead background-image env from prod variants ([9622cc7](https://github.com/bauer-group/CS-IAM/commit/9622cc74ce97c2485ed1be3cec2206bf3b5fcb76))
* **login:** runtime favicon, dropped background + dead overlay ([7793f5f](https://github.com/bauer-group/CS-IAM/commit/7793f5f324ca5f156e1a10e976973cacb346c202))

## [0.12.5](https://github.com/bauer-group/CS-IAM/compare/v0.12.4...v0.12.5) (2026-06-13)

## [0.12.4](https://github.com/bauer-group/CS-IAM/compare/v0.12.3...v0.12.4) (2026-06-12)

### 🐛 Bug Fixes

* **config:** updated privacy and help links in defaults.yaml ([cc282cb](https://github.com/bauer-group/CS-IAM/commit/cc282cb0031bee04069f62048d0d894a32954d9e))
* **login:** enabled MFA login via login-client SA + WebAuthn-valid domain ([35ea7fa](https://github.com/bauer-group/CS-IAM/commit/35ea7fa674164b94f07963cf12ece0536d89d29b))
* **login:** fixed console mixed-content (tlsMode external) + TOTP issuer ([dcbdea4](https://github.com/bauer-group/CS-IAM/commit/dcbdea4bb214e1bcc810387f0a9120956036b752))
* **login:** fixed Login v2 dev HTTPS origin and prod routing ([46432b2](https://github.com/bauer-group/CS-IAM/commit/46432b2662e18b9b3bd35ab8143ffcfdfb4ceed7))

## [0.12.3](https://github.com/bauer-group/CS-IAM/compare/v0.12.2...v0.12.3) (2026-06-11)

### ♻️ Refactoring

* moved oidc-test-client from src/ to tests/ ([20ef68b](https://github.com/bauer-group/CS-IAM/commit/20ef68bbd477070706e2ae95e17bd07f531908e5))

## [0.12.2](https://github.com/bauer-group/CS-IAM/compare/v0.12.1...v0.12.2) (2026-06-11)

### 🐛 Bug Fixes

* **provisioner:** marked client_id outputs non-sensitive (apply was failing) ([6d36adf](https://github.com/bauer-group/CS-IAM/commit/6d36adf0d7173b1bd083b185b5fc6ce6cd8bef20))

## [0.12.1](https://github.com/bauer-group/CS-IAM/compare/v0.12.0...v0.12.1) (2026-06-11)

## [0.12.0](https://github.com/bauer-group/CS-IAM/compare/v0.11.0...v0.12.0) (2026-06-11)

### 🚀 Features

* **test:** added an in-stack OIDC test client to validate the demo user ([7431a5f](https://github.com/bauer-group/CS-IAM/commit/7431a5f481349319833ac55f4feb2afd590e6b09))

## [0.11.0](https://github.com/bauer-group/CS-IAM/compare/v0.10.1...v0.11.0) (2026-06-10)

### 🚀 Features

* **apps:** isolated the demo into its own pDemo project (roles + app + user + grant) ([708fd92](https://github.com/bauer-group/CS-IAM/commit/708fd921669478513a09c72d613f45f5bfa5bc66))

## [0.10.1](https://github.com/bauer-group/CS-IAM/compare/v0.10.0...v0.10.1) (2026-06-10)

## [0.10.0](https://github.com/bauer-group/CS-IAM/compare/v0.9.0...v0.10.0) (2026-06-10)

### 🚀 Features

* **apps:** made the demo OIDC app fully loginable (user + grant) ([4086c0e](https://github.com/bauer-group/CS-IAM/commit/4086c0e95450012aadb7a3856944d99cea831ea1))

## [0.9.0](https://github.com/bauer-group/CS-IAM/compare/v0.8.0...v0.9.0) (2026-06-09)

### 🚀 Features

* **login:** automated logo/icon/font branding + login background ([d1d1c73](https://github.com/bauer-group/CS-IAM/commit/d1d1c73da5d9cee5fb1d1b2d490e4c7afaeddd72))

## [0.8.0](https://github.com/bauer-group/CS-IAM/compare/v0.7.3...v0.8.0) (2026-06-09)

### 🚀 Features

* **login:** added the BAUER GROUP favicon set to the login overlay ([d29d007](https://github.com/bauer-group/CS-IAM/commit/d29d007116dc6b78e99490b906dc644f9ee22587))

## [0.7.3](https://github.com/bauer-group/CS-IAM/compare/v0.7.2...v0.7.3) (2026-06-09)

### ♻️ Refactoring

* **idp:** renamed Google IdP vars to the EXTERNAL_ prefix ([b965368](https://github.com/bauer-group/CS-IAM/commit/b9653688d1699a68fe675601182bc8003b1cc0f7))

## [0.7.2](https://github.com/bauer-group/CS-IAM/compare/v0.7.1...v0.7.2) (2026-06-09)

### 🐛 Bug Fixes

* **login:** floated the overlay base default to latest ([a8d8784](https://github.com/bauer-group/CS-IAM/commit/a8d878488b5a513186c9384c2942848a3bee76cc)), closes [#12144](https://github.com/bauer-group/CS-IAM/issues/12144)

## [0.7.1](https://github.com/bauer-group/CS-IAM/compare/v0.7.0...v0.7.1) (2026-06-09)

### 🐛 Bug Fixes

* **login:** floated base images on latest to track upstream fixes ([6a446a8](https://github.com/bauer-group/CS-IAM/commit/6a446a8f336966e6102e1cb77cbb5a03859dad4e)), closes [#12144](https://github.com/bauer-group/CS-IAM/issues/12144)

## [0.7.0](https://github.com/bauer-group/CS-IAM/compare/v0.6.0...v0.7.0) (2026-06-09)

### 🚀 Features

* **login:** added a branding overlay image atop the EP-Zitadel base ([18868c1](https://github.com/bauer-group/CS-IAM/commit/18868c12cbcd79b6d786a8971caf0f0da2c7fa21))

## [0.6.0](https://github.com/bauer-group/CS-IAM/compare/v0.5.1...v0.6.0) (2026-06-09)

### 🚀 Features

* **login:** switched login image to the EP-Zitadel branded fork ([1bf2c5c](https://github.com/bauer-group/CS-IAM/commit/1bf2c5cc069b94555034814f63c69c134b9cb3d7))

## [0.5.1](https://github.com/bauer-group/CS-IAM/compare/v0.5.0...v0.5.1) (2026-06-08)

## [0.5.0](https://github.com/bauer-group/CS-IAM/compare/v0.4.1...v0.5.0) (2026-06-07)

### 🚀 Features

* **login:** added Login v2 hosted UI (official image, branded) ([7070456](https://github.com/bauer-group/CS-IAM/commit/70704564400c2e12a02c28b38c2ce10f728319c4))

## [0.4.1](https://github.com/bauer-group/CS-IAM/compare/v0.4.0...v0.4.1) (2026-06-07)

### 🐛 Bug Fixes

* **branding:** corrected login/console colours to the brand palette ([112d244](https://github.com/bauer-group/CS-IAM/commit/112d2441c1aee446de59080962b488b374aef212)), closes [#1f4e79](https://github.com/bauer-group/CS-IAM/issues/1f4e79) [#FF8500](https://github.com/bauer-group/CS-IAM/issues/FF8500) [#FB923](https://github.com/bauer-group/CS-IAM/issues/FB923) [#231F1](https://github.com/bauer-group/CS-IAM/issues/231F1) [#F9F8F6](https://github.com/bauer-group/CS-IAM/issues/F9F8F6) [#EF4444](https://github.com/bauer-group/CS-IAM/issues/EF4444)

## [0.4.0](https://github.com/bauer-group/CS-IAM/compare/v0.3.0...v0.4.0) (2026-06-07)

### 🚀 Features

* **iam:** added per-org identity-provider federation ([3b01360](https://github.com/bauer-group/CS-IAM/commit/3b013607037210786de05b1bf269d13bced28f64))

## [0.3.0](https://github.com/bauer-group/CS-IAM/compare/v0.2.0...v0.3.0) (2026-06-07)

### 🚀 Features

* **iam:** added External Users org and customer app-access model ([19bbbec](https://github.com/bauer-group/CS-IAM/commit/19bbbec35a55f10f62391f2e202251a34be5bb9a))

## [0.2.0](https://github.com/bauer-group/CS-IAM/compare/v0.1.3...v0.2.0) (2026-06-07)

### 🚀 Features

* **stack:** baked Zitadel config in the image, moved key under /data ([2ca6b22](https://github.com/bauer-group/CS-IAM/commit/2ca6b22f77a34fc46b9f3fefbae94836055aa4ea))

## [0.1.3](https://github.com/bauer-group/CS-IAM/compare/v0.1.2...v0.1.3) (2026-06-07)

### 🐛 Bug Fixes

* **compose:** used a scalar user override instead of group_add ([af56165](https://github.com/bauer-group/CS-IAM/commit/af56165fbe6fab9eeaf40c534067e6e3442117cd))
* **security:** locked down the machine-key volume permissions ([f6c5952](https://github.com/bauer-group/CS-IAM/commit/f6c59524ff41f03139512f7134ced63b7411328b))

## [0.1.2](https://github.com/bauer-group/CS-IAM/compare/v0.1.1...v0.1.2) (2026-06-07)

### 🐛 Bug Fixes

* **compose:** fixed the dev bootstrap (machine-key perms + resolvable issuer) ([6a81146](https://github.com/bauer-group/CS-IAM/commit/6a811465d8b773ec721c29fbfcb811ae94747aaf))

## [0.1.1](https://github.com/bauer-group/CS-IAM/compare/v0.1.0...v0.1.1) (2026-06-07)

### 🐛 Bug Fixes

* **ci:** fixed the four Docker image builds ([f068719](https://github.com/bauer-group/CS-IAM/commit/f068719a57534b7e1919538205e28ce2fc3eceba))

## [0.1.0](https://github.com/bauer-group/CS-IAM/compare/v0.0.0...v0.1.0) (2026-06-07)

### 🚀 Features

* **iam:** added Zitadel OIDC/IAM stack with Entra federation ([af83007](https://github.com/bauer-group/CS-IAM/commit/af8300704738a7c2b042f91f0c8e9316d7d983de))

### 🐛 Bug Fixes

* **iam:** aligned stack to BAUER GROUP conventions and fixed CI ([38031c0](https://github.com/bauer-group/CS-IAM/commit/38031c0af8e998ec9d6b550aaba8300364fc32bc))
