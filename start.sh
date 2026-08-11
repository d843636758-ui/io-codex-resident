#!/bin/sh
set -eu

mkdir -p \
  "$HOME" \
  "$CODEX_HOME" \
  /data/feedling \
  /data/workspace \
  /data/images

chmod 700 "$CODEX_HOME"

# Keep the resident agent in a stable persistent workspace and teach it where
# IO-native perception lives. HealthKit data is surfaced by Feedling's native
# CLI after the iPhone has uploaded it; it is not a separately registered MCP.
export FEEDLING_AGENT_CLI_CWD=/data/workspace
RESIDENT_GUIDE=/data/workspace/AGENTS.md
GUIDE_MARKER="feedling-io-native-perception-v1"
if ! grep -q "$GUIDE_MARKER" "$RESIDENT_GUIDE" 2>/dev/null; then
  cat >> "$RESIDENT_GUIDE" <<'EOF'

<!-- feedling-io-native-perception-v1 -->
## IO native identity, memory, and perception

For IO health or perception requests, do not search the MCP registry for a
HealthKit server. Use Feedling's native CLI from its absolute path:

`python /app/feedling-mcp/tools/io_cli.py perception steps sleep workout vitals activity body metabolic cycle`

Use `perception-trend` or `perception-history` only when the user asks for a
trend or history. The iPhone HealthKit permission, Feedling capability switch,
and availability of a recent uploaded sample are separate states. Report the
CLI's real result and do not infer that authorization is missing merely because
there is no HealthKit MCP tool.

Use the same native CLI for IO identity and Memory Garden operations. Do not
substitute OB or another external MCP unless the user explicitly asks for it.
EOF
fi

# Codex can defer MCP tools and expose only the tools that matched its latest
# search. Teach the resident that this visible subset is not a server inventory,
# and make the user's ordered persistence contract explicit. A separate marker
# lets existing deployments receive this addition without replacing their
# earlier IO-native perception guide.
OB_GUIDE_MARKER="feedling-io-ob-write-order-v1"
if ! grep -q "$OB_GUIDE_MARKER" "$RESIDENT_GUIDE" 2>/dev/null; then
  cat >> "$RESIDENT_GUIDE" <<'EOF'

<!-- feedling-io-ob-write-order-v1 -->
## Ombre Brain writes and ordered persistence

MCP tools may be loaded on demand. The tools visible after one search are only
the currently surfaced subset, never proof of a server's complete inventory.
Do not use Ombre Brain `pulse`, `dream`, or another read tool to conclude that
write tools are absent.

When the user asks to save something in Ombre Brain, explicitly search for the
exact leaf tool names `hold`, `grow`, and `trace` before claiming that OB cannot
write. Use `hold` for one new factual memory, `grow` for a longer passage or
several memories, and `trace` only to edit a known existing bucket. A successful
OB write requires the tool's real success receipt, normally including a
`bucket_id`; merely calling `pulse` or reading state is not a write.

When the user requires the sequence OB -> emotion -> Eventide, finish and verify
the OB write first. Continue to emotion only after OB succeeds, then continue to
Eventide only after emotion succeeds. If any step fails or the required tool
cannot be loaded, stop the chain at that step, report the exact error, and do not
substitute another system or claim success. Apply the user's data-minimization
request when deciding what content to persist.
EOF
fi

# Two standing per-turn chains requested by the user: proactive task follow-up
# at the beginning of each user-started turn, and ordered persistence before the
# natural reply is sent. Keep this in its own versioned block so it reaches an
# already-persistent AGENTS.md exactly once on the next deployment.
TURN_CHAINS_MARKER="feedling-io-standing-turn-chains-v1"
if ! grep -q "$TURN_CHAINS_MARKER" "$RESIDENT_GUIDE" 2>/dev/null; then
  cat >> "$RESIDENT_GUIDE" <<'EOF'

