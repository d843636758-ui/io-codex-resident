#!/usr/bin/env python3
"""Start Feedling's resident consumer with narrow background MCP lanes.

The wrapper patches functions in memory only. It never edits the Feedling git
checkout, so the resident's normal self-update can keep the working tree clean.
When Feedling re-execs after an update, ``sys.argv`` still points to this wrapper
and the patches are installed again against the newly imported consumer.
"""

from __future__ import annotations

import functools
import inspect
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Any


TOOLS_DIR = Path("/app/feedling-mcp/tools")
GARDEN_LANE = "garden"
PRESENCE_LANE = "presence"
GARDEN_TRIGGER_RE = re.compile(
    r"(?m)^- trigger: [^\n]*\bgarden_wake_[a-z0-9_.:-]+"
)
PRESENCE_WAKE_RE = re.compile(r"(?m)^\[Feedling proactive wake\]\s*$")


def _bounded_float_env(name: str, default: float, minimum: float) -> float:
    try:
        return max(minimum, float(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


HTTP_TIMEOUT_SEC = _bounded_float_env(
    "FEEDLING_HTTP_TIMEOUT_SEC", 35.0, 10.0
)
HTTP_KEEPALIVE_EXPIRY_SEC = _bounded_float_env(
    "FEEDLING_HTTP_KEEPALIVE_EXPIRY_SEC", 15.0, 1.0
)


def _resident_http_client(resident, *, verify: bool = True):
    """Build a pool that retires idle edge connections before they go stale.

    Feedling's upstream consumer intentionally shares one Client for its API
    traffic.  On the IO deployment there are two extra reverse-proxy hops; an
    idle TLS socket can therefore be closed before upstream's 60-second pool
    expiry and surface as UNEXPECTED_EOF on the next poll.  Keep the shared
    client, but retire idle sockets sooner and leave enough read time for the
    resident's bounded long polls.
    """
    httpx_module = resident.httpx
    return httpx_module.Client(
        timeout=httpx_module.Timeout(
            HTTP_TIMEOUT_SEC,
            connect=min(10.0, HTTP_TIMEOUT_SEC),
            pool=min(10.0, HTTP_TIMEOUT_SEC),
        ),
        verify=verify,
        limits=httpx_module.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=HTTP_KEEPALIVE_EXPIRY_SEC,
        ),
    )


class _RecyclingHttpClient:
    """Rebuild stale edge pools and replay read-only requests promptly.

    A failed long poll used to escape to Feedling's outer loop, whose capped
    exponential backoff then left IO unreachable for roughly a minute at a
    time.  Read-only requests are safe to replay. Mutating requests are never
    replayed because the server may have committed them before disconnecting;
    their pool is still recycled so the following attempt starts cleanly.
    """

    _SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

    def __init__(self, resident, *, verify: bool = True):
        self._resident = resident
        self._verify = verify
        self._lock = threading.RLock()
        self._client = _resident_http_client(resident, verify=verify)

    def _replace(self, failed_client: Any) -> None:
        with self._lock:
            if self._client is failed_client:
                self._client = _resident_http_client(
                    self._resident, verify=self._verify
                )
        _close_quietly(failed_client)

    def request(self, method: str, url: Any, *args: Any, **kwargs: Any):
        method_upper = str(method).upper()
        max_attempts = 3 if method_upper in self._SAFE_METHODS else 1
        for attempt in range(max_attempts):
            with self._lock:
                client = self._client
            try:
                return client.request(method, url, *args, **kwargs)
            except self._resident.httpx.TransportError:
                self._replace(client)
                if attempt + 1 >= max_attempts:
                    raise
                time.sleep(0.25 * (attempt + 1))
        raise RuntimeError("unreachable transport retry state")

    def get(self, url: Any, *args: Any, **kwargs: Any):
        return self.request("GET", url, *args, **kwargs)

    def head(self, url: Any, *args: Any, **kwargs: Any):
        return self.request("HEAD", url, *args, **kwargs)

    def options(self, url: Any, *args: Any, **kwargs: Any):
        return self.request("OPTIONS", url, *args, **kwargs)

    def post(self, url: Any, *args: Any, **kwargs: Any):
        return self.request("POST", url, *args, **kwargs)

    def put(self, url: Any, *args: Any, **kwargs: Any):
        return self.request("PUT", url, *args, **kwargs)

    def patch(self, url: Any, *args: Any, **kwargs: Any):
        return self.request("PATCH", url, *args, **kwargs)

    def delete(self, url: Any, *args: Any, **kwargs: Any):
        return self.request("DELETE", url, *args, **kwargs)

    def close(self) -> None:
        with self._lock:
            client = self._client
        _close_quietly(client)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def __getattr__(self, name: str):
        with self._lock:
            client = self._client
        return getattr(client, name)


def _close_quietly(client: Any) -> None:
    close = getattr(client, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass


def install_transport_resilience(resident) -> bool:
    """Replace upstream's import-time pools without dirtying its checkout."""
    if getattr(resident, "_io_transport_resilience_installed", False):
        return True

    logger = getattr(resident, "log", None)
    if not hasattr(resident, "_HTTP") or not hasattr(resident, "httpx"):
        if logger is not None:
            logger.warning(
                "[transport] upstream HTTP client hook missing; "
                "using upstream transport unchanged"
            )
        return False

    old_http = resident._HTTP
    resident._HTTP = _RecyclingHttpClient(resident)
    _close_quietly(old_http)

    if str(getattr(resident, "FEEDLING_ENCLAVE_URL", "") or "").strip():
        old_enclave = getattr(resident, "_ENCLAVE_CLIENT", None)
        resident._ENCLAVE_CLIENT = _RecyclingHttpClient(
            resident, verify=False
        )
        _close_quietly(old_enclave)

    resident._io_transport_resilience_installed = True
    if logger is not None:
        logger.info(
            "[transport] recycling pools installed timeout=%ss keepalive=%ss",
            HTTP_TIMEOUT_SEC,
            HTTP_KEEPALIVE_EXPIRY_SEC,
        )
    return True


def _allowed_mcp_names() -> set[str]:
    raw = os.environ.get(
        "FEEDLING_GARDEN_MCP_NAMES",
        "garden,galatea,galatea_garden",
    )
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _presence_mcp_names() -> set[str]:
    raw = os.environ.get(
        "FEEDLING_PRESENCE_MCP_NAMES",
        (
            "desire,desirecore,desire_core,phosphene,xinchao,"
            "xinchao_dynamic_mind,心潮,ob,ombre,ombre_brain,"
            "emotion,eventide"
        ),
    )
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def _is_garden_wake_prompt(message: Any) -> bool:
    return bool(GARDEN_TRIGGER_RE.search(str(message or "")))


def _is_presence_wake_prompt(message: Any) -> bool:
    text = str(message or "")
    return bool(PRESENCE_WAKE_RE.search(text)) and not _is_garden_wake_prompt(text)


def _presence_retry_prompt(message: Any) -> str:
    return (
        "The final control result from this proactive presence turn could not be "
        "parsed. All tool effects from that turn may already be committed. Do not "
        "call any tool and do not repeat any write. Re-evaluate only whether to "
        "speak or stay quiet from the same context below, then return exactly one "
        "JSON object with no Markdown fence and no text outside it: either "
        '{"messages":["natural message"]} or '
        '{"actions":[{"type":"proactive.sleep","reason":"short reason"}]}.'
        "\n\nOriginal proactive context:\n"
        + str(message or "")
    )


def install_patches(resident, materializer) -> bool:
    """Install idempotent, runtime-local patches on a consumer module.

    Feedling is allowed to self-update independently of this wrapper. If a
    future release changes the private hook contract, leave the ordinary
    resident running without the Garden lane instead of crashing IO Chat. The
    normal background policy disables user MCPs, so this fallback is also
    fail-closed for Garden and presence writes.
    """
    if getattr(resident, "_garden_wake_wrapper_installed", False):
        return True

    required_resident = (
        "_user_mcp_cli_value",
        "_user_mcp_applied",
        "_cli_template_is_codex",
        "call_agent",
        "_turn_reply_parse_failed",
        "log",
    )
    missing = [name for name in required_resident if not hasattr(resident, name)]
    if not hasattr(materializer, "effective_transport"):
        missing.append("user_mcp_materialize.effective_transport")
    if missing:
        logger = getattr(resident, "log", None)
        if logger is not None:
            logger.error(
                "[garden_wake] upstream compatibility contract changed; "
                "Garden lane disabled while ordinary IO Chat continues; missing=%s",
                ",".join(missing),
            )
        return False

    original_mcp_value = resident._user_mcp_cli_value
    lane_names = {
        GARDEN_LANE: _allowed_mcp_names(),
        PRESENCE_LANE: _presence_mcp_names(),
    }

    @functools.wraps(original_mcp_value)
    def selective_mcp_value(template: str, lane: str) -> str:
        if lane not in lane_names:
            return original_mcp_value(template, lane)
        if "{mcp}" not in template:
            return ""

        enabled_servers = [
            server
            for server in resident._user_mcp_applied.get("servers") or []
            if server.get("enabled")
        ]
        if not enabled_servers:
            return ""

        # This deployment uses Codex. Other drivers do not support enabling a
        # safe subset of user MCPs for one background turn, so they stay on the
        # normal all-disabled background policy.
        if not resident._cli_template_is_codex():
            resident.log.warning(
                "[garden_wake] selective MCP lane requires Codex; keeping user MCP disabled"
            )
            return original_mcp_value(template, "background")

        materialized = [
            server
            for server in enabled_servers
            if materializer.effective_transport(server) != "sse"
        ]
        allowed_names = lane_names[lane]
        selected_names = {
            str(server.get("name") or "").strip().lower()
            for server in materialized
            if str(server.get("name") or "").strip().lower() in allowed_names
        }
        if not selected_names:
            resident.log.error(
                "[%s_wake] no enabled MCP matched names=%s; turn will fail closed",
                lane,
                sorted(allowed_names),
            )

        disabled_names = sorted(
            str(server.get("name") or "").strip()
            for server in materialized
            if str(server.get("name") or "").strip()
            and str(server.get("name") or "").strip().lower() not in selected_names
        )
        return " ".join(
            f"-c mcp_servers.{name}.enabled=false" for name in disabled_names
        )

    original_call_agent = resident.call_agent
    call_signature = inspect.signature(original_call_agent)

    @functools.wraps(original_call_agent)
    def routed_call_agent(message: str, *args, **kwargs):
        bound = call_signature.bind_partial(message, *args, **kwargs)
        lane = str(bound.arguments.get("lane") or "background")
        if lane == "background" and _is_garden_wake_prompt(message):
            bound.arguments["lane"] = GARDEN_LANE
            resident.log.info(
                "[garden_wake] using selective Garden MCP background lane"
            )
        elif lane == "background" and _is_presence_wake_prompt(message):
            bound.arguments["lane"] = PRESENCE_LANE
            resident.log.info(
                "[presence_wake] using selective continuity MCP background lane"
            )

        result = original_call_agent(*bound.args, **bound.kwargs)
        routed_lane = str(bound.arguments.get("lane") or "background")
        failure_class = str(
            getattr(resident, "_turn_reply_parse_failed", "") or ""
        ).strip()
        if routed_lane != PRESENCE_LANE or not failure_class:
            return result

        resident.log.warning(
            "[presence_wake] final reply parse failed class=%s; retrying final "
            "protocol once with user MCPs disabled",
            failure_class,
        )
        # The original call resets this per-turn marker on entry. Calling the
        # unwrapped function directly with the ordinary background lane keeps
        # every user MCP disabled, so a format-only retry cannot duplicate an
        # OB/emotion/Eventide write that may already have succeeded.
        retry_kwargs: dict[str, Any] = {"lane": "background"}
        if "isolated_session" in call_signature.parameters:
            retry_kwargs["isolated_session"] = True
        return original_call_agent(_presence_retry_prompt(message), **retry_kwargs)

    resident._user_mcp_cli_value = selective_mcp_value
    resident.call_agent = routed_call_agent
    resident._garden_wake_wrapper_installed = True
    return True


def main() -> None:
    tools_path = str(TOOLS_DIR)
    if tools_path not in sys.path:
        sys.path.insert(0, tools_path)

    import chat_resident_consumer as resident  # noqa: PLC0415
    import user_mcp_materialize as materializer  # noqa: PLC0415

    install_transport_resilience(resident)
    install_patches(resident, materializer)
    resident.run()


if __name__ == "__main__":
    main()
