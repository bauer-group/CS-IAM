#!/usr/bin/env bash
# =============================================================================
# CS-IAM backup round trip - prepare
# =============================================================================
# Fills the .env with the stack's own generator, because the secrets have
# formats a generic generator does not know: ZITADEL_MASTERKEY must be exactly
# 32 characters, the admin and demo passwords must satisfy Zitadel's password
# complexity policy. At this point the module has just copied .env.example to
# .env, so regenerating it with --force loses nothing.
#
# The generator prints a preview of every secret it writes. Its output is
# dropped: the module masks the new values only after this script has run, and
# the CI log of this public repository must not show any part of them.
# =============================================================================
set -euo pipefail

python3 scripts/generate-env.py --force > /dev/null
# --force keeps the replaced file as .env.bak - a template copy, not needed.
rm -f .env.bak

echo "generated .env from .env.example"
