import contextlib
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from sambapilot.cli import main
from sambapilot.demo import demo_configuration
from sambapilot.inspection import (MAX_CONFIG_BYTES, InspectionError, format_inspection,
                                   inspect_content, inspect_file)


class InspectionTests(unittest.TestCase):
    def test_demo_declarations_are_read_without_effective_rights(self):
        report = inspect_content(demo_configuration())
        self.assertEqual(report.status, "inspected")
        self.assertEqual(len(report.shares), 3)
        self.assertEqual(report.special_sections, ("global",))
        row = report.shares[0]
        self.assertEqual(row.name, "Famille")
        self.assertEqual(row.unix_groups, ("famille",))
        self.assertIs(row.read_only, False)
        self.assertIs(row.guest_ok, False)
        self.assertEqual(row.access_list_status, "declared")

    def test_missing_local_values_do_not_inherit_globals_or_defaults(self):
        report = inspect_content("[global]\nread only = no\nguest ok = yes\n[Photos]\npath = /srv/photos\n")
        row = report.shares[0]
        self.assertIsNone(row.read_only)
        self.assertIsNone(row.guest_ok)
        self.assertIsNone(row.browseable)
        self.assertEqual(row.access_list_status, "not-declared")

    def test_synonyms_are_supported_with_correct_inversion(self):
        for key in ("writable", "writeable", "write ok"):
            for raw, expected in (("yes", False), ("No", True), ("1", False), ("false", True)):
                with self.subTest(key=key, raw=raw):
                    content = "[Files]\npath = /files\n" + key + " = " + raw + "\nbrowsable = 0\npublic = TRUE\n"
                    row = inspect_content(content).shares[0]
                    self.assertIs(row.read_only, expected)
                    self.assertIs(row.browseable, False)
                    self.assertIs(row.guest_ok, True)

    def test_alias_collisions_remain_unknown(self):
        row = inspect_content("[Files]\npath = /one\npath = /two\nread only = yes\nwritable = yes\n").shares[0]
        self.assertIsNone(row.path)
        self.assertIsNone(row.read_only)
        self.assertTrue(any("synonymes" in issue for issue in row.issues))

    def test_invalid_boolean_is_unknown_without_echoing_value(self):
        row = inspect_content("[Files]\npath = /files\nread only = invalid-secret\n").shares[0]
        self.assertIsNone(row.read_only)
        self.assertNotIn("invalid-secret", json.dumps(asdict(row)))
        self.assertTrue(any("booléenne" in issue for issue in row.issues))

    def test_advanced_option_names_are_reported_but_values_are_not(self):
        content = "[Files]\npath = /files\npassword = SECRET_VALUE\nforce user = private_admin\n"
        report = inspect_content(content)
        row = report.shares[0]
        self.assertEqual(row.unparsed_options, ("force user", "password"))
        output = json.dumps(report.to_dict()) + format_inspection(report)
        self.assertNotIn("SECRET_VALUE", output)
        self.assertNotIn("private_admin", output)

    def test_unix_groups_and_unresolved_netgroups_are_distinct(self):
        row = inspect_content("[Files]\npath = /files\nvalid users = alex, +famille @reseau DOMAIN\\lea %U\n").shares[0]
        self.assertEqual(row.users, ("alex",))
        self.assertEqual(row.unix_groups, ("famille",))
        self.assertEqual(row.unresolved_principals, ("@reseau", "DOMAIN\\lea", "%U"))
        self.assertEqual(row.access_list_status, "partial")

    def test_empty_access_list_is_distinct_from_not_declared(self):
        row = inspect_content("[Files]\npath = /files\nvalid users =\n").shares[0]
        self.assertEqual(row.access_list_status, "empty")
        self.assertEqual(row.users, ())

    def test_repeated_access_list_is_not_merged(self):
        row = inspect_content("[Files]\npath = /files\nvalid users = alex\nvalid users = lea\n").shares[0]
        self.assertEqual(row.access_list_status, "unknown")
        self.assertEqual(row.users, ())

    def test_variables_are_not_expanded_and_missing_path_is_not_invented(self):
        report = inspect_content("[Personal]\npath = /srv/%U\n[Other]\nread only = yes\n")
        self.assertEqual(report.shares[0].path, "/srv/%U")
        self.assertTrue(any("substitution" in issue for issue in report.shares[0].issues))
        self.assertIsNone(report.shares[1].path)

    def test_special_sections_are_not_expanded_into_fictitious_shares(self):
        report = inspect_content("[global]\nworkgroup = MAISON\n[homes]\npath = /home/%U\n[printers]\nprintable = yes\n")
        self.assertEqual(report.shares, ())
        self.assertEqual(report.special_sections, ("global", "homes", "printers"))
        self.assertEqual(len(report.issues), 2)

    def test_indirect_or_ambiguous_source_is_blocked_not_reported_empty(self):
        for content in ("[global]\ninclude = /private/other.conf\n[Local]\npath = /local\n",
                        "[Local]\npath = /local\ncopy = Other\n", "[A]\npath = /a\n[a]\npath = /b\n",
                        "[A]\npath = /srv/\\\ncontinued\n", "[Broken\n", "[A]\npath = /a\x1b[2J"):
            with self.subTest(content=content):
                report = inspect_content(content)
                self.assertEqual(report.status, "blocked")
                self.assertEqual(report.shares, ())
                self.assertIn("ne signifie pas", format_inspection(report))

    def test_empty_file_is_a_valid_empty_local_inventory(self):
        report = inspect_content("")
        self.assertEqual(report.status, "inspected")
        self.assertEqual(report.shares, ())

    def test_case_and_crlf_are_supported(self):
        row = inspect_content("[Photos été]\r\n PaTh = /srv/Photos été\r\n READ ONLY = True\r\n").shares[0]
        self.assertEqual(row.path, "/srv/Photos été")
        self.assertIs(row.read_only, True)

    def test_report_sanitizes_filename_controls(self):
        report = inspect_content("", source="file\x1b[2J")
        self.assertNotIn("\x1b", format_inspection(report))


class FileInspectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "smb.conf"
        self.path.write_text(demo_configuration(), encoding="utf-8")

    def test_file_is_read_without_write_flags_or_process(self):
        before = self.path.read_bytes()
        metadata = self.path.stat()
        with patch("subprocess.run", side_effect=AssertionError("process")), \
                patch("sambapilot.inspection.os.open", wraps=os.open) as opener:
            report = inspect_file(str(self.path))
        self.assertEqual(report.mode, "file")
        flags = opener.call_args.args[1]
        self.assertFalse(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mtime_ns, metadata.st_mtime_ns)

    def test_utf8_bom_does_not_change_fingerprint_of_original_bytes(self):
        import hashlib
        content = b"\xef\xbb\xbf" + demo_configuration().encode("utf-8")
        self.path.write_bytes(content)
        report = inspect_file(str(self.path))
        self.assertEqual(len(report.shares), 3)
        self.assertEqual(report.sha256, hashlib.sha256(content).hexdigest())

    def test_invalid_utf8_is_refused_without_replacement_characters(self):
        self.path.write_bytes(b"[Files]\npath = /srv/\xff\n")
        with self.assertRaises(InspectionError):
            inspect_file(str(self.path))

    def test_oversized_file_is_refused(self):
        self.path.write_bytes(b"#" * (MAX_CONFIG_BYTES + 1))
        with self.assertRaises(InspectionError):
            inspect_file(str(self.path))

    def test_special_files_and_symlinks_are_refused_before_opening(self):
        link = self.path.parent / "linked.conf"
        link.symlink_to(self.path)
        fifo = self.path.parent / "fifo.conf"
        os.mkfifo(fifo)
        for path in (link, fifo, self.path.parent):
            with self.subTest(path=path), patch("sambapilot.inspection.os.open", side_effect=AssertionError("open")), \
                    self.assertRaises(InspectionError):
                inspect_file(str(path))

    def test_missing_denied_and_invalid_paths_are_handled(self):
        for name in (str(self.path.parent / "missing"), "", "bad\x00name"):
            with self.subTest(name=name), self.assertRaises(InspectionError):
                inspect_file(name)
        with patch("sambapilot.inspection.os.open", side_effect=PermissionError()), self.assertRaises(InspectionError):
            inspect_file(str(self.path))

    def test_changed_file_during_read_is_refused(self):
        before = self.path.stat()
        changed = SimpleNamespace(st_dev=before.st_dev, st_ino=before.st_ino, st_size=before.st_size,
                                  st_mtime_ns=before.st_mtime_ns + 1, st_ctime_ns=before.st_ctime_ns)
        with patch("sambapilot.inspection.os.fstat", side_effect=[before, changed]), self.assertRaises(InspectionError):
            inspect_file(str(self.path))

    def test_include_path_is_never_opened(self):
        self.path.write_text("[global]\ninclude = /DO_NOT_OPEN.conf\n", encoding="utf-8")
        with patch("sambapilot.inspection.os.open", wraps=os.open) as opener:
            report = inspect_file(str(self.path))
        self.assertEqual(opener.call_count, 1)
        self.assertEqual(opener.call_args.args[0], self.path)
        self.assertEqual(report.status, "blocked")

    def test_cli_requires_explicit_path_and_returns_json(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["examiner-config", "--config", str(self.path), "--json"]), 0)
        self.assertEqual(json.loads(output.getvalue())["mode"], "file")
        with patch("sambapilot.cli.inspect_file", side_effect=AssertionError("read")), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["examiner-config"])
        self.assertEqual(caught.exception.code, 2)

    def test_cli_errors_and_blocked_configuration_have_nonzero_exit(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["examiner-config", "--config", str(self.path.parent / "missing")])
        self.assertEqual(caught.exception.code, 2)
        self.path.write_text("[global]\ninclude = /DO_NOT_OPEN.conf\n", encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["examiner-config", "--config", str(self.path)]), 2)
        self.assertIn("Analyse bloquée", output.getvalue())


if __name__ == "__main__":
    unittest.main()
