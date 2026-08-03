from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "resident_garden_wrapper",
    ROOT / "resident_garden_wrapper.py",
)
assert SPEC and SPEC.loader
WRAPPER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(WRAPPER)


class Materializer:
    @staticmethod
    def effective_transport(server):
        return server.get("transport") or "streamable-http"


class FakeResident:
    log = logging.getLogger("garden-wrapper-test")
    _garden_wake_wrapper_installed = False
    _user_mcp_applied = {
        "servers": [
            {"name": "garden", "enabled": True, "transport": "streamable-http"},
            {"name": "ob", "enabled": True, "transport": "streamable-http"},
            {"name": "legacy", "enabled": True, "transport": "sse"},
        ]
    }
    calls = []

    @staticmethod
    def _cli_template_is_codex():
        return True

    @staticmethod
    def _user_mcp_cli_value(template, lane):
        return f"original:{lane}"

    @classmethod
    def call_agent(
        cls,
        message,
        images=None,
        image_paths=None,
        raw_text=False,
        trace_id="",
        lane="background",
    ):
        cls.calls.append({"message": message, "lane": lane})
        return {"messages": [], "actions": [{"type": "proactive.sleep"}]}


class GardenWrapperTests(unittest.TestCase):
    def setUp(self):
        FakeResident._garden_wake_wrapper_installed = False
        FakeResident.calls = []
        FakeResident._user_mcp_cli_value = staticmethod(
            lambda template, lane: f"original:{lane}"
        )
        FakeResident.call_agent = classmethod(
            lambda cls, message, images=None, image_paths=None, raw_text=False,
            trace_id="", lane="background": cls.calls.append(
                {"message": message, "lane": lane}
            ) or {"messages": [], "actions": [{"type": "proactive.sleep"}]}
        )
        WRAPPER.install_patches(FakeResident, Materializer)

    def test_garden_trigger_uses_selective_lane(self):
        FakeResident.call_agent(
            "[Feedling proactive wake]\n\nwake_metadata:\n- trigger: garden_wake_game_turn_required\n"
        )
        self.assertEqual(FakeResident.calls[-1]["lane"], "garden")

    def test_ordinary_background_wake_stays_background(self):
        FakeResident.call_agent(
            "[Feedling proactive wake]\n\nwake_metadata:\n- trigger: heartbeat\n"
        )
        self.assertEqual(FakeResident.calls[-1]["lane"], "background")

    def test_coalesced_wake_still_uses_garden_lane(self):
        FakeResident.call_agent(
            "[Feedling proactive wake]\n\nwake_metadata:\n"
            "- trigger: heartbeat, garden_wake_game_turn_required\n"
        )
        self.assertEqual(FakeResident.calls[-1]["lane"], "garden")

    def test_garden_lane_disables_every_other_materialized_user_mcp(self):
        value = FakeResident._user_mcp_cli_value("codex {mcp}", "garden")
        self.assertEqual(value, "-c mcp_servers.ob.enabled=false")

    def test_foreground_policy_is_untouched(self):
        value = FakeResident._user_mcp_cli_value("codex {mcp}", "chat")
        self.assertEqual(value, "original:chat")


if __name__ == "__main__":
    unittest.main()
