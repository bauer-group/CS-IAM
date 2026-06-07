#!/usr/bin/env bash
# =============================================================================
# zitadel-provision — guarded OpenTofu apply (true IaC, non-destructive)
# =============================================================================
# 1. Wait for the FirstInstance machine key + Zitadel readiness.
# 2. tofu init.
# 3. tofu plan -detailed-exitcode.
#      exit 0 → no changes        → done.
#      exit 1 → plan error        → fail.
#      exit 2 → changes pending    → inspect.
# 4. If the plan contains ANY destroy/replace → ABORT + alert (never run an
#    unattended destroy; this protects resources made in the Zitadel UI that
#    are not in the Terraform config). Otherwise apply the additive plan.
# =============================================================================
set -euo pipefail

WORKDIR="/workspace/terraform"
PLAN="/tmp/plan.tfplan"
KEY_FILE="${ZITADEL_JWT_PROFILE_FILE:-/machinekey/iam-admin.json}"
WAIT_TIMEOUT="${ZITADEL_WAIT_TIMEOUT:-180}"

log() { printf '%s [provision] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
fail() { log "ERROR: $*"; exit 1; }

# ── Resolve the readiness URL (same host as the issuer) ──────────────────────
scheme="https"
[ "${ZITADEL_INSECURE:-false}" = "true" ] && scheme="http"
domain="${ZITADEL_DOMAIN:?ZITADEL_DOMAIN is required}"
port="${ZITADEL_PORT:-443}"
ready_url="${scheme}://${domain}:${port}/.well-known/openid-configuration"

# ── 1. Wait for the machine key ──────────────────────────────────────────────
log "waiting for machine key at ${KEY_FILE} ..."
elapsed=0
until [ -s "${KEY_FILE}" ]; do
  [ "${elapsed}" -ge "${WAIT_TIMEOUT}" ] && fail "machine key not present after ${WAIT_TIMEOUT}s"
  sleep 3
  elapsed=$((elapsed + 3))
done
log "machine key present."

# ── 2. Wait for Zitadel readiness ────────────────────────────────────────────
log "waiting for Zitadel at ${ready_url} ..."
elapsed=0
until curl -fsS -o /dev/null --max-time 5 "${ready_url}"; do
  [ "${elapsed}" -ge "${WAIT_TIMEOUT}" ] && fail "Zitadel not ready after ${WAIT_TIMEOUT}s (${ready_url})"
  sleep 5
  elapsed=$((elapsed + 5))
done
log "Zitadel is ready."

cd "${WORKDIR}"

# ── 3. init + plan ───────────────────────────────────────────────────────────
log "tofu init ..."
tofu init -input=false -no-color

log "tofu plan ..."
set +e
tofu plan -input=false -no-color -detailed-exitcode -out="${PLAN}"
plan_rc=$?
set -e

case "${plan_rc}" in
  0)
    log "no changes — infrastructure is up to date."
    exit 0
    ;;
  1)
    fail "tofu plan failed."
    ;;
  2)
    log "changes detected — checking for destructive actions ..."
    ;;
  *)
    fail "unexpected tofu plan exit code: ${plan_rc}"
    ;;
esac

# ── 4. Non-destructive guard ─────────────────────────────────────────────────
# Any action containing "delete" (delete or replace) is destructive.
destructive=$(tofu show -json "${PLAN}" \
  | jq '[.resource_changes[]?.change.actions[]?] | index("delete") != null')

if [ "${destructive}" = "true" ]; then
  log "ABORT: the plan contains destroy/replace actions. Refusing to run an"
  log "       unattended destructive apply. Resources created in the UI that"
  log "       are not in Terraform are NEVER touched — but a config/state drift"
  log "       wants to delete a managed resource. Review and apply manually:"
  log "         cd terraform && tofu plan && tofu apply"
  tofu show -no-color "${PLAN}" || true
  exit 1
fi

# ── Apply additive / in-place changes ────────────────────────────────────────
log "applying additive changes ..."
tofu apply -input=false -no-color -auto-approve "${PLAN}"
log "provisioning complete."
