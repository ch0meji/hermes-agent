# Nashichan dashboard assets

The Hermes dashboard uses fourteen independent approved-artwork WebP files at runtime, one for each Nashichan state:

```text
idle.webp
greeting.webp
listening.webp
thinking.webp
working.webp
approval.webp
success.webp
celebrate.webp
warning.webp
error.webp
offline.webp
security.webp
update.webp
sleep.webp
```

`web/src/lib/nashichan/assets.ts` owns the state-to-file mapping. A sprite sheet is intentionally not used: an invalid or missing file must affect only that state, not every Nashichan state.

The runtime artwork comes from the approved character images without redesigning Nashichan. Character identity stays separate from Hermes; server/AI context belongs in the surrounding dashboard UI.

The character UI is fail-safe: if an asset cannot be loaded, that mascot image hides itself and Chat continues to work.
