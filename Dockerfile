FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/data/home \
    CODEX_HOME=/data/codex \
    FEEDLING_AUTO_UPDATE=1

# Start from the current stable Feedling release. The resident's built-in
# updater remains enabled so later backend-advertised compatible releases can
# be adopted without rebuilding this image.
ARG FEEDLING_COMMIT=2c7f7c0765aa351118b786b8a9c2220361223bc7
ARG GARDEN_BRIDGE_COMMIT=5ef71b0bb6f853fec490ce643a68f5b4e06d118d

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
 && mkdir -p /opt/galatea-garden-wake-bridge \
 && git init /opt/galatea-garden-wake-bridge \
 && git -C /opt/galatea-garden-wake-bridge remote add origin \
      https://github.com/d843636758-ui/galatea-garden-wake-bridge.git \
 && git -C /opt/galatea-garden-wake-bridge fetch --depth 1 origin "$GARDEN_BRIDGE_COMMIT" \
 && git -C /opt/galatea-garden-wake-bridge checkout --detach FETCH_HEAD \
 && npm --prefix /opt/galatea-garden-wake-bridge ci \
 && npm --prefix /opt/galatea-garden-wake-bridge run build \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app/feedling-mcp

RUN python -m pip install --no-cache-dir \
      -r tools/chat_resident_requirements.txt

COPY start.sh /usr/local/bin/start-resident
COPY oauth_callback_relay.py /usr/local/bin/oauth-callback-relay
COPY repair_codex_config.py /usr/local/bin/repair-codex-config
COPY resident_garden_wrapper.py /usr/local/bin/resident-garden-wrapper.py
COPY garden_bridge_control.py /usr/local/bin/garden-bridge-control

RUN chmod 755 \
      /usr/local/bin/start-resident \
      /usr/local/bin/oauth-callback-relay \
      /usr/local/bin/repair-codex-config \
      /usr/local/bin/resident-garden-wrapper.py \
      /usr/local/bin/garden-bridge-control

CMD ["/usr/local/bin/start-resident"]
