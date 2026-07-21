FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/data/home \
    CODEX_HOME=/data/codex \
    FEEDLING_AUTO_UPDATE=1

# Start from the exact consumer release advertised by the current Feedling
# backend. The resident's built-in updater remains enabled and can move forward
# automatically when a later compatible release is advertised.
ARG FEEDLING_COMMIT=feef5e44612bdeed3150b5cb06f900f7e558adbc

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

RUN python -m pip install --no-cache-dir \
      -r tools/chat_resident_requirements.txt

COPY start.sh /usr/local/bin/start-resident
COPY oauth_callback_relay.py /usr/local/bin/oauth-callback-relay
COPY repair_codex_config.py /usr/local/bin/repair-codex-config

RUN chmod 755 \
      /usr/local/bin/start-resident \
      /usr/local/bin/oauth-callback-relay \
      /usr/local/bin/repair-codex-config

CMD ["/usr/local/bin/start-resident"]
