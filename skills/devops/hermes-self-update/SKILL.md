---
name: hermes-self-update
description: Safely update the Hermes production Docker container from Hermes itself without leaving the replacement container stopped when the current Gateway disappears.
version: 1.0.0
author: COCOROTUS
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [hermes, docker, self-update, recovery]
    category: devops
environments:
  - terminal
---

# Hermes Self-Update

Use this procedure when the user asks Hermes/Nashi to update the production `hermes` Docker container on `hermes-prod` to a new `ghcr.io/ch0meji/hermes-agent:sha-<40-hex>` image.

The current Hermes Gateway runs inside the very container being replaced. A normal SSH-driven sequence can therefore stop its own caller after `docker create` and before `docker start`. The host-side start guard below exists specifically to bridge that lifecycle gap.

## Scope

This skill applies only to:

- Docker host: `hermes-prod`
- container: `hermes`
- image family: `ghcr.io/ch0meji/hermes-agent:sha-<40-hex>`

Do not use it for `hermes-nanomon-tunnel-1`, `hermes-nanomon-1`, `hermes-webui`, or unrelated containers.

## Before changing anything

1. Resolve the exact target image SHA/tag.
2. Inspect the current `hermes` container.
3. If it is already running the exact target image and is healthy with `RestartCount=0`, report success and stop. Do not restart or recreate it.
4. Verify the target image is available before stopping the current container.
5. Preserve the existing production settings, especially:
   - `/opt/hermes-data -> /opt/data`
   - network `hermes_default`
   - restart policy `unless-stopped`
   - existing environment

Never delete `/opt/data`, Docker volumes, or run `docker prune`. Do not change Tailscale or firewall settings as part of this update.

## Arm the host-side recovery guard

Before any command that can stop/remove the current `hermes` container, launch the guard as a detached process on the Docker host using the same authorized SSH/host execution path already being used for the deployment.

Expected host path:

```text
/opt/hermes-data/bin/hermes-self-update-start-guard
```

Launch pattern:

```bash
nohup /opt/hermes-data/bin/hermes-self-update-start-guard \
  'ghcr.io/ch0meji/hermes-agent:sha-<40-hex>' hermes \
  >/tmp/hermes-self-update-start-guard.log 2>&1 </dev/null &
```

The detached host process must be started successfully before stopping the current container. Do not run the guard inside the `hermes` container: it must live in the host process tree so it survives the Gateway/container shutdown.

## Perform the update

After the guard is armed, perform the existing production update procedure. Keep the replacement container configuration equivalent to the current production container. The guard is only a recovery mechanism for the final start; it does not authorize broader configuration changes.

It waits for a container named `hermes` whose `.Config.Image` exactly equals the requested target image. It will not start an old or unexpected image. If that replacement appears in `created` or `exited`, it starts it. If the replacement is already running, it only verifies it.

Because the originating Gateway may disappear during replacement, do not treat the transient disconnect itself as update failure.

## After reconnect

Verify:

```text
image = exact requested SHA tag
status = running
health = healthy
RestartCount = 0
```

Also confirm the Discord Gateway reconnects and that there is no fatal startup error. Then report the final result briefly.

If the original request is replayed after restart, first check whether the target image is already running and healthy. If so, report success without starting another deployment. This prevents a self-update loop.

If recovery did not complete, inspect:

```text
/tmp/hermes-self-update-start-guard.log
```

Do not recursively retry container replacement. Report the concrete blocked/failure state instead.
