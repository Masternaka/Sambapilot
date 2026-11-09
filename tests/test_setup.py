import contextlib
from dataclasses import replace
import io
import json
import subprocess
import unittest
from unittest.mock import Mock, patch

from sambapilot.cli import main
from sambapilot.diagnostic import Observation, Service, collect
from sambapilot.setup import (DemoSetupProbe, HostSetupProbe, Package, build_installation_plan,
                              collect_installation_plan, query_package)


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.report = collect(DemoSetupProbe("configured"))
        self.packages = (Package("samba", "installed", "example"), Package("smbclient", "installed", "example"))

    def steps(self, plan):
        return {step.key: step for step in plan.steps}

    def test_fresh_demo_proposes_packages_without_running_or_reading_anything(self):
        with patch("subprocess.run", side_effect=AssertionError("process")), \
                patch("pathlib.Path.open", side_effect=AssertionError("open")), \
                patch("pathlib.Path.stat", side_effect=AssertionError("stat")):
            plan = collect_installation_plan(DemoSetupProbe("fresh"))
        self.assertEqual(plan.mode, "demo")
        self.assertEqual(plan.status, "review")
        self.assertFalse(plan.can_apply)
        steps = self.steps(plan)
        self.assertEqual(steps["package:samba"].status, "needed")
        self.assertEqual(steps["configuration"].status, "needed")
        self.assertEqual(steps["smb-service"].status, "after-packages")

    def test_configured_demo_preserves_existing_components(self):
        plan = collect_installation_plan(DemoSetupProbe("configured"))
        steps = self.steps(plan)
        for key in ("package:samba", "package:smbclient", "smb-service", "startup"):
            self.assertEqual(steps[key].status, "retained")
        self.assertEqual(steps["configuration"].status, "review")
        self.assertEqual(steps["firewall"].status, "review")
        self.assertEqual(plan.status, "review")

    def test_inaccessible_states_never_become_install_requests(self):
        plan = collect_installation_plan(DemoSetupProbe("restricted"))
        self.assertEqual(plan.status, "blocked")
        self.assertEqual(self.steps(plan)["package:samba"].status, "blocked")
        self.assertEqual(self.steps(plan)["configuration"].status, "blocked")

    def test_non_linux_stops_probes_and_package_queries(self):
        probe = Mock(mode="live")
        probe.system.return_value = "Darwin"
        plan = collect_installation_plan(probe)
        self.assertEqual(plan.status, "blocked")
        probe.package.assert_not_called()
        probe.tool.assert_not_called()
        probe.service.assert_not_called()
        self.assertTrue(all(package.status == "unknown" for package in plan.packages))

    def test_non_arch_skips_package_queries(self):
        probe = DemoSetupProbe("configured")
        with patch.object(probe, "os_release", return_value=('ID=debian\n', None)), \
                patch.object(probe, "package", side_effect=AssertionError("query")):
            plan = collect_installation_plan(probe)
        self.assertEqual(plan.status, "blocked")
        self.assertEqual(self.steps(plan)["package:samba"].status, "blocked")

    def test_absent_pacman_never_triggers_a_query(self):
        probe = DemoSetupProbe("configured")
        original = probe.tool
        with patch.object(probe, "tool", side_effect=lambda name: None if name == "pacman" else original(name)), \
                patch.object(probe, "package", side_effect=AssertionError("query")):
            self.assertEqual(collect_installation_plan(probe).status, "blocked")

    def test_package_and_executable_disagreement_blocks_reinstallation(self):
        missing = (Package("samba", "missing"), self.packages[1])
        plan = build_installation_plan(self.report, missing)
        self.assertEqual(self.steps(plan)["package:samba"].status, "blocked")
        self.assertTrue(any("Incohérence" in blocker for blocker in plan.blockers))
        tools = tuple(tool for tool in self.report.tools if tool.name != "testparm")
        plan = build_installation_plan(replace(self.report, tools=tools), self.packages)
        self.assertEqual(self.steps(plan)["package:samba"].status, "blocked")

    def test_masked_and_failed_services_are_not_started_blindly(self):
        for active, startup in (("inactive", "masked"), ("active", "masked-runtime"), ("failed", "disabled")):
            services = tuple(Service(item.name, "observed", "loaded", active, startup)
                             if item.name == "smb.service" else item for item in self.report.services)
            with self.subTest(active=active, startup=startup):
                plan = build_installation_plan(replace(self.report, services=services), self.packages)
                self.assertEqual(self.steps(plan)["smb-service"].status, "blocked")
                self.assertEqual(plan.status, "blocked")

    def test_active_and_persistent_startup_remain_distinct(self):
        for active, startup, start_status in (("active", "disabled", "retained"), ("inactive", "disabled", "needed"),
                                               ("active", "enabled-runtime", "retained")):
            services = tuple(Service(item.name, "observed", "loaded", active, startup)
                             if item.name == "smb.service" else item for item in self.report.services)
            with self.subTest(active=active, startup=startup):
                plan = build_installation_plan(replace(self.report, services=services), self.packages)
                self.assertEqual(self.steps(plan)["smb-service"].status, start_status)
                self.assertEqual(self.steps(plan)["startup"].status, "review")

    def test_unreadable_configuration_does_not_propose_overwriting_it(self):
        report = replace(self.report, configuration=Observation("unknown", "denied"))
        plan = build_installation_plan(report, self.packages)
        self.assertEqual(self.steps(plan)["configuration"].status, "blocked")

    def test_multiple_firewall_services_do_not_choose_one_or_open_any_network(self):
        services = tuple(Service(item.name, "observed", "loaded", "active", "enabled")
                         if item.name in {"ufw.service", "nftables.service"} else item for item in self.report.services)
        plan = build_installation_plan(replace(self.report, services=services), self.packages)
        step = self.steps(plan)["firewall"]
        self.assertEqual(step.status, "review")
        self.assertIn("Plusieurs", step.detail)
        self.assertIn("Choisir le réseau", step.detail)
        self.assertFalse(plan.can_apply)

    def test_fingerprint_changes_when_package_state_changes(self):
        first = build_installation_plan(self.report, self.packages)
        self.assertEqual(first.basis_sha256, build_installation_plan(self.report, self.packages).basis_sha256)
        packages = (replace(self.packages[0], version="different"), self.packages[1])
        self.assertNotEqual(first.basis_sha256, build_installation_plan(self.report, packages).basis_sha256)

    def test_missing_duplicate_or_invalid_package_observations_are_refused(self):
        for packages in ((self.packages[0],), (self.packages[0], self.packages[0]),
                         (replace(self.packages[0], status="inferred"), self.packages[1])):
            with self.subTest(packages=packages), self.assertRaises(ValueError):
                build_installation_plan(self.report, packages)

    def test_cli_demo_and_json_never_instantiate_host(self):
        with patch("sambapilot.cli.HostSetupProbe", side_effect=AssertionError("host")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["preparer-installation", "--demo", "--json"]), 0)
        report = json.loads(output.getvalue())
        self.assertFalse(report["can_apply"])
        self.assertEqual(report["mode"], "demo")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["preparer-installation", "--demo", "restricted"]), 2)

    def test_cli_source_choice_is_required_and_exclusive(self):
        for args in ([], ["--local", "--demo"]):
            with self.subTest(args=args), patch("sambapilot.cli.HostSetupProbe", side_effect=AssertionError("host")), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(["preparer-installation", *args])
            self.assertEqual(caught.exception.code, 2)


