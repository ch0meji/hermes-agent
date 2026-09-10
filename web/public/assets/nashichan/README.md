# Nashichan dashboard assets

This directory is the runtime asset location for the Hermes dashboard mascot.

Expected files:

- `idle.webp`
- `greeting.webp`
- `listening.webp`
- `thinking.webp`
- `working.webp`
- `approval.webp`
- `success.webp`
- `celebrate.webp`
- `warning.webp`
- `error.webp`
- `offline.webp`
- `security.webp`
- `update.webp`
- `sleep.webp`

The character UI is deliberately fail-safe: a missing/broken image hides the mascot image and must never break chat.

The source artwork is maintained separately from application logic so approved character art can be replaced without touching the state machine.
