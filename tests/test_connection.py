import contextlib
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sambapilot.cli import main
from sambapilot.connection import ConnectionError, format_connection, prepare_connection, validate_server
from sambapilot.demo import demo_configuration
from sambapilot.inspection import inspect_content, read_configuration


class ConnectionTests(unittest.TestCase):
    def setUp(self):
        self.report = inspect_content(demo_configuration(), 'Exemple fictif', 'demo')

    def test_windows_and_smb_addresses_refer_to_share_not_local_folder(self):
        card = prepare_connection(self.report, 'Famille', 'SERVEUR.local')
        guides = {guide.key: guide for guide in card.guides}
        self.assertEqual(guides['windows'].address, '\\\\serveur.local\\Famille')
        self.assertEqual(guides['macos'].address, 'smb://serveur.local/Famille')
        self.assertEqual(guides['linux'].address, guides['macos'].address)
        self.assertNotIn('/srv/', format_connection(card))
        self.assertEqual(card.source_sha256, self.report.sha256)
        self.assertIsNone(card.network_verified)
        self.assertFalse(card.can_apply)

    def test_unicode_and_spaces_are_encoded_as_a_single_uri_segment(self):
        report = inspect_content('[Été famille]\npath = /srv/photos\n', mode='demo')
        card = prepare_connection(report, 'Été famille', '192.0.2.10')
        self.assertEqual(card.guides[1].address, 'smb://192.0.2.10/%C3%89t%C3%A9%20famille')
        self.assertEqual(card.guides[0].address, '\\\\192.0.2.10\\Été famille')

    def test_server_normalization_keeps_explicit_dns_or_ipv4(self):
        for supplied, expected in ((' serveur.LOCAL ', 'serveur.local'), ('nas-1', 'nas-1'),
                                    ('nas.example.', 'nas.example.'), ('192.0.2.10', '192.0.2.10')):
            with self.subTest(supplied=supplied):
                self.assertEqual(validate_server(supplied), expected)

    def test_urls_credentials_ports_controls_ipv6_and_ambiguous_names_are_refused(self):
        for server in ('', ' ', 'smb://nas/Docs', 'user:private-secret@nas', '//nas', 'nas/Docs',
                       'nas\\Docs', 'nas:445', '::1', '[::1]', 'nas%20.local', 'nas?query',
                       'nas#fragment', 'nas\n', 'nas\x1b[2J', 'nas.local..', 'nas..local',
                       '-nas', 'nas-', 'a' * 64 + '.local', 'a.' * 128, '999.1.2.3',
                       '192.168.01.1', 'nas;reboot', '$(reboot)', 'réseau.local'):
            with self.subTest(server=server), self.assertRaises(ConnectionError) as caught:
                validate_server(server)
            self.assertNotIn('private-secret', str(caught.exception))

    def test_unknown_duplicate_and_special_shares_are_refused(self):
        for name in ('unknown', 'homes', 'printers', 'global'):
            with self.subTest(name=name), self.assertRaises(ConnectionError):
                prepare_connection(self.report, name, 'nas')
        duplicated = replace(self.report, shares=(self.report.shares[0], self.report.shares[0]))
        with self.assertRaises(ConnectionError):
            prepare_connection(duplicated, 'Famille', 'nas')

    def test_nonportable_share_names_are_refused_without_guessing(self):
        for name in ('Medias$', 'Medias.', 'A/B', 'A%U'):
            report = inspect_content('[' + name + ']\npath = /srv/docs\n', mode='demo')
            with self.subTest(name=name), self.assertRaises(ConnectionError):
                prepare_connection(report, name, 'nas')

    def test_case_insensitive_selection_preserves_declared_spelling(self):
        card = prepare_connection(self.report, 'famille', 'nas')
        self.assertEqual(card.share, 'Famille')

    def test_blocked_inventory_and_unspecified_sources_are_refused(self):
        for report in (replace(self.report, status='blocked'), replace(self.report, mode='provided')):
            with self.subTest(report=report), self.assertRaises(ConnectionError):
                prepare_connection(report, 'Famille', 'nas')

    def test_preparation_and_formatting_never_probe_host_network_or_processes(self):
        with patch('pathlib.Path.open', side_effect=AssertionError('file')), \
                patch('subprocess.run', side_effect=AssertionError('process')), \
                patch('socket.getaddrinfo', side_effect=AssertionError('DNS')):
            card = prepare_connection(self.report, 'Famille', 'nas.local')
            self.assertIn('Windows', format_connection(card))

    def test_hidden_and_readonly_flags_are_explanations_not_grants(self):
        report = inspect_content('[Docs]\npath = /srv/docs\nbrowseable = no\nread only = yes\n', mode='demo')
        card = prepare_connection(report, 'Docs', 'nas')
        self.assertTrue(any('masqué' in note for note in card.notes))
        self.assertTrue(any('Lecture seule' in note for note in card.notes))
        self.assertIsNone(card.network_verified)

    def test_incomplete_inventory_keeps_uncertainties_and_does_not_infer_permissions(self):
        report = inspect_content('[Docs]\nvfs objects = private-option\n', mode='demo')
        card = prepare_connection(report, 'Docs', 'nas')
        self.assertTrue(any('non interprétés' in note for note in card.notes))
        self.assertNotIn('private-option', format_connection(card))
        self.assertIsNone(card.network_verified)

    def test_source_read_date_and_bytes_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            content = b'\xef\xbb\xbf[Docs]\r\npath = /srv/docs\r\n'
            path.write_bytes(content)
            snapshot = read_configuration(str(path))
            card = prepare_connection(snapshot.inspect(), 'Docs', 'nas')
            self.assertEqual(card.read_at, snapshot.read_at)
            self.assertEqual(card.source_sha256, snapshot.sha256)
            self.assertEqual(card.source, str(path))
            self.assertEqual(path.read_bytes(), content)

    def test_terminal_does_not_render_control_sequences_from_source(self):
        report = replace(self.report, source='source\x1b[2J')
        self.assertNotIn('\x1b', format_connection(prepare_connection(report, 'Famille', 'nas')))


