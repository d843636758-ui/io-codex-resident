FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/data/home \
    CODEX_HOME=/data/codex

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      git curl ca-certificates build-essential libssl-dev libffi-dev \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g @openai/codex@0.142.4 \
 && git clone --depth 1 --branch main \
      https://github.com/teleport-computer/feedling-mcp.git \
      /app/feedling-mcp \
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
