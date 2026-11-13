import contextlib
import io
import json
import subprocess
import unittest
from unittest.mock import Mock, patch

from sambapilot.cli import main
from sambapilot.demo import DemoProbe, SCENARIOS
from sambapilot.diagnostic import collect
from sambapilot.distributions import PROFILES, identify_profile
from sambapilot.setup import DemoSetupProbe, HostSetupProbe, collect_installation_plan, query_package


class DistributionTests(unittest.TestCase):
    def test_exact_identity_precedes_family_and_ambiguous_family_is_unknown(self):
        self.assertEqual(identify_profile("debian", "arch").key, "debian")
        self.assertEqual(identify_profile("derivative", "debian linux").key, "debian")
        self.assertIsNone(identify_profile("unknown", "arch debian"))
        self.assertIsNone(identify_profile("unknown", "rhel"))

    def test_all_demo_profiles_and_scenarios_never_consult_host(self):
        with patch("subprocess.run", side_effect=AssertionError("process")), \
                patch("pathlib.Path.open", side_effect=AssertionError("file")), \
                patch("pathlib.Path.stat", side_effect=AssertionError("stat")):
            for family, profile in PROFILES.items():
                for scenario in SCENARIOS:
                    with self.subTest(family=family, scenario=scenario):
                        plan = collect_installation_plan(DemoSetupProbe(scenario, family))
                        self.assertEqual(plan.diagnostic.environment.distribution_family, family)
                        self.assertEqual(plan.diagnostic.environment.samba_service, profile.services[0])
                        self.assertEqual(tuple(package.name for package in plan.packages), profile.packages)
                        self.assertFalse(plan.can_apply)
                        self.assertEqual(plan.status, "blocked" if scenario == "restricted" else "review")
                        self.assertEqual(plan.schema_version, 2)

    def test_debian_queries_only_its_service_names(self):
        probe = DemoProbe(distribution="debian")
        with patch.object(probe, "service", wraps=probe.service) as service:
            report = collect(probe)
        self.assertEqual([call.args[0] for call in service.call_args_list],
                         ["smbd.service", "nmbd.service", "ufw.service", "firewalld.service", "nftables.service"])
        self.assertNotIn("smb.service", [item.name for item in report.services])

    def test_missing_query_tool_prevents_all_package_processes_for_each_family(self):
        for family, profile in PROFILES.items():
            probe = DemoSetupProbe(distribution=family)
            original = probe.tool
            with self.subTest(family=family), \
                    patch.object(probe, "tool", side_effect=lambda name: None if name == profile.query_tool else original(name)), \
                    patch.object(probe, "package", side_effect=AssertionError("query")):
                plan = collect_installation_plan(probe)
                self.assertEqual(plan.status, "blocked")
                self.assertTrue(all(package.status == "unknown" for package in plan.packages))

    def test_host_profile_selects_query_tool_and_fixed_packages(self):
        for family, profile in PROFILES.items():
            probe = HostSetupProbe()
            with self.subTest(family=family), \
                    patch.object(probe, "tool", return_value="/usr/bin/" + profile.query_tool), \
                    patch("sambapilot.setup.query_package") as query:
                probe.package(profile.packages[-1], family)
                query.assert_called_once_with(profile.packages[-1], "/usr/bin/" + profile.query_tool)

    def test_cli_demonstrates_all_families_without_host(self):
        with patch("sambapilot.cli.HostProbe", side_effect=AssertionError("host")), \
                patch("sambapilot.cli.HostSetupProbe", side_effect=AssertionError("host")):
            for family in PROFILES:
                for command in ("diagnostic", "preparer-installation"):
                    with self.subTest(family=family, command=command), contextlib.redirect_stdout(io.StringIO()) as output:
                        self.assertEqual(main([command, "--demo", "--distribution", family, "--json"]), 0)
                        data = json.loads(output.getvalue())
                        environment = data.get("diagnostic", data)["environment"]
                        self.assertEqual(environment["distribution_family"], family)

    def test_distribution_cannot_override_real_host(self):
        for args in (["diagnostic"], ["preparer-installation", "--local"],
                     ["depannage", "--local", "--symptom", "denied"]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), \
                    patch("sambapilot.cli.HostProbe", side_effect=AssertionError("host")), \
                    self.assertRaises(SystemExit) as caught:
                main([*args, "--distribution", "debian"])
            self.assertEqual(caught.exception.code, 2)

    def test_fedora_reports_security_policy_as_unverified(self):
        report = collect(DemoProbe(distribution="fedora"))
        self.assertTrue(any("SELinux" in note and "ne sont pas consultés" in note for note in report.notes))


