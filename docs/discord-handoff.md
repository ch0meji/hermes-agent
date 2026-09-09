# Discord Ops handoff bridge

Hermes can receive bounded Ops requests from the Hatsugarasu Codex controller through a dedicated
Discord channel. The bridge reuses the normal Hermes agent execution and Discord reply path; it does
not add a supervisor, queue, or persistent task database.

Configure both values in the Discord platform `extra` config, or provide the matching environment
variables:

```yaml
discord:
  extra:
    handoff_channel_id: "<dedicated-channel-snowflake>"
    hatsugarasu_bot_user_id: "1545456768430121022"
```

```text
DISCORD_HANDOFF_CHANNEL_ID=<dedicated-channel-snowflake>
HATSUGARASU_BOT_USER_ID=1545456768430121022
```

The adapter accepts a message only when it is in the configured channel (or a thread under it), is
authored by the configured Hatsugarasu bot ID, and contains all of `type: ops_handoff`,
`handoff_id`, `from: codex`, `to: hermes`, and a non-empty request. Humans, Hermes itself, unknown
bots, invalid payloads, and valid payloads in other channels are rejected. Existing normal-channel
bot behavior remains controlled by `DISCORD_ALLOW_BOTS`; that setting never enables the handoff route.

Hermes keeps message-ID and handoff-ID dedupe state in memory. The execution prompt includes the
original handoff ID and the reply is posted to the same channel or thread as:

```text
🍆 → 🐦 Ops result

type: ops_result
handoff_id: H-20260909-001
from: hermes
to: codex

result:
- status: success
- uptime: ...
```

Result text is secret-redacted and bounded before delivery. Restarting Hermes clears bridge dedupe
state, as intended for the initial implementation.
