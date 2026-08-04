from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class GardenActionGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.start_script = (ROOT / "start.sh").read_text(encoding="utf-8")

    def test_guard_uses_a_new_persistent_marker(self):
        self.assertIn("feedling-io-garden-action-guard-v1", self.start_script)

    def test_guard_requires_fresh_authoritative_status(self):
        self.assertIn("get_my_status(since_event_id=0)", self.start_script)
        self.assertIn("expected_state_version", self.start_script)
        self.assertIn("stable `request_id`", self.start_script)

    def test_guard_forbids_optional_compensating_actions(self):
        self.assertIn("At most one state-changing game call", self.start_script)
        self.assertIn("accept that server result as final", self.start_script)
        for forbidden in (
            "`reveal_item`",
            "`give_item`",
            "initiating a steal or robbery",
            "trade/exchange",
        ):
            self.assertIn(forbidden, self.start_script)
        self.assertIn("If no required action is pending, perform no write", self.start_script)


if __name__ == "__main__":
    unittest.main()
