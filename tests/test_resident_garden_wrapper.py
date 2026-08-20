from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock


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
    _turn_reply_parse_failed = ""
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
        FakeResident._turn_reply_parse_failed = ""
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

    def test_ordinary_presence_wake_uses_selective_presence_lane(self):
        FakeResident.call_agent(
            "[Feedling proactive wake]\n\nwake_metadata:\n- trigger: heartbeat\n"
        )
        self.assertEqual(FakeResident.calls[-1]["lane"], "presence")

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

    def test_upstream_contract_change_keeps_io_chat_running(self):
        class FutureResident:
            log = logging.getLogger("garden-wrapper-contract-test")
            _garden_wake_wrapper_installed = False

            @staticmethod
            def call_agent(message, lane="background"):
                return {"message": message, "lane": lane}

        original = FutureResident.call_agent
        installed = WRAPPER.install_patches(FutureResident, Materializer)

        self.assertFalse(installed)
        self.assertIs(FutureResident.call_agent, original)
        self.assertFalse(FutureResident._garden_wake_wrapper_installed)


class TransportResilienceTests(unittest.TestCase):
    def test_replaces_backend_and_enclave_pools_and_closes_old_clients(self):
        old_http = mock.Mock()
        old_enclave = mock.Mock()
        new_http = mock.Mock()
        new_enclave = mock.Mock()
        httpx_module = SimpleNamespace(
            Client=mock.Mock(side_effect=[new_http, new_enclave]),
            Timeout=mock.Mock(return_value="timeout-config"),
            Limits=mock.Mock(return_value="limits-config"),
        )
        resident = SimpleNamespace(
            _HTTP=old_http,
            _ENCLAVE_CLIENT=old_enclave,
            FEEDLING_ENCLAVE_URL="https://enclave.example",
            httpx=httpx_module,
            log=logging.getLogger("transport-wrapper-test"),
        )

        installed = WRAPPER.install_transport_resilience(resident)

        self.assertTrue(installed)
        self.assertIs(resident._HTTP, new_http)
        self.assertIs(resident._ENCLAVE_CLIENT, new_enclave)
        old_http.close.assert_called_once_with()
        old_enclave.close.assert_called_once_with()
        self.assertEqual(httpx_module.Client.call_count, 2)
        self.assertTrue(httpx_module.Client.call_args_list[0].kwargs["verify"])
        self.assertFalse(httpx_module.Client.call_args_list[1].kwargs["verify"])

    def test_is_idempotent(self):
        resident = SimpleNamespace(
            _HTTP=mock.Mock(),
            _io_transport_resilience_installed=True,
        )
        self.assertTrue(WRAPPER.install_transport_resilience(resident))


if __name__ == "__main__":
    unittest.main()