class PackageQueryTests(unittest.TestCase):
    def test_only_local_query_is_launched(self):
        result = Mock(returncode=0, stdout="samba 2:4.25.1-1\n", stderr="")
        with patch("sambapilot.setup.subprocess.run", return_value=result) as runner:
            package = query_package("samba", "/usr/bin/pacman")
        self.assertEqual(package.status, "installed")
        self.assertEqual(package.version, "2:4.25.1-1")
        args, kwargs = runner.call_args
        self.assertEqual(args[0], ("/usr/bin/pacman", "--query", "--", "samba"))
        self.assertFalse(kwargs["shell"])
        self.assertFalse(kwargs["check"])
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(kwargs["timeout"], 3)
        self.assertEqual(kwargs["env"], {"PATH": "/usr/bin:/usr/sbin", "LC_ALL": "C"})

    def test_explicit_not_found_is_distinct_from_query_failures(self):
        cases = ((1, "", "error: package 'samba' was not found\n", "missing"),
                 (1, "", "error: could not open database", "unknown"),
                 (1, "", "", "unknown"), (0, "unexpected output", "", "unknown"),
                 (0, "other 1.0", "", "unknown"), (0, "samba bad\x1b[2J", "", "unknown"),
                 (2, "", "error: package 'samba' was not found", "unknown"))
        for code, stdout, stderr, expected in cases:
            with self.subTest(code=code, stdout=stdout, stderr=stderr), \
                    patch("sambapilot.setup.subprocess.run", return_value=Mock(returncode=code, stdout=stdout, stderr=stderr)):
                self.assertEqual(query_package("samba", "/usr/bin/pacman").status, expected)

    def test_timeouts_and_permission_errors_remain_unknown(self):
        for error in (PermissionError(), subprocess.TimeoutExpired("pacman", 3)):
            with self.subTest(error=type(error)), patch("sambapilot.setup.subprocess.run", side_effect=error):
                self.assertEqual(query_package("samba", "/usr/bin/pacman").status, "unknown")

    def test_package_names_and_executable_are_closed_lists(self):
        for name, executable in (("bash", "/usr/bin/pacman"), ("samba;reboot", "/usr/bin/pacman"),
                                  ("samba", "/tmp/mise/pacman")):
            with self.subTest(name=name, executable=executable), self.assertRaises(ValueError):
                query_package(name, executable)

    def test_absent_system_pacman_is_never_launched(self):
        with patch.object(HostSetupProbe, "tool", return_value=None), \
                patch("subprocess.run", side_effect=AssertionError("process")):
            self.assertEqual(HostSetupProbe().package("samba").status, "unknown")


if __name__ == "__main__":
    unittest.main()
