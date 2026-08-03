#!/usr/bin/env python3
"""Manual lifecycle controller for the bundled Garden wake bridge.

This deliberately has no watchdog and no boot hook. A failed or disconnected
bridge stays stopped until a user explicitly runs ``check`` and ``start``.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from typing import Any


BRIDGE_ROOT = Path(
    os.environ.get("GARDEN_BRIDGE_ROOT", "/opt/galatea-garden-wake-bridge")
)
STATE_DIR = Path(os.environ.get("GARDEN_BRIDGE_STATE_DIR", "/data/feedling"))
PID_FILE = STATE_DIR / "garden-wake-bridge.pid"
LOG_FILE = STATE_DIR / "garden-wake-bridge.log"
NODE = os.environ.get("GARDEN_BRIDGE_NODE", "node")


class ControlError(RuntimeError):
    pass


def _bridge_command(action: str) -> list[str]:
    cli = BRIDGE_ROOT / "dist" / "cli.js"
    if not cli.is_file():
        raise ControlError(f"Garden bridge build is missing: {cli}")
    return [NODE, str(cli), action]


def _bridge_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("GARDEN_BASE_URL", "https://wake-v1.abysslumina.com")
    env.setdefault("GARDEN_INJECTOR_EXECUTABLE", NODE)
    env.setdefault(
        "GARDEN_INJECTOR_ARGS_JSON",
        json.dumps(
            [str(BRIDGE_ROOT / "integrations" / "feedling-io" / "inject.mjs")],
            ensure_ascii=False,
        ),
    )
    env.setdefault("GARDEN_INJECTOR_WORKING_DIRECTORY", str(BRIDGE_ROOT))
    return env


def _read_pid() -> int | None:
    try:
        value = int(PID_FILE.read_text(encoding="utf-8").strip())
        return value if value > 1 else None
    except (OSError, TypeError, ValueError):
        return None


def _is_bridge_process(pid: int | None) -> bool:
    if not pid:
        return False
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return False
    return b"dist/cli.js\x00run" in raw and b"galatea-garden-wake-bridge" in raw


def _clear_stale_pid() -> None:
    pid = _read_pid()
    if pid and _is_bridge_process(pid):
        return
    try:
        PID_FILE.unlink()
    except FileNotFoundError:
        pass


def status() -> dict[str, Any]:
    pid = _read_pid()
    running = _is_bridge_process(pid)
    if not running:
        _clear_stale_pid()
        pid = None
    return {
        "ok": True,
        "running": running,
        "pid": pid,
        "log_file": str(LOG_FILE),
        "restart_policy": "manual_only",
    }


def check(*, runner=subprocess.run) -> dict[str, Any]:
    completed = runner(
        _bridge_command("check"),
        cwd=BRIDGE_ROOT,
        env=_bridge_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
        check=False,
    )
    output = str(completed.stdout or "").strip()[-2000:]
    if completed.returncode != 0:
        raise ControlError(f"Garden bridge check failed: {output or 'no details'}")
    return {"ok": True, "check": "passed", "detail": output}


def start(*, runner=subprocess.run, popen=subprocess.Popen, settle_seconds: float = 0.75) -> dict[str, Any]:
    current = status()
    if current["running"]:
        return {**current, "already_running": True}

    env = _bridge_env()
    for name in ("GARDEN_MACHINE_TOKEN", "FEEDLING_API_KEY"):
        if not str(env.get(name) or "").strip():
            raise ControlError(f"required deployment secret is missing: {name}")

    check(runner=runner)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    log_fd = os.open(LOG_FILE, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
    try:
        process = popen(
            _bridge_command("run"),
            cwd=BRIDGE_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        os.close(log_fd)

    time.sleep(max(0.0, settle_seconds))
    code = process.poll()
    if code is not None:
        raise ControlError(
            f"Garden bridge exited during startup with code {code}; inspect {LOG_FILE}"
        )
    PID_FILE.write_text(f"{process.pid}\n", encoding="utf-8")
    os.chmod(PID_FILE, 0o600)
    return {
        "ok": True,
        "running": True,
        "pid": process.pid,
        "log_file": str(LOG_FILE),
        "restart_policy": "manual_only",
    }


def stop(*, timeout_seconds: float = 10.0) -> dict[str, Any]:
    current = status()
    pid = current.get("pid")
    if not current["running"] or not isinstance(pid, int):
        return {**current, "already_stopped": True}

    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + max(0.1, timeout_seconds)
    while time.monotonic() < deadline:
        if not _is_bridge_process(pid):
            _clear_stale_pid()
            return {
                "ok": True,
                "running": False,
                "pid": None,
                "restart_policy": "manual_only",
            }
        time.sleep(0.1)
    raise ControlError(
        "Garden bridge did not stop after SIGTERM; no forced kill was attempted"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Manual Garden wake bridge control")
    parser.add_argument("action", choices=("check", "start", "status", "stop"))
    args = parser.parse_args(argv)
    try:
        result = {
            "check": check,
            "start": start,
            "status": status,
            "stop": stop,
        }[args.action]()
    except (ControlError, OSError, subprocess.SubprocessError) as error:
        print(json.dumps({"ok": False, "error": str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
