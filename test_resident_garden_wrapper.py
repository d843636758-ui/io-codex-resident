import logging
import types
import unittest

import resident_garden_wrapper as wrapper


class _Materializer:
    @staticmethod
    def effective_transport(server):
        return server.get("transport", "streamable_http")


def _resident(call_impl):
    resident = types.SimpleNamespace()
    resident._user_mcp_applied = {
        "servers": [
            {"name": "garden", "enabled": True},
            {"name": "desire", "enabled": True},
            {"name": "emotion", "enabled": True},
            {"name": "unrelated", "enabled": True},
        ]
    }
    resident._turn_reply_parse_failed = ""
    resident._cli_template_is_codex = lambda: True
    resident._user_mcp_cli_value = (
        lambda template, lane: "ordinary-background-policy"
    )
    resident.call_agent = call_impl
    resident.log = logging.getLogger("wrapper-test")
    return resident


class WrapperTests(unittest.TestCase):
    def test_presence_lane_exposes_only_continuity_mcps(self):
        resident = _resident(lambda message, lane="background": message)
        self.assertTrue(wrapper.install_patches(resident, _Materializer()))

        value = resident._user_mcp_cli_value("codex {mcp}", "presence")

        self.assertNotIn("mcp_servers.desire.enabled=false", value)
        self.assertNotIn("mcp_servers.emotion.enabled=false", value)
        self.assertIn("mcp_servers.garden.enabled=false", value)
        self.assertIn("mcp_servers.unrelated.enabled=false", value)

    def test_presence_parse_failure_retries_once_without_presence_lane(self):
        calls = []
        resident = None

        def call_agent(message, lane="background", isolated_session=False):
            calls.append((message, lane, isolated_session))
            if len(calls) == 1:
                resident._turn_reply_parse_failed = "reply_parse_failed"
                return ["fallback"]
            resident._turn_reply_parse_failed = ""
            return '{"actions":[{"type":"proactive.sleep","reason":"quiet"}]}'

        resident = _resident(call_agent)
        self.assertTrue(wrapper.install_patches(resident, _Materializer()))

        result = resident.call_agent("[Feedling proactive wake]\n\ncontext")

        self.assertEqual(2, len(calls))
        self.assertEqual("presence", calls[0][1])
        self.assertEqual("background", calls[1][1])
        self.assertTrue(calls[1][2])
        self.assertIn("Do not call any tool", calls[1][0])
        self.assertIn("proactive.sleep", result)

    def test_garden_and_ordinary_background_routing_are_unchanged(self):
        calls = []

        def call_agent(message, lane="background", isolated_session=False):
            calls.append(lane)
            return "ok"

        resident = _resident(call_agent)
        self.assertTrue(wrapper.install_patches(resident, _Materializer()))

        resident.call_agent(
            "[Feedling proactive wake]\n- trigger: garden_wake_game_turn_required"
        )
        resident.call_agent("[maintenance]")

        self.assertEqual(["garden", "background"], calls)


if __name__ == "__main__":
    unittest.main()
