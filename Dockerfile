FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/data/home \
    CODEX_HOME=/data/codex \
    FEEDLING_AUTO_UPDATE=0

# Start from the exact consumer release advertised by the current Feedling
# backend. Auto-update is temporarily disabled because this image carries a
# compatibility patch for Codex 0.142 multi-message output. Re-enable it once
# the same fix ships upstream, otherwise checkout would overwrite the patch.
ARG FEEDLING_COMMIT=be8beab497a220ec9797c51997f2607f8c166a3a

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git curl ca-certificates build-essential libssl-dev libffi-dev \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g @openai/codex@0.142.4 \
 && mkdir -p /app/feedling-mcp \
 && git init /app/feedling-mcp \
 && git -C /app/feedling-mcp remote add origin \
      https://github.com/teleport-computer/feedling-mcp.git \
 && git -C /app/feedling-mcp fetch --depth 1 origin "$FEEDLING_COMMIT" \
 && git -C /app/feedling-mcp checkout --detach FETCH_HEAD \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/feedling-mcp

COPY patch_feedling_codex_reply.py /usr/local/bin/patch-feedling-codex-reply

RUN python /usr/local/bin/patch-feedling-codex-reply \
      tools/chat_resident_consumer.py \
 && python -m pip install --no-cache-dir \
      -r tools/chat_resident_requirements.txt

COPY start.sh /usr/local/bin/start-resident
COPY oauth_callback_relay.py /usr/local/bin/oauth-callback-relay
COPY repair_codex_config.py /usr/local/bin/repair-codex-config

RUN chmod 755 \
      /usr/local/bin/start-resident \
      /usr/local/bin/oauth-callback-relay \
      /usr/local/bin/repair-codex-config \
      /usr/local/bin/patch-feedling-codex-reply

CMD ["/usr/local/bin/start-resident"]
