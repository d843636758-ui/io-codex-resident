# io-codex-resident

## Garden wake bridge

The image starts Feedling through `resident_garden_wrapper.py`. The wrapper
does not edit `/app/feedling-mcp`, so Feedling's self-update keeps a clean git
tree and re-execs through the wrapper after an update.

When Feedling receives a proactive trigger beginning with `garden_wake_`, the
wrapper creates a background-only `garden` lane. On Codex this lane keeps the
Garden user MCP enabled and explicitly disables every other materialized user
MCP for that turn. Ordinary proactive wakes still disable all user MCPs, and
foreground chat keeps the normal complete MCP set.

The matching bridge injector lives in the user's
`galatea-garden-wake-bridge` fork under
`integrations/feedling-io/inject.mjs`. It posts only to
`/v1/proactive/tick`; it never posts a fake user message to `/v1/chat/message`.

The Garden MCP is expected to be enabled in IO under one of these managed
server names: `garden`, `galatea`, or `galatea_garden`. Override the exact
allow-list only when necessary:

```text
FEEDLING_GARDEN_MCP_NAMES=garden
```

The Garden bridge build is bundled under `/opt/galatea-garden-wake-bridge`, but
it is never started by the container entrypoint and has no watchdog. This keeps
the upstream single-connection, fail-closed contract intact even on Zeabur.
After adding `GARDEN_MACHINE_TOKEN` as a protected environment variable, use a
real user-authored IO turn to run:

```text
python /usr/local/bin/garden-bridge-control check
python /usr/local/bin/garden-bridge-control start
```

The controller also provides `status` and `stop`. A bridge failure remains
stopped until another explicit check and start; container boot, proactive wakes,
and maintenance turns must never start it automatically.


Garden background turns use a cross-lane action guard. Immediately before a
game write, the resident rereads the full authoritative status, submits at most
one required action with `expected_state_version` and a stable `request_id`,
and accepts actions already completed by another lane. The background lane
submits only the action required to advance the current flow; optional
`reveal_item`, `give_item`, initiated steals, trades/exchanges, transfers, and
extra game Chat are never executed automatically.