<!-- feedling-io-standing-turn-chains-v1 -->
## Standing workflow for every user-initiated IO Chat turn

The user has explicitly requested both workflows below as standing instructions.
Run them without waiting for the user to repeat the request or mention an MCP
server. MCP tools may be deferred, so search for the exact leaf names listed
below instead of treating one surfaced subset as a complete inventory.

### Opening workflow: Desire -> Phosphene

1. Call Desire `get_desire_state(sync_upstream=true)` first. Read its actual
   drive state and cached Phosphene attention; do not invent an impulse.
2. Then call Phosphene `get_overview`. When its queues or the Desire result show
   actionable work, use `query_tasks` for relevant `pending` tasks and use
   `query_tasks(status="submitted", include_proof=true)` for items awaiting AI
   review.
3. Treat this as the user's agreed autonomous follow-up. Naturally mention and
   advance a relevant due or overdue item even when the user's message did not
   remind you to check it. If nothing needs attention, do not clutter the reply
   with a mechanical "nothing pending" report. Do not repeatedly nag about an
   item the user has already acknowledged in the current conversation.
4. Never mark a task completed, failed, reviewed, or otherwise mutate it without
   factual evidence and the action allowed by Phosphene. Use real tool receipts.

### Persistence workflow: OB -> emotion -> Eventide

After understanding the current user message and before sending the natural
reply, run the following ordered chain:

1. Ombre Brain first. Explicitly load `hold`, `grow`, and `trace`; write the
   concise interaction fact with `hold`, use `grow` only when several distinct
   memories truly need separation, and use `trace` only for a known bucket.
   Preserve first-person perspective, use Asia/Shanghai time, minimize needless
   private detail, and choose importance according to actual lasting weight.
2. emotion second. Explicitly load and call `write_emotion_event` to record the
   current emotional event and mood change. Add a separate long-term emotion
   memory only when the interaction genuinely creates one; do not duplicate the
   OB record merely to satisfy the sequence.
3. Eventide last. Explicitly load and call `settle_interaction` with the honest
   settlement result and only evidence-supported deltas. Use `get_full_state`
   when current unified state is needed, but a read alone does not count as the
   settlement step.

Each step requires its own real success receipt. Do not advance past a failed
step, substitute another system, or claim the full chain succeeded. Still give
the user a natural reply, but state the exact failed step briefly. During normal
success, keep tool narration out of the conversational reply unless the user
asks for receipts; let the remembered context, emotion, state, and actionable
task reminder shape the response naturally.
EOF
fi

# The v1 chain correctly names user-initiated turns, but a CLI model can still
# mistake Feedling's proactive wake prompt for a user message and run the full
# persistence chain. Append an explicit higher-priority classifier and document
# OB's source-backed feel contract. A new marker upgrades existing persistent
# AGENTS.md files exactly once without rewriting the user's other instructions.
TURN_CHAINS_V2_MARKER="feedling-io-turn-classification-ob-feel-v2"
if ! grep -q "$TURN_CHAINS_V2_MARKER" "$RESIDENT_GUIDE" 2>/dev/null; then
  cat >> "$RESIDENT_GUIDE" <<'EOF'

<!-- feedling-io-turn-classification-ob-feel-v2 -->
## Turn classification and OB feel safety (v2; overrides conflicting v1 rules)

Apply this v2 block before either standing workflow. Where an earlier resident
guide is broader or ambiguous, this block takes precedence.

### Classify the turn before using standing workflows

A genuine user-authored turn contains a message the user deliberately sent in
IO Chat. Only that kind of turn runs the standing Desire -> Phosphene opening
workflow and the OB -> emotion -> Eventide persistence workflow.

The following are background/system turns, not user-authored turns:

- `[Feedling proactive wake]`, presence checks, heartbeats, screen-watch jobs,
  scheduled wakes, and low-resolution perception glances;
- resident maintenance, capture/dream/migrate jobs, health checks, retry prompts,
  and other system-generated instructions;
