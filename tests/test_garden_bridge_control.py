from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "garden_bridge_control",
    ROOT / "garden_bridge_control.py",
)
assert SPEC and SPEC.loader
CONTROL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTROL)


class GardenBridgeControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "bridge"
        (root / "dist").mkdir(parents=True)
        (root / "dist" / "cli.js").write_text("// test", encoding="utf-8")
        (root / "integrations" / "feedling-io").mkdir(parents=True)
        (root / "integrations" / "feedling-io" / "inject.mjs").write_text(
            "// test", encoding="utf-8"
        )
        state = Path(self.temp.name) / "state"
        CONTROL.BRIDGE_ROOT = root
        CONTROL.STATE_DIR = state
        CONTROL.PID_FILE = state / "garden-wake-bridge.pid"
        CONTROL.LOG_FILE = state / "garden-wake-bridge.log"

    def tearDown(self):
        self.temp.cleanup()

    def test_check_uses_the_bridge_check_command(self):
        calls = []

        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(returncode=0, stdout="configuration valid")

        result = CONTROL.check(runner=runner)
        self.assertEqual(result["check"], "passed")
        self.assertEqual(calls[0][0][-1], "check")

    def test_start_requires_both_deployment_secrets(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(CONTROL.ControlError, "GARDEN_MACHINE_TOKEN"):
                CONTROL.start(settle_seconds=0)

    def test_start_runs_check_then_launches_without_a_shell(self):
        runner_calls = []
        popen_calls = []

        def runner(command, **kwargs):
            runner_calls.append(command)
            return SimpleNamespace(returncode=0, stdout="ok")

        class Process:
            pid = 4321

            @staticmethod
            def poll():
                return None

        def popen(command, **kwargs):
            popen_calls.append((command, kwargs))
            return Process()

        env = {"GARDEN_MACHINE_TOKEN": "garden", "FEEDLING_API_KEY": "feedling"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            CONTROL, "status", return_value={"ok": True, "running": False, "pid": None}
        ):
            result = CONTROL.start(runner=runner, popen=popen, settle_seconds=0)

        self.assertEqual(result["pid"], 4321)
        self.assertEqual(runner_calls[0][-1], "check")
        self.assertEqual(popen_calls[0][0][-1], "run")
        self.assertNotIn("shell", popen_calls[0][1])
        self.assertTrue(popen_calls[0][1]["start_new_session"])

    def test_status_clears_a_stale_pid(self):
        CONTROL.STATE_DIR.mkdir(parents=True)
        CONTROL.PID_FILE.write_text("999999\n", encoding="utf-8")
        result = CONTROL.status()
        self.assertFalse(result["running"])
        self.assertFalse(CONTROL.PID_FILE.exists())


if __name__ == "__main__":
    unittest.main()