class ConnectionCliTests(unittest.TestCase):
    def test_demo_produces_text_or_json_without_host_or_network(self):
        with patch('sambapilot.cli.HostProbe', side_effect=AssertionError('host')), \
                patch('pathlib.Path.open', side_effect=AssertionError('file')), \
                patch('subprocess.run', side_effect=AssertionError('process')), \
                patch('socket.getaddrinfo', side_effect=AssertionError('DNS')):
            for extra in ([], ['--json']):
                with self.subTest(extra=extra), contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(['fiche-connexion', '--demo', '--share', 'Famille', '--server', 'nas.local', *extra]), 0)
                if extra:
                    data = json.loads(output.getvalue())
                    self.assertIsNone(data['network_verified'])
                    self.assertFalse(data['can_apply'])
                    self.assertEqual(data['mode'], 'demo')
                else:
                    self.assertIn('DÉMONSTRATION', output.getvalue())

    def test_file_source_is_explicit_and_never_modified(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            path.write_text('[Docs]\npath = /srv/docs\n', encoding='utf-8')
            before = path.read_bytes(), path.stat().st_mtime_ns
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(['fiche-connexion', '--config', str(path), '--share', 'Docs', '--server', '192.0.2.1', '--json']), 0)
            data = json.loads(output.getvalue())
            self.assertEqual(data['mode'], 'file')
            self.assertIsNotNone(data['read_at'])
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_source_choice_and_fields_are_required(self):
        for args in ([], ['--demo', '--config', '/unused'], ['--demo'], ['--demo', '--share', 'Famille']):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(['fiche-connexion', *args])
            self.assertEqual(caught.exception.code, 2)

    def test_bad_server_is_refused_before_file_read_without_echoing_credentials(self):
        with patch('sambapilot.cli.inspect_file', side_effect=AssertionError('file')), \
                contextlib.redirect_stderr(io.StringIO()) as error, self.assertRaises(SystemExit):
            main(['fiche-connexion', '--config', '/unused', '--share', 'Docs', '--server', 'user:private-secret@nas'])
        self.assertNotIn('private-secret', error.getvalue())