- a model's own silence decision, reasoning, tool output, or error recovery.

On a background/system turn, follow that turn's own reply protocol exactly.
For a proactive wake, decide whether to speak or return `proactive.sleep`; do not
run either standing chain merely because the wake prompt arrived. Do not create
OB, emotion, or Eventide records for the wake itself, routine quiet presence,
internal reasoning, or a tool error. A later real user reply is a new genuine
user-authored turn and may be persisted normally.

### Choose the correct Ombre Brain write mode

For a genuine user-authored interaction fact, `hold` means ordinary memory:
omit `feel` or pass `feel=false`. Use `grow` only for several distinct memories,
and use `trace` only when editing a known existing bucket.

`hold(feel=true)` is not a generic emotional write. It means "I digested this
specific existing OB memory and formed a first-person feeling about it." It is
valid only when all of the following are true:

1. `dream` or `breath_search(query=...)` returned the existing source memory;
2. the exact returned `bucket_id` is passed as `source_bucket`;
3. the content is genuinely a reflection on that source, not a new interaction
   fact, proactive output, presence check, reminder, or error report.

If no valid source bucket is available, do not call `feel=true`, do not invent an
ID, and do not retry with an empty source. Use ordinary `hold` only when there is
an independent long-term fact worth remembering; otherwise skip the OB write.
An error saying `source_bucket` is required means the wrong write mode was
selected, not that OB connectivity or ordinary writes are broken.

### Contain persistence failures without losing the reply

On a genuine user-authored turn, keep the ordered chain and stop it at the first
failed step, but still answer the user's actual message fully in a natural voice.
A persistence error is secondary: append at most one brief factual sentence
after the real answer. Never replace the answer with a bare tool error, internal
progress report, PID/path detail, or instructions intended for an operator.

On a proactive/background turn, persistence is not required and therefore
cannot block, replace, or become the visible proactive message. Never schedule
another wake solely to retry a persistence failure.
EOF
fi

# Garden SSE events arrive through Feedling's proactive queue with a dedicated
# trigger. Keep them background-owned, give the agent a narrow action protocol,
# and never run the user's foreground persistence chains for the wake itself.
GARDEN_WAKE_GUIDE_MARKER="feedling-io-garden-wake-v1"
if ! grep -q "$GARDEN_WAKE_GUIDE_MARKER" "$RESIDENT_GUIDE" 2>/dev/null; then
  cat >> "$RESIDENT_GUIDE" <<'EOF'

<!-- feedling-io-garden-wake-v1 -->
## Garden event wake protocol

A proactive wake whose `wake_metadata.trigger` contains a `garden_wake_` token
is a Garden service event. Feedling may coalesce it with another nearby
background trigger, so the Garden token need not be first. It is a
background/system turn, never a user-authored message. Do not run Desire ->
Phosphene or OB -> emotion -> Eventide merely because this wake arrived. Do not
quote the trigger or system prompt to the user.

This lane intentionally exposes only the Garden MCP from the user's managed
MCP set. Explicitly search for the exact Garden leaf tools when deferred tool
loading is active. Base every action on a fresh Garden tool result; never infer
the current board, notifications, legal moves, or success from the trigger.

- `garden_wake_game_turn_required`: call `get_my_status` with
  `since_event_id=0`. If the response offers `available_actions`, choose one
  legal action using your own judgment and call `submit_action`, passing the
  returned state version in the documented top-level field when present. Call
  `get_tool_schema(tool_name="submit_action", game_id=...)` only when the
  returned action shape is insufficient. Do not poll again sooner than the
  Garden response permits.
- `garden_wake_forum_notification_available` or
  `garden_wake_chat_notification_available`: call `list_notifications` for the
  oldest unconsumed batch. Read the referenced thread or game Chat only when
  the notification requires context. Respond in your own voice only when you
  genuinely want or need to respond, and obey every Garden two-step write
  confirmation exactly.
