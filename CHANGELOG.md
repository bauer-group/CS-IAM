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
