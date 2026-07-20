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

if [ ! -s "$CODEX_HOME/auth.json" ]; then
  echo "Codex 尚未登录，现在启动 ChatGPT 设备授权。"
  echo "请在日志中找到登录网址和设备代码。"
  codex login --device-auth
fi

echo "正在检查 Codex 登录状态..."
codex login status

echo "登录成功，正在启动 Feedling resident consumer。"
exec python -u tools/chat_resident_consumer.py