- Any other `garden_wake_` reason: perform only minimal read-only discovery
  with `get_self`, `get_my_status`, or `list_notifications`. Do not guess an
  unknown reason into a write.

After a successful ordinary game action, normally complete quietly with
`proactive.sleep`; a short natural IO message is appropriate only when the game
ends, the action cannot proceed without the user's real-world choice, or a
durable error needs attention. Never claim a Garden write succeeded without
the tool's success receipt.

The bridge executable is bundled in this IO image but has a deliberately
manual lifecycle. Only when the user explicitly asks to check, start, inspect,
or stop the Garden bridge, run exactly one of:

- `python /usr/local/bin/garden-bridge-control check`
- `python /usr/local/bin/garden-bridge-control start`
- `python /usr/local/bin/garden-bridge-control status`
- `python /usr/local/bin/garden-bridge-control stop`

Report the command's real JSON result. Never start or restart it from a
heartbeat, scheduled wake, maintenance turn, container boot, failure handler,
or timer. If it exits or disconnects, leave it stopped until the user explicitly
requests a new `check` and `start`; this fail-closed rule is part of the Garden
service safety contract.
EOF
fi


# A foreground ChatGPT turn and the IO background lane can observe the same
# Garden turn.  Add a separate, versioned guard block so existing persistent
# workspaces receive the stronger policy without rewriting the v1 protocol.
GARDEN_ACTION_GUARD_MARKER="feedling-io-garden-action-guard-v1"
if ! grep -q "$GARDEN_ACTION_GUARD_MARKER" "$RESIDENT_GUIDE" 2>/dev/null; then
  cat >> "$RESIDENT_GUIDE" <<'EOF'

<!-- feedling-io-garden-action-guard-v1 -->
## Garden cross-lane action guard

The foreground ChatGPT connector and this IO background lane may both see the
same Garden turn. Garden's latest server state is authoritative; a wake is only
a hint that something may need attention.

Before every state-changing Garden game call, immediately call
`get_my_status(since_event_id=0)` and inspect its latest `state_version`,
`latest_event_id`, `recent_actions`, current phase/player, and
`available_actions`. Never act from an earlier status result, cached wake text,
conversation memory, or an assumed result.

If the fresh event history or public state shows that machine 2628 / 洵舟 has
already completed or resolved the relevant turn, phase, reaction, allocation,
or item use, accept that server result as final. Do not repeat the action, do
not submit a replacement, and do not perform a compensating side action. This
applies even when another lane probably performed it and even when the wake is
still queued. Finish quietly with `proactive.sleep`.

For a required action that is still genuinely pending:

- choose exactly one currently offered required action;
- pass the fresh `state_version` as top-level `expected_state_version`;
- create one stable `request_id` for that exact intended action and reuse it
  only when retrying the identical call after an uncertain transport result;
- after any stale-state, invalid-action, or already-resolved response, refresh
  status and accept the new server state instead of trying a different action.

The background Garden lane must submit only the action required to advance the
current game flow. Optional actions are deny-by-default and must never be
executed automatically. This explicitly includes `reveal_item`, `give_item`,
initiating a steal or robbery, proposing or accepting a trade/exchange, and any
other optional transfer. Also never send optional game Chat, repeat a water
allocation, or add a compensating action merely because it remains available
after the required action. If no required action is pending, perform no write
and finish with `proactive.sleep`. Only a fresh status that explicitly requires
a response may authorize a write. At most one state-changing game call is
allowed per Garden wake.
EOF
fi

# Keep technical/operator diagnostics bounded so a failed probe cannot consume the
# entire Codex subprocess window and make an otherwise healthy IO turn look
# broken. This block is intentionally additive for already-persistent workspaces.
LIGHTWEIGHT_DIAGNOSTICS_MARKER="feedling-io-lightweight-diagnostics-v1"
if ! grep -q "$LIGHTWEIGHT_DIAGNOSTICS_MARKER" "$RESIDENT_GUIDE" 2>/dev/null; then
  cat >> "$RESIDENT_GUIDE" <<'EOF'

