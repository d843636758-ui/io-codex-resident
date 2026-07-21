#!/bin/sh
set -eu

mkdir -p \
  "$HOME" \
  "$CODEX_HOME" \
  /data/feedling \
  /data/workspace \
  /data/images

chmod 700 "$CODEX_HOME"

CONFIG_FILE="$CODEX_HOME/config.toml"

if [ ! -f "$CONFIG_FILE" ]; then
  cat > "$CONFIG_FILE" <<'EOF'
cli_auth_credentials_store = "file"
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

if ! codex mcp get ob >/dev/null 2>&1; then
  echo "正在添加 Ombre Brain MCP。"
  codex mcp add ob --url "$OB_MCP_URL"
fi

if [ ! -f "$OB_OAUTH_MARKER" ]; then
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
  cleanup_relay
  trap - EXIT INT TERM
fi

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
