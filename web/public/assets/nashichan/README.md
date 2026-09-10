# Nashichan dashboard assets

The Hermes dashboard uses one approved-artwork sprite sheet at runtime:

- `nashichan-sprite.webp`

The sheet is a 4x4 grid containing the fourteen approved states in this order:

```text
idle       greeting   listening   thinking
working    approval   success     celebrate
warning    error      offline     security
update     sleep      (empty)     (empty)
```

`web/src/lib/nashichan/assets.ts` owns the state-to-cell mapping. Keeping the artwork in one binary makes the state set atomic and avoids fourteen independent browser requests.

The source/archival artwork may still be kept as individual PNG files outside the application bundle. The runtime sprite was assembled only from the approved images; no character redraw is involved.

The character UI is fail-safe: if the sprite cannot be loaded, the mascot image hides itself and Chat continues to work.
