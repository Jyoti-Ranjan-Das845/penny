"""Check configured verdicts, not end-to-end native tool interception."""

import unittest
from pathlib import Path

from omnigent.spec import load
from omnigent.spec.types import Phase, PolicyAction
from omnigent.policies.function import resolve_function_policy
from omnigent.policies.types import EvaluationContext


PROJECT = Path(__file__).resolve().parents[1]
TOOLS = (
    "Write", "Edit", "Bash", "Read", "apply_patch", "exec_command",
    "sys_os_write", "sys_os_shell", "sys_session_send",
    "sys_add_policy", "mcp__external__send",
)


class RolePolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_children_deny_tools_and_allow_text(self):
        for role in ("intent", "reader", "curator"):
            spec = load(PROJECT / "omnigent" / "agents" / role, expand_env=False)
            self.assertEqual(len(spec.guardrails.policies), 1)
            policy = resolve_function_policy(spec.guardrails.policies[0])
            for name in TOOLS:
                with self.subTest(role=role, tool=name):
                    result = await policy.evaluate(EvaluationContext(
                        phase=Phase.TOOL_CALL,
                        content={"name": name, "arguments": {}}, tool_name=name,
                    ), {})
                    self.assertEqual(result.action, PolicyAction.DENY)
            for phase in (Phase.REQUEST, Phase.RESPONSE):
                with self.subTest(role=role, phase=phase):
                    result = await policy.evaluate(EvaluationContext(
                        phase=phase, content="Synthetic review text",
                    ), {})
                    self.assertEqual(result.action, PolicyAction.ALLOW)


if __name__ == "__main__":
    unittest.main()
