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

echo "Waiting for Codex ChatGPT login and START_RESIDENT marker..."

while [ ! -s "$CODEX_HOME/auth.json" ] || [ ! -f /data/START_RESIDENT ]; do
  sleep 10
done

echo "Codex login and start marker found. Starting Feedling resident consumer."

exec python -u tools/chat_resident_consumer.py
