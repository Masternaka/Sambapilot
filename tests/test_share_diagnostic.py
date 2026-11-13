import contextlib
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sambapilot.cli import main
from sambapilot.demo import demo_configuration
from sambapilot.inspection import inspect_content, read_configuration
from sambapilot.share_diagnostic import ShareDiagnosticError, format_share_diagnostic, prepare_share_diagnostic
from sambapilot.volumes import DemoVolumeProbe, collect_volume


class ShareDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.source = inspect_content(demo_configuration(), 'Exemple fictif', 'demo')

    def test_opening_is_pure_and_no_effective_access_is_inferred(self):
        with patch('pathlib.Path.open', side_effect=AssertionError('file')), \
                patch('subprocess.run', side_effect=AssertionError('process')), \
                patch('socket.getaddrinfo', side_effect=AssertionError('DNS')):
            report = prepare_share_diagnostic(self.source, 'famille')
            self.assertIn('Famille', format_share_diagnostic(report))
        self.assertEqual(report.share.name, 'Famille')
        self.assertIsNone(report.connection)
        self.assertIsNone(report.volume)
        self.assertIsNone(report.effective_read)
        self.assertIsNone(report.effective_write)
        self.assertIsNone(report.network_verified)
        self.assertFalse(report.can_apply)

    def test_selected_share_and_source_are_preserved(self):
        report = prepare_share_diagnostic(self.source, 'Medias', 'readonly', 'nas.local')
        self.assertTrue(report.share.read_only)
        self.assertEqual(report.source_sha256, self.source.sha256)
        self.assertEqual(report.connection.share, 'Medias')
        self.assertEqual(report.connection.guides[1].address, 'smb://nas.local/Medias')
        self.assertTrue(any(item.key == 'declared-write' and item.status == 'attention' for item in report.findings))

    def test_hidden_share_affects_only_visibility_guidance(self):
        source = inspect_content('[Docs]\npath = /srv/docs\nbrowseable = no\n', mode='demo')
        report = prepare_share_diagnostic(source, 'Docs', 'invisible')
        self.assertTrue(any(item.key == 'visibility' and item.status == 'attention' for item in report.findings))
        self.assertIsNone(report.effective_read)

    def test_unknown_or_unsupported_settings_are_not_replaced(self):
        source = inspect_content('[Docs]\nvfs objects = private-option\n', mode='demo')
        report = prepare_share_diagnostic(source, 'Docs', 'readonly')
        self.assertIsNone(report.share.path)
        self.assertIsNone(report.share.read_only)
        self.assertTrue(any(item.key == 'declaration' and item.status == 'attention' for item in report.findings))
        self.assertNotIn('private-option', json.dumps(report.to_dict()))

    def test_nonportable_name_does_not_block_diagnostic_when_connection_is_unavailable(self):
        source = inspect_content('[Medias$]\npath = /srv/docs\n', mode='demo')
        report = prepare_share_diagnostic(source, 'Medias$', server='nas.local')
        self.assertEqual(report.share.name, 'Medias$')
        self.assertIsNone(report.connection)
        self.assertIn('portable', report.connection_notice)

    def test_invalid_server_leaves_no_old_address_or_secret(self):
        good = prepare_share_diagnostic(self.source, 'Famille', server='nas.local')
        bad = prepare_share_diagnostic(self.source, 'Famille', server='user:private-secret@nas')
        self.assertIsNotNone(good.connection)
        self.assertIsNone(bad.connection)
        self.assertNotIn('private-secret', format_share_diagnostic(bad))

    def test_only_matching_volume_path_and_source_mode_can_be_attached(self):
        volume = collect_volume('/srv/partages/famille', '/srv/partages', DemoVolumeProbe('mounted', '/srv/partages'))
        result = prepare_share_diagnostic(self.source, 'Famille', volume=volume)
        self.assertIs(result.volume, volume)
        self.assertIsNone(result.effective_write)
        for invalid in (replace(volume, path='/srv/autre'), replace(volume, mode='live')):
            with self.subTest(invalid=invalid), self.assertRaises(ShareDiagnosticError):
                prepare_share_diagnostic(self.source, 'Famille', volume=invalid)
        with self.assertRaises(ShareDiagnosticError):
            prepare_share_diagnostic(replace(self.source, mode='file'), 'Famille', volume=volume)

    def test_local_volume_does_not_describe_remote_server_or_prove_rights(self):
        volume = replace(collect_volume('/srv/partages/famille', '/srv/partages',
                                        DemoVolumeProbe('readonly', '/srv/partages')), mode='live')
        result = prepare_share_diagnostic(replace(self.source, mode='file'), 'Famille', 'readonly', 'remote.example.invalid', volume)
        self.assertIsNone(result.effective_write)
        self.assertTrue(any('serveur distant' in item.observation for item in result.findings if item.key == 'volume'))

    def test_missing_or_duplicate_share_blocked_report_and_bad_symptom_are_refused(self):
        for source, name, symptom in ((self.source, 'unknown', 'denied'), (self.source, 'homes', 'denied'),
                                      (replace(self.source, status='blocked'), 'Famille', 'denied'),
                                      (replace(self.source, shares=(self.source.shares[0], self.source.shares[0])), 'Famille', 'denied'),
                                      (self.source, 'Famille', 'restart')):
            with self.subTest(name=name, symptom=symptom), self.assertRaises(ShareDiagnosticError):
                prepare_share_diagnostic(source, name, symptom)

    def test_read_date_and_configuration_bytes_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            raw = b'\xef\xbb\xbf[Docs]\r\npath = /srv/docs\r\n'
            path.write_bytes(raw)
            snapshot = read_configuration(str(path))
            report = prepare_share_diagnostic(snapshot.inspect(), 'Docs')
            self.assertEqual(report.read_at, snapshot.read_at)
            self.assertEqual(report.source_sha256, snapshot.sha256)
            self.assertEqual(path.read_bytes(), raw)

    def test_terminal_source_controls_are_filtered(self):
        source = replace(self.source, source='source\x1b[2J')
        self.assertNotIn('\x1b', format_share_diagnostic(prepare_share_diagnostic(source, 'Famille')))