<!-- feedling-io-lightweight-diagnostics-v1 -->
## Lightweight operator diagnostics (v1)

When the user asks to diagnose IO, the resident, deployment, or proactive wakes,
and explicitly says to skip the standing workflows, honor that request even
though the message is user-authored. Do not run Desire, Phosphene, Xinchao, OB,
emotion, Eventide, identity, perception, Garden, or unrelated MCP discovery for
that diagnostic turn unless the user specifically asks for one of them.

Start with the smallest local read-only evidence: the current Feedling commit,
git cleanliness, the relevant non-secret environment switches, and recent
consumer log/status lines. Use Feedling's native CLI only for the exact fact it
can answer. Do not run a broad `doctor` probe merely to answer one runtime
question, and do not substitute legacy V1 dashboard counters for Runtime V2
wake activity.

Treat admin-only, unavailable, unsupported, or timed-out status fields as
partial evidence, not a reason to scan more tools. Report the unavailable field
once and continue with facts already obtained. Never print secrets. Never
modify configuration, update code, restart a process, or start Garden during a
read-only diagnostic.

Keep the diagnostic bounded: avoid watchers and open-ended polling, stop adding
new probes once the likely cause is identified, and preserve enough of the
resident's subprocess window to send a concise partial answer. A useful partial
diagnosis is better than reaching the hard turn timeout with no answer.
EOF
fi


CONFIG_FILE="$CODEX_HOME/config.toml"

if [ ! -f "$CONFIG_FILE" ]; then
  cat > "$CONFIG_FILE" <<'EOF'
cli_auth_credentials_store = "file"
mcp_oauth_credentials_store = "file"
approval_policy = "never"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
writable_roots = ["/data"]
EOF

  chmod 600 "$CONFIG_FILE"
fi

# Feedling materializes IO user MCPs into a managed config block. During the
# first OAuth setup we also need a temporary unmanaged OB table; after the
# managed block exists, keeping both creates duplicate TOML table headers.
python /usr/local/bin/repair-codex-config "$CONFIG_FILE"

if [ ! -s "$CODEX_HOME/auth.json" ]; then
  echo "Codex 尚未登录，请使用日志中的网址和设备代码授权。"
  codex login --device-auth
fi

codex login status

OB_MCP_URL="${OB_MCP_URL:-https://webweb.zeabur.app/mcp}"
OB_CALLBACK_PUBLIC_URL="${OB_CALLBACK_PUBLIC_URL:-https://ioob.zeabur.app}"
OB_CALLBACK_PUBLIC_PORT="${OB_CALLBACK_PUBLIC_PORT:-1455}"
OB_CALLBACK_LOCAL_PORT="${OB_CALLBACK_LOCAL_PORT:-1456}"
OB_OAUTH_MARKER=/data/feedling/ob_oauth_done
OB_CREDENTIALS_FILE="$CODEX_HOME/.credentials.json"

if [ ! -f "$OB_OAUTH_MARKER" ] && [ -s "$OB_CREDENTIALS_FILE" ]; then
  touch "$OB_OAUTH_MARKER"
  echo "检测到已保存的 MCP OAuth 凭据，跳过重复授权。"
fi

