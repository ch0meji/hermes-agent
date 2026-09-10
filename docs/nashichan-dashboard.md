# Nashichan on the Hermes dashboard

Nashichan is a presentation-only operator mascot for the dashboard Chat page.

Core concept:

> BitcoinとMonacoin・AI・自宅サーバーをまたいで動く、やさしい案内役兼オペレーター。

## Runtime model

Hermes remains the source of truth. Nashichan listens to the existing structured-event stream used by `ChatSidebar` and maps those events to a visual state. The mascot never changes task/session state.

The integration deliberately reuses the existing `/api/events?channel=...` WebSocket instead of opening another activity subscription.

## States

| State | Typical trigger | Default line |
| --- | --- | --- |
| `idle` | No mapped activity | いつでもどうぞだよ |
| `greeting` | New dashboard session | よろしくね！ |
| `listening` | Reserved for explicit input/listening UI | 聞いてるよ！ |
| `thinking` | Model/reasoning/message stream | 確認してるよ |
| `working` | Tool/preview/terminal execution | いま処理中だよ |
| `approval` | Clarification/setup/approval request | これで実行していい？ |
| `success` | Message completed | 終わったよ |
| `celebrate` | Reaction / notable success | やったー！すごいよ！ |
| `warning` | Warning notification | 確認してほしいところがあるよ |
| `error` | Error notification | ここでエラーが出たよ |
| `offline` | Dashboard sidecar/feed connection failure | 接続が切れてるみたい… |
| `security` | Credential/sudo/secret request | セキュリティを確認中だよ |
| `update` | Reserved for update lifecycle events | アップデート中だよ |
| `sleep` | Reserved for explicit rest/suspended state | 少しおやすみ… |

`greeting`, `success`, and `celebrate` are transient presentation states and automatically return to `idle`.

## Artwork

The dashboard ships one runtime sprite assembled from the approved individual images:

```text
web/public/assets/nashichan/nashichan-sprite.webp
```

The 4x4 grid layout is:

```text
idle       greeting   listening   thinking
working    approval   success     celebrate
warning    error      offline     security
update     sleep      (empty)     (empty)
```

The source/archival pack can remain as fourteen individual PNGs. The runtime sprite is only a packaging optimization: it was assembled from those approved assets without redrawing the character. `web/src/lib/nashichan/assets.ts` owns the state-to-cell mapping.

Artwork remains decoupled from behavior. Missing or broken artwork is non-fatal: the image component hides itself rather than affecting Chat.

## UI behavior

The mascot is rendered through a React portal so the mobile sidebar transform does not trap its fixed positioning. It uses `pointer-events: none` and a lower z-index than modal/sheet layers, so the character cannot block dashboard controls.

The desktop position leaves room for the structured-events sidebar. Mobile uses a smaller character and hides the speech bubble on very small screens.

## Validation

Before merge, run the workspace checks and production build:

```bash
npm run check -w web
npm run build -w web
```

Also verify manually:

1. Chat remains usable when the Nashichan sprite is absent.
2. The mascot does not intercept mouse/touch input.
3. Desktop and narrow/mobile layouts do not cover critical controls.
4. Tool events switch to `working`; model activity switches to `thinking`.
5. Completion briefly shows `success` then returns to `idle`.
6. Event-feed or sidecar failures show `offline` without breaking the PTY chat.
