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
