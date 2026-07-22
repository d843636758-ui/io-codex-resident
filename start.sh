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

echo "正在启动 Feedling resident consumer。"

python -u tools/chat_resident_consumer.py &
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