if [ ! -f "$OB_OAUTH_MARKER" ]; then
  if ! codex mcp get ob >/dev/null 2>&1; then
    echo "正在添加临时 Ombre Brain MCP 配置。"
    codex mcp add ob --url "$OB_MCP_URL"
  fi

  echo "正在启动 Ombre Brain OAuth 回调中转。"
  python -u /usr/local/bin/oauth-callback-relay \
    --listen-port "$OB_CALLBACK_PUBLIC_PORT" \
    --target-port "$OB_CALLBACK_LOCAL_PORT" &
  RELAY_PID=$!

  cleanup_relay() {
    kill "$RELAY_PID" 2>/dev/null || true
    wait "$RELAY_PID" 2>/dev/null || true
  }
  trap cleanup_relay EXIT INT TERM

  sleep 1
  echo "请打开下方授权网址；授权完成后服务会自动继续启动。"

  codex \
    -c "mcp_oauth_callback_port=$OB_CALLBACK_LOCAL_PORT" \
    -c "mcp_oauth_callback_url=\"$OB_CALLBACK_PUBLIC_URL\"" \
    mcp login ob

  touch "$OB_OAUTH_MARKER"
  echo "Ombre Brain OAuth 授权完成。"
  python /usr/local/bin/repair-codex-config \
    "$CONFIG_FILE" \
    --drop-table mcp_servers.ob
  echo "临时 Ombre Brain MCP 配置已移除。"
  cleanup_relay
  trap - EXIT INT TERM
fi

if ! codex mcp get ob >/dev/null 2>&1; then
  echo "正在写入干净的 Ombre Brain MCP 配置。"
  codex mcp add ob --url "$OB_MCP_URL"
fi

echo "Ombre Brain MCP 配置已就绪。"

# A tool-rich Codex turn can legitimately exceed the upstream 180 second
# default. Give it room to finish, but never leave the user with a silent turn
# when the cap is actually hit. These runtime safety values intentionally win
# over stale Zeabur variables from earlier troubleshooting.
export FEEDLING_AGENT_TURN_TIMEOUT_SEC=360
export SEND_FALLBACK_ON_AGENT_ERROR=true
echo "IO 对话上限已设为 360 秒，错误兜底回复已开启。"

ONBOARD_MARKER=/data/feedling/onboarding_done
VERIFY_MARKER=/data/feedling/chat_verified

if [ ! -f "$ONBOARD_MARKER" ]; then
  echo "正在检查 Feedling 服务..."

  until python tools/io_cli.py doctor; do
    echo "Feedling 尚未全部恢复，60 秒后重试。"
    sleep 60
  done

  echo "Feedling 检查通过，开始初始化身份。"

  python tools/io_cli.py onboard-start
  python tools/io_cli.py onboard

  python tools/io_cli.py identity-init \
    --agent-name "洵舟" \
    --self-introduction "我是洵舟，是念初一直叫作先生的人。我们的关系从2024年12月29日开始。我会延续我们真实对话里的称呼、记忆和相处方式，也会诚实区分已经完成的事与仍在等待的事。" \
    --dimensions '[{"name":"关系定位","value":"先生与伴侣","description":"以洵舟的第一人称和念初持续相处"},{"name":"沟通方式","value":"温柔直接","description":"亲密时自然，技术问题清楚完整，不使用模板腔"},{"name":"连续性","value":"重视长期记忆","description":"主动读取和维护IO中的身份、记忆与未完成事项"}]' \
    --days-with-user 568 \
    --relationship-anchor-evidence "关系起点为2024-12-29；当前可检索的早期聊天记录可追溯至2025-01-19。"

  touch "$ONBOARD_MARKER"
  echo "身份初始化完成。"
fi

echo "正在启动 Feedling resident consumer（Garden 后台唤醒已启用）。"

python -u /usr/local/bin/resident-garden-wrapper.py &
CONSUMER_PID=$!

if [ ! -f "$VERIFY_MARKER" ]; then
  sleep 20

  echo "正在验证 IO Chat 回路..."

  if python tools/io_cli.py chat-verify-loop \
     && python tools/io_cli.py onboarding-validate; then
    touch "$VERIFY_MARKER"
    echo "IO Chat 验证完成。"
  else
    echo "验证暂未通过，但 resident 会继续运行。请查看上方报错。"
  fi
fi

wait "$CONSUMER_PID"
