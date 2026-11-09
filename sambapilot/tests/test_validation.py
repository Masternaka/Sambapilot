import contextlib
from dataclasses import replace
import io
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from sambapilot.cli import main
from sambapilot.demo import demo_configuration
from sambapilot.file_planning import FilePlanSession
from sambapilot.planning import ShareDraft, digest, prepare_plan
from sambapilot.validation import ValidationResult, format_validation, validate_plan


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.draft = ShareDraft("Documents", "/srv/documents", ("alex",))
        self.plan = prepare_plan(demo_configuration(), "create", "Documents", self.draft, mode="demo")
        self.platform = patch("sambapilot.validation.platform.system", return_value="Linux")
        self.platform.start()
        self.addCleanup(self.platform.stop)
        self.tool = patch("sambapilot.validation.HostProbe.tool", return_value="/usr/bin/testparm")
        self.tool.start()
        self.addCleanup(self.tool.stop)

    def test_exact_candidate_is_private_and_passed_without_shell_or_stdin(self):
        paths = []

        def run(command, **kwargs):
            candidate = Path(command[-1])
            paths.append(candidate)
            self.assertEqual(candidate.read_bytes(), self.plan.candidate.encode("utf-8"))
            self.assertEqual(stat.S_IMODE(candidate.stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(candidate.parent.stat().st_mode), 0o700)
            self.assertEqual(command[:-1], ("/usr/bin/testparm", "--suppress-prompt", "--debuglevel=0"))
            self.assertFalse(kwargs["shell"])
            self.assertFalse(kwargs["check"])
            self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
            self.assertEqual(kwargs["stdout"], subprocess.DEVNULL)
            self.assertEqual(kwargs["stderr"], subprocess.PIPE)
            self.assertEqual(kwargs["timeout"], 5)
            self.assertEqual(kwargs["cwd"], str(candidate.parent))
            self.assertEqual(kwargs["env"], {"PATH": "/usr/bin:/usr/sbin", "LC_ALL": "C"})
            return Mock(returncode=0, stderr=b"WARNING: exemple\n")

        with patch("sambapilot.validation.subprocess.run", side_effect=run):
            result = validate_plan(self.plan)
        self.assertEqual(result.status, "accepted")
        self.assertEqual(result.candidate_sha256, self.plan.candidate_sha256)
        self.assertIn("WARNING", result.diagnostics)
        self.assertFalse(result.can_apply)
        self.assertTrue(all(not path.parent.exists() for path in paths))

    def test_return_codes_distinguish_rejection_and_unexpected_failure(self):
        for code, status in ((1, "rejected"), (2, "error"), (-9, "error")):
            with self.subTest(code=code), patch("sambapilot.validation.subprocess.run",
                                                return_value=Mock(returncode=code, stderr=b"exemple")):
                result = validate_plan(self.plan)
                self.assertEqual(result.status, status)
                self.assertEqual(result.returncode, code)
                self.assertFalse(result.can_apply)

    def test_timeout_and_execution_error_cleanup_temporary_copy(self):
        for failure, status in ((subprocess.TimeoutExpired("testparm", 5, stderr=b"pending"), "timeout"),
                                (PermissionError("denied"), "error")):
            paths = []

            def run(command, **_kwargs):
                paths.append(Path(command[-1]).parent)
                raise failure

            with self.subTest(status=status), patch("sambapilot.validation.subprocess.run", side_effect=run):
                result = validate_plan(self.plan)
            self.assertEqual(result.status, status)
            self.assertTrue(all(not path.exists() for path in paths))

    def test_temporary_creation_failure_does_not_launch_process(self):
        with patch("sambapilot.validation.tempfile.TemporaryDirectory", side_effect=OSError()), \
                patch("subprocess.run", side_effect=AssertionError("process")):
            self.assertEqual(validate_plan(self.plan).status, "error")

    def test_missing_tool_never_installs_or_creates_files(self):
        with patch("sambapilot.validation.HostProbe.tool", return_value=None), \
                patch("subprocess.run", side_effect=AssertionError("process")), \
                patch("tempfile.TemporaryDirectory", side_effect=AssertionError("write")):
            result = validate_plan(self.plan)
        self.assertEqual(result.status, "unavailable")
        self.assertIn("Aucune installation", result.message)

    def test_non_linux_never_probes_or_creates_files(self):
        with patch("sambapilot.validation.platform.system", return_value="Darwin"), \
                patch("sambapilot.validation.HostProbe.tool", side_effect=AssertionError("tool")), \
                patch("tempfile.TemporaryDirectory", side_effect=AssertionError("write")):
            self.assertEqual(validate_plan(self.plan).status, "unavailable")

    def test_tampered_candidate_is_not_sent_to_samba(self):
        with patch("subprocess.run", side_effect=AssertionError("process")):
            result = validate_plan(replace(self.plan, candidate=self.plan.candidate + "# tampered\n"))
        self.assertEqual(result.status, "unsupported")

    def test_external_configs_scripts_backends_and_special_shares_are_refused(self):
        for content in ("[global]\ninclude = /private/other\n", "[global]\nconfig backend = registry\n",
                        "[global]\nlog file = /private/log\n", "[global]\nsecurity = ads\n",
                        "[global]\nserver role = active directory domain controller\n",
                        "[Files]\npath = /files\npreexec = touch /private/unwanted\n",
                        "[Files]\npath = /files\nvfs objects = fruit\n", "[homes]\npath = /home/%U\n",
                        "[Files]\npath = /files\nvalid users = @netgroup\n",
                        "[global]\nworkgroup = FIRST\nworkgroup = SECOND\n"):
            plan = replace(self.plan, candidate=content, candidate_sha256=digest(content))
            with self.subTest(content=content), \
                    patch("subprocess.run", side_effect=AssertionError("process")), \
                    patch("tempfile.TemporaryDirectory", side_effect=AssertionError("write")):
                self.assertEqual(validate_plan(plan).status, "unsupported")

    def test_oversized_candidate_is_refused_before_creation(self):
        content = "#" * (1024 * 1024 + 1)
        plan = replace(self.plan, candidate=content, candidate_sha256=digest(content))
        with patch("tempfile.TemporaryDirectory", side_effect=AssertionError("write")):
            self.assertEqual(validate_plan(plan).status, "unsupported")

    def test_diagnostics_are_bounded_sanitized_and_do_not_reveal_temp_path(self):
        def run(command, **_kwargs):
            raw = b"x" * 10000 + str(Path(command[-1]).parent).encode() + b"\x1b[2J\xff"
            return Mock(returncode=1, stderr=raw)

        with patch("sambapilot.validation.subprocess.run", side_effect=run):
            result = validate_plan(self.plan)
        self.assertLessEqual(len(result.diagnostics), 8192)
        self.assertIn("<temporaire>", result.diagnostics)
        self.assertNotIn("\x1b", result.diagnostics)
        self.assertNotIn("sambapilot-validation-", result.diagnostics)

    def test_bom_is_preserved_in_actual_candidate_file(self):
        content = "\ufeff" + self.plan.candidate
        plan = replace(self.plan, candidate=content, candidate_sha256=digest(content))

        def run(command, **_kwargs):
            self.assertTrue(Path(command[-1]).read_bytes().startswith(b"\xef\xbb\xbf"))
            return Mock(returncode=1, stderr=b"rejected by fixture")

        with patch("sambapilot.validation.subprocess.run", side_effect=run):
            self.assertEqual(validate_plan(plan).status, "rejected")

    def test_file_source_changed_before_validation_never_launches_testparm(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "smb.conf"
            path.write_text(demo_configuration(), encoding="utf-8")
            plan = FilePlanSession.open(str(path)).preview("create", "Documents", self.draft)
            path.write_text(demo_configuration() + "# modified\n", encoding="utf-8")
            with patch("subprocess.run", side_effect=AssertionError("process")):
                self.assertEqual(validate_plan(plan).status, "stale")

    def test_file_source_changed_during_validation_discards_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "smb.conf"
            path.write_text(demo_configuration(), encoding="utf-8")
            plan = FilePlanSession.open(str(path)).preview("create", "Documents", self.draft)

            def run(*_args, **_kwargs):
                path.write_text(demo_configuration() + "# changed\n", encoding="utf-8")
                return Mock(returncode=0, stderr=b"")

            with patch("sambapilot.validation.subprocess.run", side_effect=run):
                result = validate_plan(plan)
            self.assertEqual(result.status, "stale")
            self.assertFalse(result.can_apply)

    def test_missing_source_and_missing_file_path_are_stale(self):
        with patch("subprocess.run", side_effect=AssertionError("process")):
            for source in (None, "/unavailable-sambapilot-test.conf"):
                with self.subTest(source=source):
                    self.assertEqual(validate_plan(replace(self.plan, mode="file", source=source)).status, "stale")

    def test_validating_does_not_change_a_real_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "smb.conf"
            path.write_text(demo_configuration(), encoding="utf-8")
            before = path.read_bytes(), path.stat().st_mtime_ns
            plan = FilePlanSession.open(str(path)).preview("create", "Documents", self.draft)
            with patch("sambapilot.validation.subprocess.run", return_value=Mock(returncode=0, stderr=b"")):
                self.assertEqual(validate_plan(plan).status, "accepted")
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_cli_preview_does_not_validate_implicitly(self):
        with patch("sambapilot.cli.validate_plan", side_effect=AssertionError("validation")), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["plan-partage", "--demo", "--action", "remove", "--name", "Medias"]), 0)

    def test_cli_validation_preserves_plan_json_and_uses_failure_exit_code(self):
        for status, expected in (("accepted", 0), ("rejected", 4), ("unavailable", 4), ("stale", 4)):
            result = ValidationResult(status, self.plan.candidate_sha256, "Fixture de validation")
            with self.subTest(status=status), patch("sambapilot.cli.validate_plan", return_value=result), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                code = main(["plan-partage", "--demo", "--action", "remove", "--name", "Medias", "--validate", "--json"])
            self.assertEqual(code, expected)
            report = json.loads(output.getvalue())
            self.assertEqual(report["mode"], "demo")
            self.assertEqual(report["validation"]["status"], status)
            self.assertFalse(report["can_apply"])

    def test_cli_human_validation_is_separate_from_preview(self):
        result = ValidationResult("unavailable", self.plan.candidate_sha256, "Outil absent")
        with patch("sambapilot.cli.validate_plan", return_value=result), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["plan-partage", "--demo", "--action", "remove", "--name", "Medias", "--validate"]), 4)
        self.assertIn("Aperçu de partage", output.getvalue())
        self.assertIn("Outil absent", output.getvalue())
        self.assertIn("Empreinte du candidat", format_validation(result))


if __name__ == "__main__":
    unittest.main()
