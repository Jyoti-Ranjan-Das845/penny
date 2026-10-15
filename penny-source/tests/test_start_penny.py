from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import start_penny


class StartPennyTests(unittest.TestCase):
    def setUp(self):
        self.server_status = patch.object(
            start_penny, "local_server_status", return_value=Mock(running=False, pid=None)
        ).start()
        self.addCleanup(patch.stopall)

    def test_refuses_any_recorded_daemon_without_touching_server(self):
        status = Mock(stdout='{"daemons":[{"process":"online","target":"local"}]}')
        with patch.object(start_penny.subprocess, "run", return_value=status), \
                patch.object(start_penny.socket, "create_connection") as connect:
            with self.assertRaisesRegex(RuntimeError, "host daemon"):
                start_penny.require_stopped()
            connect.assert_not_called()

    def test_refuses_server_and_uncertain_status(self):
        with patch.object(start_penny.subprocess, "run", return_value=Mock(stdout='{"daemons":[]}')), \
                patch.object(start_penny.socket, "create_connection", return_value=Mock()) as connect:
            with self.assertRaisesRegex(RuntimeError, "port 6767"):
                start_penny.require_stopped()
            connect.return_value.close.assert_called_once()
        with patch.object(start_penny.subprocess, "run", return_value=Mock(stdout='{}')):
            with self.assertRaisesRegex(RuntimeError, "verify local host"):
                start_penny.require_stopped()

    def test_only_connection_refused_confirms_stopped(self):
        with patch.object(start_penny.subprocess, "run", return_value=Mock(stdout='{"daemons":[]}')), \
                patch.object(start_penny.socket, "create_connection", side_effect=ConnectionRefusedError):
            start_penny.require_stopped()
        with patch.object(start_penny.subprocess, "run", return_value=Mock(stdout='{"daemons":[]}')), \
                patch.object(start_penny.socket, "create_connection", side_effect=TimeoutError):
            with self.assertRaisesRegex(RuntimeError, "verify that"):
                start_penny.require_stopped()

    def test_refuses_standalone_server_on_fallback_port(self):
        self.server_status.return_value = Mock(running=True, pid=123, port=8123)
        with patch.object(start_penny.subprocess, "run", return_value=Mock(stdout='{"daemons":[]}')), \
                patch.object(start_penny.socket, "create_connection", side_effect=ConnectionRefusedError) as connect:
            with self.assertRaisesRegex(RuntimeError, "local server is still recorded"):
                start_penny.require_stopped()
            connect.assert_not_called()

    @patch.object(start_penny, "validate_bundle")
    @patch.object(start_penny, "version", return_value=start_penny.VERIFIED_RUNTIME)
    def test_environment_preserves_extras_and_never_mutates_original(self, _version, validate):
        original = {"OMNIGENT_BUILTIN_AGENT_DIRS": "/tmp/other", "UNRELATED": "kept"}
        selected = start_penny.start_environment(Path("/tmp/penny"), original)
        self.assertEqual(selected["OMNIGENT_BUILTIN_AGENT_DIRS"], "/tmp/other:/tmp/penny")
        self.assertEqual(selected["UNRELATED"], "kept")
        self.assertEqual(original["OMNIGENT_BUILTIN_AGENT_DIRS"], "/tmp/other")
        self.assertEqual(start_penny.start_environment(Path("/tmp/penny"), selected), selected)
        validate.assert_called_with(Path("/tmp/penny"))

    @patch.object(start_penny, "validate_bundle")
    @patch.object(start_penny, "version", return_value=start_penny.VERIFIED_RUNTIME)
    def test_rejects_wrong_basename_and_conflicting_source(self, _version, _validate):
        with self.assertRaises(ValueError):
            start_penny.start_environment(Path("/tmp/penny-release"), {})
        with self.assertRaisesRegex(ValueError, "Another Penny source"):
            start_penny.start_environment(Path("/tmp/penny"), {"OMNIGENT_BUILTIN_AGENT_DIRS": "/other/penny"})

    def test_check_only_never_starts_and_preflight_failure_never_starts(self):
        args = ["start_penny.py", "--bundle", "/tmp/penny", "--check-only"]
        with patch.object(sys, "argv", args), \
                patch.object(start_penny, "start_environment", return_value={}), \
                patch.object(start_penny, "require_stopped"), \
                patch.object(start_penny.subprocess, "call") as call:
            start_penny.main()
            call.assert_not_called()
        with patch.object(sys, "argv", args[:-1]), \
                patch.object(start_penny, "start_environment", return_value={}), \
                patch.object(start_penny, "require_stopped", side_effect=RuntimeError("still running")), \
                patch.object(start_penny.subprocess, "call") as call:
            with self.assertRaises(RuntimeError):
                start_penny.main()
            call.assert_not_called()


if __name__ == "__main__":
    unittest.main()
