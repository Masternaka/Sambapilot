import contextlib
import io
import json
import unittest
from unittest.mock import Mock, patch

from sambapilot.cli import main, render
from sambapilot.demo import DemoProbe, SCENARIOS
from sambapilot.diagnostic import collect, parse_os_release


class DiagnosticTests(unittest.TestCase):
    def test_os_release_is_parsed_without_expanding_shell_content(self):
        values = parse_os_release('''# commentaire
ID=arch
ID_LIKE="arch linux"
PRETTY_NAME="$(touch /tmp/unwanted)"
IGNORED=value
MALFORMED
''')
        self.assertEqual(values, {"ID": "arch", "ID_LIKE": "arch linux",
                                  "PRETTY_NAME": "$(touch /tmp/unwanted)"})

    def test_malformed_values_are_ignored(self):
        self.assertEqual(parse_os_release('ID="unterminated\nID_LIKE=\nPRETTY_NAME=a b'), {})

    def test_demo_never_instantiates_host_or_executes_process(self):
        with patch("sambapilot.cli.HostProbe", side_effect=AssertionError("host")), \
                patch("subprocess.run", side_effect=AssertionError("subprocess")), \
                patch("pathlib.Path.open", side_effect=AssertionError("open")), \
                patch("pathlib.Path.stat", side_effect=AssertionError("stat")):
            for scenario in SCENARIOS:
                with self.subTest(scenario=scenario), contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(["diagnostic", "--demo", scenario, "--json"]), 0)
                    data = json.loads(output.getvalue())
                    self.assertEqual(data["mode"], "demo")
                    self.assertEqual(data["schema_version"], 1)

    def test_fresh_demo_does_not_claim_samba_installed(self):
        report = collect(DemoProbe("fresh"))
        tools = {tool.name: tool.path for tool in report.tools}
        self.assertIsNone(tools["smbd"])
        self.assertIsNotNone(tools["pacman"])
        self.assertEqual(report.configuration.status, "missing")
        self.assertTrue(all(service.status == "missing" for service in report.services))

    def test_restricted_demo_preserves_unknown_state(self):
        report = collect(DemoProbe("restricted"))
        self.assertEqual(report.configuration.status, "unknown")
        self.assertTrue(all(service.active_state == "unknown" for service in report.services))
        self.assertTrue(all(service.status == "unknown" for service in report.services))

    def test_configured_demo_distinguishes_active_service_from_rules(self):
        report = collect(DemoProbe())
        services = {service.name: service for service in report.services}
        self.assertEqual(services["smb.service"].active_state, "active")
        self.assertEqual(services["ufw.service"].unit_file_state, "enabled")
        self.assertTrue(any("règles effectives" in note for note in report.notes))

    def test_non_linux_only_asks_for_platform(self):
        probe = Mock(mode="live")
        probe.system.return_value = "Darwin"
        report = collect(probe)
        self.assertEqual(report.environment.system, "Darwin")
        self.assertEqual(report.services, ())
        self.assertEqual(report.tools, ())
        probe.os_release.assert_not_called()
        probe.omarchy_marker.assert_not_called()
        probe.configuration.assert_not_called()
        probe.service.assert_not_called()
        probe.tool.assert_not_called()

    def test_unknown_distribution_does_not_claim_arch(self):
        probe = DemoProbe()
        with patch.object(probe, "os_release", return_value=("", "Lecture refusée.")):
            report = collect(probe)
        self.assertEqual(report.environment.distribution_id, "unknown")
        self.assertFalse(report.environment.arch_based)
        self.assertIn("Lecture refusée.", report.notes)

    def test_arch_derivative_is_recognized_without_claiming_omarchy(self):
        probe = DemoProbe()
        with patch.object(probe, "os_release", return_value=('ID=other\nID_LIKE="arch"', None)):
            report = collect(probe)
        self.assertTrue(report.environment.arch_based)
        self.assertTrue(any("ne certifie pas" in note for note in report.notes))

    def test_terminal_filters_control_characters(self):
        probe = DemoProbe()
        with patch.object(probe, "os_release", return_value=('ID=arch\nPRETTY_NAME="bad\x1b[2J"', None)):
            text = render(collect(probe))
        self.assertNotIn("\x1b", text)

    def test_cli_non_linux_exit_code_and_json(self):
        with patch("sambapilot.system.platform.system", return_value="Darwin"), \
                patch("subprocess.run", side_effect=AssertionError("process")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["diagnostic", "--json"]), 2)
        self.assertEqual(json.loads(output.getvalue())["environment"]["system"], "Darwin")

    def test_no_mutating_cli_command_is_available(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["install"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
