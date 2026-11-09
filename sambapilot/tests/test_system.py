from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from sambapilot.diagnostic import SERVICES, collect
from sambapilot.system import HostProbe, observe_path, read_service, service_command


class SystemTests(unittest.TestCase):
    def test_only_fixed_service_names_are_allowed(self):
        for name in ("sshd.service", "smb.service; reboot", "--help", "../smb.service"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                service_command(name)

    def test_service_query_has_no_shell_no_stdin_and_timeout(self):
        result = Mock(returncode=0, stdout="LoadState=loaded\nActiveState=inactive\nUnitFileState=disabled\n")
        with patch("sambapilot.system.subprocess.run", return_value=result) as runner:
            service = read_service("smb.service")
        self.assertEqual(service.status, "observed")
        self.assertEqual(service.active_state, "inactive")
        self.assertEqual(service.unit_file_state, "disabled")
        args, kwargs = runner.call_args
        self.assertEqual(args[0], ("/usr/bin/systemctl", "--system", "--no-pager",
                                  "--no-ask-password", "show", "smb.service",
                                  "--property=LoadState,ActiveState,UnitFileState"))
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(kwargs["timeout"], 3)
        self.assertNotIn("DBUS_SYSTEM_BUS_ADDRESS", kwargs["env"])

    def test_failed_query_does_not_report_missing_or_inactive(self):
        with patch("sambapilot.system.subprocess.run", return_value=Mock(returncode=1)):
            service = read_service("smb.service")
        self.assertEqual(service.status, "unknown")
        self.assertEqual(service.active_state, "unknown")

    def test_query_timeout_and_os_error_are_reported(self):
        for error in (subprocess.TimeoutExpired("systemctl", 3), PermissionError("denied")):
            with self.subTest(error=type(error)), \
                    patch("sambapilot.system.subprocess.run", side_effect=error):
                self.assertEqual(read_service("smb.service").status, "unknown")

    def test_not_found_unit_ignores_inactive_fallback(self):
        result = Mock(returncode=0, stdout="LoadState=not-found\nActiveState=inactive\nUnitFileState=\n")
        with patch("sambapilot.system.subprocess.run", return_value=result):
            service = read_service("smb.service")
        self.assertEqual(service.status, "missing")
        self.assertEqual(service.active_state, "unknown")

    def test_incomplete_service_output_is_unknown(self):
        with patch("sambapilot.system.subprocess.run", return_value=Mock(returncode=0, stdout="")):
            self.assertEqual(read_service("smb.service").status, "unknown")

    def test_path_observation_never_reads_config_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "smb.conf"
            config.write_text("private fixture", encoding="utf-8")
            with patch("pathlib.Path.open", side_effect=AssertionError("content read")):
                self.assertEqual(observe_path(config).status, "present")
                self.assertEqual(observe_path(Path(directory), directory=True).status, "present")
                self.assertEqual(observe_path(Path(directory)).status, "unknown")
                self.assertEqual(observe_path(config / "absent").status, "unknown")
                self.assertEqual(observe_path(Path(directory) / "absent").status, "missing")

    def test_permission_error_is_unknown_not_missing(self):
        with patch("pathlib.Path.stat", side_effect=PermissionError()):
            self.assertEqual(observe_path(Path("/unreadable")).status, "unknown")

    def test_tool_discovery_ignores_user_path_and_never_executes_tools(self):
        candidates = []

        def is_file(path):
            candidates.append(str(path))
            return str(path) == "/usr/sbin/ufw"

        with patch.object(Path, "is_file", is_file), \
                patch("sambapilot.system.os.access", return_value=True), \
                patch("subprocess.run", side_effect=AssertionError("process")), \
                patch.dict("os.environ", {"PATH": "/tmp/mise/shims"}):
            self.assertEqual(HostProbe().tool("ufw"), "/usr/sbin/ufw")
        self.assertEqual(candidates, ["/usr/bin/ufw", "/usr/sbin/ufw"])

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(ValueError):
            HostProbe().tool("sudo")

    def test_inaccessible_tool_paths_do_not_abort_diagnostic(self):
        with patch.object(Path, "is_file", side_effect=PermissionError()):
            self.assertIsNone(HostProbe().tool("smbd"))
            self.assertEqual(HostProbe().service("smb.service").status, "unknown")

    def test_linux_integration_uses_only_read_queries(self):
        result = Mock(returncode=0, stdout="LoadState=loaded\nActiveState=active\nUnitFileState=enabled\n")
        with patch("sambapilot.system.platform.system", return_value="Linux"), \
                patch.object(HostProbe, "os_release", return_value=('ID=arch', None)), \
                patch.object(HostProbe, "omarchy_marker"), \
                patch.object(HostProbe, "configuration"), \
                patch.object(Path, "is_file", return_value=True), \
                patch("sambapilot.system.os.access", return_value=True), \
                patch("sambapilot.system.subprocess.run", return_value=result) as runner:
            report = collect(HostProbe())
        self.assertTrue(report.environment.arch_based)
        self.assertEqual(runner.call_count, len(SERVICES))
        self.assertEqual([call.args[0] for call in runner.call_args_list],
                         [service_command(name) for name in SERVICES])

    def test_absent_systemctl_does_not_launch_anything(self):
        with patch.object(Path, "is_file", return_value=False), \
                patch("subprocess.run", side_effect=AssertionError("process")):
            self.assertEqual(HostProbe().service("smb.service").status, "unknown")


if __name__ == "__main__":
    unittest.main()
