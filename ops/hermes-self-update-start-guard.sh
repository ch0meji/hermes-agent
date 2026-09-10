#!/usr/bin/env bash
set -u

# Host-side recovery guard for updating the Hermes Docker container from Hermes itself.
# Launch this detached on the Docker host before the current `hermes` container is
# stopped/removed. It waits for the exact replacement image and starts it if the
# updater loses its SSH/Gateway session when the old container disappears.

EXPECTED_IMAGE="${1:-}"
CONTAINER_NAME="${2:-hermes}"
TIMEOUT_SECONDS="${HERMES_START_GUARD_TIMEOUT:-180}"
POLL_SECONDS="${HERMES_START_GUARD_POLL_SECONDS:-2}"
HEALTH_TIMEOUT_SECONDS="${HERMES_START_GUARD_HEALTH_TIMEOUT:-90}"

log() {
  printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*"
}

if [[ ! "$EXPECTED_IMAGE" =~ ^ghcr\.io/ch0meji/hermes-agent:sha-[0-9a-f]{40}$ ]]; then
  log "refusing invalid expected image: $EXPECTED_IMAGE"
  exit 64
fi

if [[ ! "$CONTAINER_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]]; then
  log "refusing invalid container name: $CONTAINER_NAME"
  exit 64
fi

if ! [[ "$TIMEOUT_SECONDS" =~ ^[0-9]+$ && "$POLL_SECONDS" =~ ^[0-9]+$ && "$HEALTH_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]]; then
  log "timeout values must be non-negative integers"
  exit 64
fi

if (( POLL_SECONDS < 1 )); then
  POLL_SECONDS=1
fi

log "guard armed container=$CONTAINER_NAME expected_image=$EXPECTED_IMAGE"
deadline=$((SECONDS + TIMEOUT_SECONDS))

while (( SECONDS <= deadline )); do
  image="$(docker inspect --format '{{.Config.Image}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  status="$(docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || true)"

  if [[ "$image" == "$EXPECTED_IMAGE" ]]; then
    case "$status" in
      running)
        log "replacement already running"
        break
        ;;
      created|exited)
        log "starting replacement state=$status"
        if ! docker start "$CONTAINER_NAME" >/dev/null; then
          log "docker start failed"
          exit 1
        fi
        break
        ;;
      dead|removing)
        log "waiting for usable replacement state=$status"
        ;;
      *)
        log "waiting for replacement state=${status:-missing}"
        ;;
    esac
  fi

  sleep "$POLL_SECONDS"
done

image="$(docker inspect --format '{{.Config.Image}}' "$CONTAINER_NAME" 2>/dev/null || true)"
status="$(docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || true)"
if [[ "$image" != "$EXPECTED_IMAGE" || "$status" != "running" ]]; then
  log "timed out without running expected replacement image=$image state=$status"
  exit 124
fi

health_deadline=$((SECONDS + HEALTH_TIMEOUT_SECONDS))
while (( SECONDS <= health_deadline )); do
  status="$(docker inspect --format '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null || true)"
  health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$CONTAINER_NAME" 2>/dev/null || true)"

  if [[ "$status" != "running" ]]; then
    log "replacement stopped during verification state=$status health=$health"
    exit 1
  fi
  if [[ "$health" == "healthy" || "$health" == "none" ]]; then
    restarts="$(docker inspect --format '{{.RestartCount}}' "$CONTAINER_NAME" 2>/dev/null || true)"
    log "replacement ready state=$status health=$health restarts=${restarts:-unknown}"
    exit 0
  fi
  if [[ "$health" == "unhealthy" ]]; then
    log "replacement unhealthy"
    exit 1
  fi
  sleep "$POLL_SECONDS"
done

log "replacement remained non-ready through health timeout"
exit 1
