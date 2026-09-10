# Nashichan dashboard assets

This directory is the runtime asset location for the Hermes dashboard mascot.

Expected files:

- `idle.png`
- `greeting.png`
- `listening.png`
- `thinking.png`
- `working.png`
- `approval.png`
- `success.png`
- `celebrate.png`
- `warning.png`
- `error.png`
- `offline.png`
- `security.png`
- `update.png`
- `sleep.png`

The approved asset pack produced for this feature already uses the same filenames under `assets/nashichan/`, so extracting that directory into `web/public/` is sufficient.

The character UI is deliberately fail-safe: a missing/broken image hides the mascot image and must never break chat.

The source artwork is maintained separately from application logic so approved character art can be replaced without touching the state machine.
