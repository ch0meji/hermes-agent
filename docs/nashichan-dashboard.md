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

The dashboard ships fourteen independent WebP assets, one per visual state:

```text
web/public/assets/nashichan/
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

`web/src/lib/nashichan/assets.ts` owns the state-to-asset mapping. The dashboard intentionally does not use a sprite sheet: keeping states independent limits a malformed or missing image to that state instead of making the entire mascot unavailable.

Artwork remains decoupled from behavior. Missing or broken artwork is non-fatal: the affected image hides itself rather than affecting Chat. The approved character artwork must remain visually faithful to Nashichan; AI/server identity belongs in surrounding UI rather than redesigning the character.

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

1. All fourteen state images load from `/assets/nashichan/<state>.webp`.
2. Chat remains usable when one Nashichan image is absent or malformed.
3. The mascot does not intercept mouse/touch input.
4. Desktop and narrow/mobile layouts do not cover critical controls.
5. Tool events switch to `working`; model activity switches to `thinking`.
6. Completion briefly shows `success` then returns to `idle`.
7. Approval/security events map to their dedicated states.
8. Event-feed or sidecar failures show `offline` without breaking the PTY chat.

### CI startup failures

A failed orchestrator run with no dispatched jobs (`jobs: []`) is a workflow startup/infrastructure failure, not evidence that frontend checks failed. In that case, retrigger the PR workflow and confirm that the `JS & TS checks` lane actually starts before diagnosing Nashichan code. Do not weaken or edit repository-wide CI merely to bypass a zero-job startup failure.
