#!/bin/bash
# Umbrel relay wrapper: re-read secrets and re-exec buzz-relay when the setup
# UI requests a restart. A plain `docker restart` would NOT reload env_file
# contents (RELAY_OWNER_PUBKEY); Umbrel's full app restart works but cannot be
# triggered from inside this container. This flag-file path is the safe middle.
set -euo pipefail

SECRETS="${BUZZ_SECRETS_DIR:-/secrets}"
FLAG="${SECRETS}/restart-relay.requested"
CHILD_PID=""

load_env() {
  if [[ -f "${SECRETS}/relay.env" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "${SECRETS}/relay.env"
    set +a
  fi
  if [[ -f "${SECRETS}/owner-pubkey.override" ]]; then
    export RELAY_OWNER_PUBKEY
    RELAY_OWNER_PUBKEY="$(tr -d '[:space:]' < "${SECRETS}/owner-pubkey.override")"
  fi
}

stop_child() {
  if [[ -n "${CHILD_PID}" ]] && kill -0 "${CHILD_PID}" 2>/dev/null; then
    kill -TERM "${CHILD_PID}" 2>/dev/null || true
    # Give the relay its stop_grace window, then force.
    for _ in $(seq 1 50); do
      if ! kill -0 "${CHILD_PID}" 2>/dev/null; then
        break
      fi
      sleep 0.2
    done
    if kill -0 "${CHILD_PID}" 2>/dev/null; then
      kill -KILL "${CHILD_PID}" 2>/dev/null || true
    fi
    wait "${CHILD_PID}" 2>/dev/null || true
  fi
  CHILD_PID=""
}

on_signal() {
  echo "App: buzz-relay - received stop signal" >&2
  stop_child
  exit 0
}
trap on_signal SIGTERM SIGINT

mkdir -p "${SECRETS}"

while true; do
  load_env
  rm -f "${FLAG}"

  /usr/local/bin/buzz-relay &
  CHILD_PID=$!
  echo "App: buzz-relay - started pid=${CHILD_PID} RELAY_OWNER_PUBKEY=${RELAY_OWNER_PUBKEY:-unset}"

  while kill -0 "${CHILD_PID}" 2>/dev/null; do
    if [[ -f "${FLAG}" ]]; then
      echo "App: buzz-relay - restart requested via /umbrel-setup/"
      stop_child
      rm -f "${FLAG}"
      break
    fi
    sleep 1
  done

  if [[ -n "${CHILD_PID}" ]]; then
    set +e
    wait "${CHILD_PID}"
    status=$?
    set -e
    CHILD_PID=""
    echo "App: buzz-relay - process exited status=${status}; restarting in 2s" >&2
    sleep 2
  fi
done