class ShareDiagnosticCliTests(unittest.TestCase):
    def test_demo_aggregates_without_host_reads_or_network(self):
        with patch('pathlib.Path.open', side_effect=AssertionError('file')), \
                patch('sambapilot.cli.HostVolumeProbe', side_effect=AssertionError('host')), \
                patch('subprocess.run', side_effect=AssertionError('process')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['diagnostic-partage', '--demo', '--share', 'Famille', '--symptom', 'readonly',
                                   '--server', 'nas.local', '--demo-volume', 'unmounted', '--mountpoint', '/srv/partages', '--json']), 0)
        report = json.loads(output.getvalue())
        self.assertFalse(report['volume']['expected_mounted'])
        self.assertIsNone(report['effective_write'])
        self.assertEqual(report['connection']['share'], 'Famille')

    def test_file_diagnostic_does_not_consult_host_without_explicit_volume_flag(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            path.write_text('[Docs]\npath = /mnt/docs\n', encoding='utf-8')
            before = path.read_bytes(), path.stat().st_mtime_ns
            with patch('sambapilot.cli.HostVolumeProbe', side_effect=AssertionError('host')), \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(['diagnostic-partage', '--config', str(path), '--share', 'Docs', '--json']), 0)
            self.assertIsNone(json.loads(output.getvalue())['volume'])
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_source_volume_scope_and_mountpoint_flags_are_required(self):
        cases = (['--share', 'Docs'], ['--demo', '--config', '/unused', '--share', 'Docs'],
                 ['--demo', '--share', 'Famille', '--local-volume', '--mountpoint', '/srv'],
                 ['--config', '/unused', '--share', 'Docs', '--demo-volume', 'mounted', '--mountpoint', '/mnt'],
                 ['--demo', '--share', 'Famille', '--mountpoint', '/srv'],
                 ['--demo', '--share', 'Famille', '--demo-volume', 'mounted'])
        for args in cases:
            with self.subTest(args=args), patch('sambapilot.cli.inspect_file', side_effect=AssertionError('file')), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(['diagnostic-partage', *args])

    def test_changed_file_during_volume_collection_is_refused(self):
        source = replace(inspect_content('[Docs]\npath = /mnt/docs\n', mode='demo'), mode='file')
        volume = replace(collect_volume('/mnt/docs', '/mnt', DemoVolumeProbe('mounted', '/mnt')), mode='live')
        with patch('sambapilot.cli.inspect_file', side_effect=[source, replace(source, sha256='changed')]), \
                patch('sambapilot.cli.HostVolumeProbe'), patch('sambapilot.cli.collect_volume', return_value=volume), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(['diagnostic-partage', '--config', '/fictif', '--share', 'Docs', '--local-volume', '--mountpoint', '/mnt'])

    def test_missing_declared_path_never_creates_local_probe(self):
        source = replace(inspect_content('[Docs]\n', mode='demo'), mode='file')
        with patch('sambapilot.cli.inspect_file', return_value=source), \
                patch('sambapilot.cli.HostVolumeProbe', side_effect=AssertionError('host')), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(['diagnostic-partage', '--config', '/fictif', '--share', 'Docs', '--local-volume', '--mountpoint', '/mnt'])

    def test_credentials_are_refused_before_source_read_without_echo(self):
        with patch('sambapilot.cli.inspect_file', side_effect=AssertionError('file')), \
                contextlib.redirect_stderr(io.StringIO()) as error, self.assertRaises(SystemExit):
            main(['diagnostic-partage', '--config', '/unused', '--share', 'Docs', '--server', 'user:private-secret@nas'])
        self.assertNotIn('private-secret', error.getvalue())
