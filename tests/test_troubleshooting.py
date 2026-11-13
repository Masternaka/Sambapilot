import contextlib
from dataclasses import replace
import io
import json
import unittest
from unittest.mock import patch

from sambapilot.cli import main
from sambapilot.demo import DemoProbe
from sambapilot.diagnostic import Service, collect
from sambapilot.troubleshooting import SYMPTOMS, format_troubleshooting, troubleshoot


class TroubleshootingTests(unittest.TestCase):
    def test_guidance_uses_only_provided_observations(self):
        report = collect(DemoProbe())
        with patch("subprocess.run", side_effect=AssertionError("process")), \
                patch("pathlib.Path.open", side_effect=AssertionError("file")):
            for symptom in SYMPTOMS:
                result = troubleshoot(report, symptom)
                self.assertIs(result.diagnostic, report)
                self.assertFalse(result.can_apply)
                self.assertEqual(result.mode, "demo")
                findings = {item.key: item for item in result.findings}
                self.assertEqual(findings["network"].status, "unknown")
                self.assertEqual(findings["security"].status, "unknown")
                if symptom == "readonly":
                    self.assertEqual(findings["write"].status, "unknown")

    def test_masked_failed_and_unknown_services_remain_distinct(self):
        original = collect(DemoProbe(distribution="debian"))
        for service, expected in ((Service("smbd.service", "observed", "loaded", "active", "enabled"), "observed"),
                                   (Service("smbd.service", "observed", "loaded", "inactive", "masked"), "attention"),
                                   (Service("smbd.service", "observed", "loaded", "failed", "disabled"), "attention"),
                                   (Service("smbd.service", "unknown"), "unknown")):
            with self.subTest(service=service):
                result = troubleshoot(replace(original, services=(service,)), "denied")
                finding = next(item for item in result.findings if item.key == "service")
                self.assertEqual(finding.status, expected)

    def test_missing_configuration_needs_review_not_overwrite(self):
        result = troubleshoot(collect(DemoProbe("fresh")), "invisible")
        finding = next(item for item in result.findings if item.key == "configuration")
        self.assertEqual(finding.status, "attention")
        self.assertIn("explicitement", finding.next_step)

    def test_unknown_configuration_is_not_missing(self):
        result = troubleshoot(collect(DemoProbe("restricted")), "readonly")
        self.assertEqual(next(item for item in result.findings if item.key == "configuration").status, "unknown")

    def test_non_linux_guidance_stops_before_samba_interpretation(self):
        probe = DemoProbe()
        with patch.object(probe, "system", return_value="Darwin"):
            result = troubleshoot(collect(probe), "denied")
        self.assertEqual([finding.key for finding in result.findings], ["platform"])

    def test_unknown_symptom_is_refused(self):
        with self.assertRaises(ValueError):
            troubleshoot(collect(DemoProbe()), "restart")

    def test_cli_demo_works_for_all_symptoms_without_host(self):
        with patch("sambapilot.cli.HostProbe", side_effect=AssertionError("host")), \
                patch("subprocess.run", side_effect=AssertionError("process")):
            for symptom in SYMPTOMS:
                with self.subTest(symptom=symptom), contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(["depannage", "--demo", "--distribution", "fedora", "--symptom", symptom, "--json"]), 0)
                    report = json.loads(output.getvalue())
                    self.assertFalse(report["can_apply"])
                    self.assertEqual(report["diagnostic"]["environment"]["distribution_family"], "fedora")

    def test_cli_requires_explicit_source_and_valid_symptom(self):
        for args in (["--symptom", "denied"], ["--demo", "--local", "--symptom", "denied"],
                     ["--demo", "--symptom", "restart"]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(["depannage", *args])

    def test_terminal_sanitizes_observed_details(self):
        report = collect(DemoProbe())
        report = replace(report, configuration=replace(report.configuration, detail="bad\x1b[2J"))
        self.assertNotIn("\x1b", format_troubleshooting(troubleshoot(report, "invisible")))