class PortablePackageQueryTests(unittest.TestCase):
    def query(self, executable, stdout="", stderr="", code=0):
        with patch("sambapilot.setup.subprocess.run", return_value=Mock(
                returncode=code, stdout=stdout, stderr=stderr)) as runner:
            result = query_package("samba", "/usr/bin/" + executable)
        self.assertFalse(runner.call_args.kwargs["shell"])
        self.assertEqual(runner.call_args.kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(runner.call_args.kwargs["timeout"], 3)
        return result, runner.call_args.args[0]

    def test_dpkg_installed_and_held_packages_are_detected(self):
        for wanted in ("install", "hold", "deinstall"):
            with self.subTest(wanted=wanted):
                package, command = self.query("dpkg-query", "samba\t" + wanted + " ok installed\t2:4.22.0+dfsg-1\n")
                self.assertEqual(package.status, "installed")
                self.assertEqual(package.version, "2:4.22.0+dfsg-1")
                self.assertEqual(command, ("/usr/bin/dpkg-query", "--show",
                                           "--showformat=${Package}\t${Status}\t${Version}\n", "--", "samba"))

    def test_dpkg_residual_configuration_is_not_an_installed_package(self):
        package, _command = self.query("dpkg-query", "samba\tdeinstall ok config-files\t1.0\n")
        self.assertEqual(package.status, "missing")
        package, _command = self.query("dpkg-query", "samba\tunknown ok not-installed\t\n")
        self.assertEqual(package.status, "missing")

    def test_dpkg_partial_and_broken_installs_remain_unknown(self):
        for status in ("install ok unpacked", "install ok half-configured", "install reinstreq installed"):
            with self.subTest(status=status):
                package, _ = self.query("dpkg-query", "samba\t" + status + "\t1.0\n")
                self.assertEqual(package.status, "unknown")

    def test_dpkg_explicit_absence_is_distinct_from_database_failure(self):
        package, _ = self.query("dpkg-query", stderr="dpkg-query: no packages found matching samba\n", code=1)
        self.assertEqual(package.status, "missing")
        package, _ = self.query("dpkg-query", stderr="dpkg-query: error: database unavailable", code=1)
        self.assertEqual(package.status, "unknown")

    def test_rpm_installed_version_and_query_command(self):
        package, command = self.query("rpm", "samba\t2:4.23.0-1.fc43\n")
        self.assertEqual(package.status, "installed")
        self.assertEqual(command, ("/usr/bin/rpm", "--query", "--queryformat",
                                   "%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\n", "--", "samba"))

    def test_rpm_explicit_absence_is_distinct_from_database_failure(self):
        package, _ = self.query("rpm", "package samba is not installed\n", code=1)
        self.assertEqual(package.status, "missing")
        package, _ = self.query("rpm", stderr="error: rpmdb failed", code=1)
        self.assertEqual(package.status, "unknown")

    def test_ambiguous_or_untrusted_responses_remain_unknown(self):
        for executable, text in (("rpm", "samba\t1.0\nsamba\t2.0"), ("rpm", "other\t1.0"),
                                  ("rpm", "samba\tbad\x1b[2J"), ("dpkg-query", "samba\tinstall ok installed\tbad\x1b[2J")):
            with self.subTest(executable=executable, text=text):
                self.assertEqual(self.query(executable, text)[0].status, "unknown")
        for executable in ("rpm", "dpkg-query"):
            self.assertEqual(self.query(executable, code=1)[0].status, "unknown")

    def test_cross_distribution_packages_and_shims_are_rejected(self):
        for name, executable in (("smbclient", "/usr/bin/rpm"), ("samba-client", "/usr/bin/dpkg-query"),
                                  ("samba;reboot", "/usr/bin/rpm"), ("samba", "/tmp/rpm")):
            with self.subTest(name=name, executable=executable), \
                    patch("subprocess.run", side_effect=AssertionError("process")), self.assertRaises(ValueError):
                query_package(name, executable)

    def test_portable_query_errors_remain_unknown(self):
        for executable in ("rpm", "dpkg-query"):
            for error in (PermissionError(), subprocess.TimeoutExpired(executable, 3)):
                with self.subTest(executable=executable, error=type(error)), \
                        patch("sambapilot.setup.subprocess.run", side_effect=error):
                    self.assertEqual(query_package("samba", "/usr/bin/" + executable).status, "unknown")
