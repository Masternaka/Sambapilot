import contextlib
from dataclasses import replace
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from sambapilot.cli import main
from sambapilot.inspection import inspect_content, read_configuration
from sambapilot.report_export import (PERSONAL_DATA_NOTICE, ReportExportError,
                                      prepare_report, save_report)


class ReportPreparationTests(unittest.TestCase):
    def setUp(self):
        self.report = inspect_content('[Documents]\npath = /srv/docs\nvalid users = alex +famille\n'
                                      '# hidden-comment-value\nvfs objects = hidden-option-value\n',
                                      '/chosen/smb.conf', 'file')
        self.date = datetime(2026, 11, 9, 17, 30, tzinfo=timezone.utc)

    def test_preparation_is_pure_and_includes_scope_personal_data_notice_and_uncertainties(self):
        with patch('pathlib.Path.open', side_effect=AssertionError('file')), \
                patch('subprocess.run', side_effect=AssertionError('process')):
            output = prepare_report(self.report, self.date)
        self.assertEqual(output.source_sha256, self.report.sha256)
        self.assertIn(PERSONAL_DATA_NOTICE, output.markdown)
        self.assertIn('/chosen/smb.conf', output.markdown)
        self.assertIn('alex', output.markdown)
        self.assertIn('famille', output.markdown)
        self.assertIn('Lecture seule déclarée : Inconnu', output.markdown)
        self.assertIn('Réglages incomplets', output.markdown)
        self.assertIn('2026-11-09T17:30:00+00:00', output.markdown)
        self.assertIn('vfs objects', output.markdown)
        self.assertNotIn('hidden-option-value', output.markdown)
        self.assertNotIn('hidden-comment-value', output.markdown)

    def test_untrusted_text_cannot_create_markdown_links_html_or_extra_headings(self):
        report = inspect_content('[<script>alert</script>]\npath = /srv/[photo](https://example.invalid)!\n',
                                 'source\n# fake heading', 'file')
        text = prepare_report(report, self.date).markdown
        self.assertNotIn('<script>', text)
        self.assertIn('&lt;script&gt;', text)
        self.assertNotIn('[photo](https://example.invalid)', text)
        self.assertNotIn('\n# fake heading', text)
        self.assertIn('\\[photo\\]', text)

    def test_blocked_inventory_omits_unreliable_rows_and_does_not_claim_no_shares(self):
        report = replace(self.report, status='blocked', issues=('Structure refusée',))
        text = prepare_report(report, self.date).markdown
        self.assertIn('Analyse bloquée', text)
        self.assertIn('Structure refusée', text)
        self.assertNotIn('### Documents', text)
        self.assertNotIn('0 déclaration', text)

    def test_demo_and_unknown_read_date_are_explicit_and_bad_modes_dates_are_refused(self):
        text = prepare_report(replace(self.report, mode='demo'), self.date).markdown
        self.assertIn('Démonstration — données fictives', text)
        self.assertIn('Date de lecture (UTC) : Inconnue', text)
        with self.assertRaises(ReportExportError):
            prepare_report(replace(self.report, mode='live'), self.date)
        with self.assertRaises(ReportExportError):
            prepare_report(self.report, datetime(2026, 11, 9))

    def test_read_timestamp_and_snapshot_survive_later_source_changes_without_reread(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'smb.conf'
            source.write_text('[Original]\npath = /srv/original\n', encoding='utf-8')
            snapshot = read_configuration(str(source))
            report = snapshot.inspect()
            self.assertEqual(report.read_at, snapshot.read_at)
            self.assertIsNotNone(datetime.fromisoformat(report.read_at).utcoffset())
            source.write_text('[Changed]\npath = /srv/changed\n', encoding='utf-8')
            before = source.read_bytes(), source.stat().st_mtime_ns
            with patch('pathlib.Path.open', side_effect=AssertionError('reread')):
                text = prepare_report(report, self.date).markdown
            self.assertIn(report.read_at, text)
            self.assertIn('### Original', text)
            self.assertNotIn('### Changed', text)
            self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns), before)


class ReportSaveTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='sambapilot-export-test-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.output = self.root / 'rapport.md'
        self.report = prepare_report(inspect_content('[Documents]\npath = /srv/docs\n', mode='demo'))

    def assert_no_temporary_files(self):
        self.assertEqual(list(self.root.glob('.sambapilot-report-*')), [])

    def test_file_is_complete_before_publication_private_and_utf8(self):
        original_link = os.link
        def publish(source, destination):
            self.assertFalse(self.output.exists())
            self.assertEqual(Path(source).read_bytes(), self.report.markdown.encode('utf-8'))
            original_link(source, destination)
        with patch('sambapilot.report_export.os.link', side_effect=publish):
            save_report(self.report, str(self.output))
        self.assertEqual(self.output.read_text(encoding='utf-8'), self.report.markdown)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o600)
        self.assert_no_temporary_files()

    def test_existing_file_is_not_changed(self):
        self.output.write_bytes(b'preserve personal report')
        before = self.output.read_bytes(), self.output.stat().st_mtime_ns
        with self.assertRaises(ReportExportError):
            save_report(self.report, str(self.output))
        self.assertEqual((self.output.read_bytes(), self.output.stat().st_mtime_ns), before)
        self.assert_no_temporary_files()

    def test_symlink_dangling_link_and_directory_are_not_replaced(self):
        victim = self.root / 'personal.txt'
        victim.write_bytes(b'private')
        for kind in ('symlink', 'dangling', 'directory'):
            with self.subTest(kind=kind):
                destination = self.root / (kind + '.md')
                if kind == 'directory':
                    destination.mkdir()
                else:
                    destination.symlink_to(victim if kind == 'symlink' else self.root / 'absent')
                with self.assertRaises(ReportExportError):
                    save_report(self.report, str(destination))
                self.assertTrue(destination.is_dir() if kind == 'directory' else destination.is_symlink())
                self.assertEqual(victim.read_bytes(), b'private')
                self.assertFalse((self.root / 'absent').exists())
        self.assert_no_temporary_files()

    def test_wrong_extension_and_absent_parent_do_not_create_directories(self):
        for output in (self.root / 'smb.conf', self.root / 'absent' / 'rapport.md'):
            with self.subTest(output=output), self.assertRaises(ReportExportError):
                save_report(self.report, str(output))
            self.assertFalse(output.exists())
        self.assertFalse((self.root / 'absent').exists())
        self.assert_no_temporary_files()

    def test_prepublication_failure_cleans_temporary_file_and_leaves_no_output(self):
        for target in ('os.fsync', 'os.link'):
            with self.subTest(target=target), patch('sambapilot.report_export.' + target, side_effect=OSError('fixture')):
                with self.assertRaises(ReportExportError):
                    save_report(self.report, str(self.output))
            self.assertFalse(self.output.exists())
            self.assert_no_temporary_files()

    def test_destination_created_during_export_wins_without_overwrite(self):
        original_link = os.link
        def race(source, destination):
            self.output.write_bytes(b'concurrent personal file')
            original_link(source, destination)
        with patch('sambapilot.report_export.os.link', side_effect=race), self.assertRaises(ReportExportError):
            save_report(self.report, str(self.output))
        self.assertEqual(self.output.read_bytes(), b'concurrent personal file')
        self.assert_no_temporary_files()


class ReportCliTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='sambapilot-export-cli-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'smb.conf'
        self.source.write_text('[Documents]\npath = /srv/docs\n', encoding='utf-8')

    def test_markdown_preview_creates_no_export_and_preserves_source(self):
        before = self.source.read_bytes(), self.source.stat().st_mtime_ns
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = main(['examiner-config', '--config', str(self.source), '--markdown'])
        self.assertEqual(code, 0)
        self.assertIn('# SambaPilot', output.getvalue())
        self.assertIn(PERSONAL_DATA_NOTICE, output.getvalue())
        self.assertEqual(list(self.root.iterdir()), [self.source])
        self.assertEqual((self.source.read_bytes(), self.source.stat().st_mtime_ns), before)

    def test_missing_acknowledgment_or_conflicting_formats_stop_before_reading(self):
        for args in (['--export', 'rapport.md'], ['--confirm-export'], ['--json', '--markdown'],
                     ['--json', '--export', 'rapport.md', '--confirm-export']):
            with self.subTest(args=args), patch('sambapilot.cli.inspect_file', side_effect=AssertionError('read')), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(['examiner-config', '--config', str(self.source), *args])
            self.assertEqual(caught.exception.code, 2)

    def test_explicit_export_and_second_attempt_refuses_overwrite(self):
        destination = self.root / 'rapport.md'
        args = ['examiner-config', '--config', str(self.source), '--export', str(destination), '--confirm-export']
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args), 0)
        before = destination.read_bytes(), destination.stat().st_mtime_ns
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(args)
        self.assertEqual(caught.exception.code, 2)
        self.assertEqual((destination.read_bytes(), destination.stat().st_mtime_ns), before)

    def test_blocked_report_can_be_saved_but_keeps_blocked_exit_status(self):
        self.source.write_text('[Docs]\n[Docs]\n', encoding='utf-8')
        destination = self.root / 'blocked.md'
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(['examiner-config', '--config', str(self.source), '--export', str(destination), '--confirm-export'])
        self.assertEqual(code, 2)
        self.assertIn('Analyse bloquée', destination.read_text(encoding='utf-8'))
