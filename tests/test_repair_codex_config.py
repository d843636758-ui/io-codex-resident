import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).parents[1] / "repair_codex_config.py"
SPEC = importlib.util.spec_from_file_location("repair_codex_config", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ContainerRuntimePolicyTests(unittest.TestCase):
    def test_workspace_write_is_migrated_for_container_runtime(self):
        source = 'approval_policy = "never"\nsandbox_mode = "workspace-write"\n'
        result, changed = MODULE.enforce_container_runtime(source)
        self.assertTrue(changed)
        self.assertIn('sandbox_mode = "danger-full-access"', result)
        self.assertNotIn('sandbox_mode = "workspace-write"', result)

    def test_container_runtime_policy_is_idempotent(self):
        source = 'sandbox_mode = "danger-full-access"\n[other]\nvalue = true\n'
        result, changed = MODULE.enforce_container_runtime(source)
        self.assertFalse(changed)
        self.assertEqual(result, source)

    def test_missing_sandbox_mode_is_added_at_top_level(self):
        source = '[sandbox_workspace_write]\nnetwork_access = true\n'
        result, changed = MODULE.enforce_container_runtime(source)
        self.assertTrue(changed)
        self.assertTrue(result.startswith('sandbox_mode = "danger-full-access"\n'))
