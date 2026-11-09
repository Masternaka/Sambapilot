from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sambapilot.inspection import inspect_content, read_configuration
from sambapilot.presentation import DeclaredSharesView, declared_share_details


class DeclaredSharesTests(unittest.TestCase):
    def view(self, content):
        return DeclaredSharesView(inspect_content(content, '/chosen/smb.conf', 'file'))

    def test_explicit_settings_are_displayed_without_inventing_effective_access(self):
        view = self.view('[Docs]\npath = /srv/docs\nread only = yes\nbrowseable = no\n'
                         'guest ok = no\nvalid users = alex +famille\n')
        details = declared_share_details(view.shares[0])
        self.assertIn('Chemin déclaré : /srv/docs', details)
        self.assertIn('Lecture seule déclarée : Oui', details)
        self.assertIn('Visibilité déclarée : Non', details)
        self.assertIn('Utilisateurs reconnus : alex', details)
        self.assertIn('Groupes UNIX reconnus : famille', details)
        self.assertIn('ACL et accès réseau : inconnus', details)
        self.assertIn('Aucun accès effectif vérifié', view.summary)

    def test_global_settings_and_missing_values_remain_unknown(self):
        view = self.view('[global]\nread only = no\nvalid users = alex\n[Docs]\n')
        share = view.shares[0]
        self.assertIsNone(share.read_only)
        self.assertEqual(share.users, ())
        details = declared_share_details(share)
        self.assertIn('Chemin déclaré : Inconnu', details)
        self.assertIn('Lecture seule déclarée : Inconnu', details)
        self.assertIn('Visibilité déclarée : Inconnu', details)
        self.assertIn('Non déclarée localement', details)

    def test_empty_access_list_is_distinct_from_absent_and_ambiguous_lists(self):
        cases = (('', 'Non déclarée localement'), ('valid users =\n', 'Explicitement vide'),
                 ('valid users = alex\nvalid users = lea\n', 'Inconnue ou ambiguë'))
        for setting, expected in cases:
            with self.subTest(setting=setting):
                self.assertIn(expected, declared_share_details(self.view('[Docs]\n' + setting).shares[0]))

    def test_partial_identities_and_advanced_option_names_are_explicit_without_raw_values(self):
        view = self.view('[Docs]\npath = /srv/%U\nvalid users = alex @netgroup\nvfs objects = private-option-value\n')
        details = declared_share_details(view.shares[0])
        self.assertIn('Partiellement reconnue', details)
        self.assertIn('@netgroup', details)
        self.assertIn('vfs objects', details)
        self.assertNotIn('private-option-value', details)
        self.assertIn('substitution', details)

    def test_blocked_inventory_is_not_presented_as_a_server_with_no_shares(self):
        report = self.view('[Docs]\npath = /srv/docs\n').report
        view = DeclaredSharesView(replace(report, status='blocked', issues=('Analyse refusée',)))
        self.assertEqual(view.shares, ())
        self.assertIn('Analyse bloquée', view.summary)
        self.assertNotIn('Aucune déclaration', view.summary)
        self.assertEqual(view.report.issues, ('Analyse refusée',))

    def test_special_sections_do_not_create_ordinary_shares(self):
        view = self.view('[global]\nworkgroup = HOME\n[homes]\n[printers]\n')
        self.assertEqual(view.shares, ())
        self.assertEqual(view.report.special_sections, ('global', 'homes', 'printers'))
        self.assertIn('Aucune déclaration locale ordinaire', view.summary)
        self.assertIn('ne prouve pas', view.summary)

    def test_demo_cannot_silently_become_a_file_report(self):
        with self.assertRaises(ValueError):
            DeclaredSharesView(inspect_content('[Docs]\n', mode='demo'))

    def test_file_snapshot_is_presented_without_new_io_and_source_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            original = b'\xef\xbb\xbf[Docs]\r\npath = /srv/docs\r\n'
            path.write_bytes(original)
            before = path.stat().st_mtime_ns
            snapshot = read_configuration(str(path))
            with patch('pathlib.Path.open', side_effect=AssertionError('unexpected read')), \
                    patch('subprocess.run', side_effect=AssertionError('process')):
                view = DeclaredSharesView(snapshot.inspect())
                details = declared_share_details(view.shares[0])
            self.assertEqual(view.report.source, str(path))
            self.assertEqual(view.report.sha256, snapshot.sha256)
            self.assertIn('/srv/docs', details)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(path.stat().st_mtime_ns, before)

    def test_search_is_trimmed_case_insensitive_and_covers_only_name_and_path(self):
        view = self.view('[Famille]\npath = /srv/photos\nvalid users = secretuser\n'
                         '[Archive]\npath = /mnt/disque\n')
        self.assertEqual([row.name for row in view.filtered(' FAMILLE ')], ['Famille'])
        self.assertEqual([row.name for row in view.filtered('/MNT/DISQUE')], ['Archive'])
        self.assertEqual(view.filtered('secretuser'), ())
        self.assertEqual(view.filtered('absent'), ())
        self.assertEqual(view.filtered('   '), view.shares)

    def test_missing_fields_are_distinct_from_repeated_or_invalid_values(self):
        view = self.view('[Missing]\n[Ambiguous]\npath = /a\npath = /b\n'
                         'read only = perhaps\nbrowseable = yes\nguest ok = no\nvalid users = alex\n')
        missing, ambiguous = view.shares
        self.assertIn('path', missing.missing_fields)
        self.assertEqual(missing.ambiguous_fields, ())
        self.assertEqual(ambiguous.missing_fields, ())
        self.assertEqual(ambiguous.ambiguous_fields, ('path', 'read only'))
        self.assertEqual([row.name for row in view.filtered(category='incomplete')], ['Missing'])
        self.assertEqual([row.name for row in view.filtered(category='ambiguous')], ['Ambiguous'])

    def test_synonym_collisions_and_substitutions_are_ambiguous_without_guessing(self):
        view = self.view('[Docs]\npath = /srv/%U\nread only = yes\nwritable = no\n')
        share = view.filtered(category='ambiguous')[0]
        self.assertIn('path', share.ambiguous_fields)
        self.assertIn('read only', share.ambiguous_fields)
        self.assertIsNone(share.read_only)

    def test_unsupported_filter_includes_unknown_options_and_unresolved_principals(self):
        view = self.view('[Advanced]\npath = /a\nvfs objects = secret-option-value\n'
                         '[Partial]\npath = /b\nvalid users = @unknown\n'
                         '[Simple]\npath = /c\n')
        rows = view.filtered(category='unsupported')
        self.assertEqual([row.name for row in rows], ['Advanced', 'Partial'])
        from sambapilot.presentation import declared_share_guidance
        self.assertIn('Interprétation non prise en charge', declared_share_guidance(rows[0]))
        self.assertNotIn('secret-option-value', declared_share_guidance(rows[0]))
        self.assertNotIn('secret-option-value', str(view.report.to_dict()))

    def test_search_and_category_intersect_without_falling_back_to_other_rows(self):
        view = self.view('[Alpha]\npath = /srv/a\nvfs objects = recycle\n'
                         '[Beta]\npath = /srv/b\n')
        self.assertEqual([row.name for row in view.filtered('alpha', 'unsupported')], ['Alpha'])
        self.assertEqual(view.filtered('beta', 'unsupported'), ())
        self.assertEqual(view.filtered('beta', 'ambiguous'), ())
        with self.assertRaises(ValueError):
            view.filtered(category='invalid-filter')

    def test_empty_and_blocked_inventories_never_gain_rows_through_filters(self):
        for view in (self.view('[global]\nworkgroup = HOME\n'),
                     self.view('[Docs]\n[Docs]\n')):
            for category in ('all', 'incomplete', 'ambiguous', 'unsupported'):
                self.assertEqual(view.filtered(category=category), ())
        self.assertIn('Analyse bloquée', view.summary)

    def test_guidance_distinguishes_empty_access_list_guest_and_missing_settings(self):
        from sambapilot.presentation import declared_share_guidance
        missing = self.view('[Docs]\n').shares[0]
        self.assertIn('Réglages incomplets', declared_share_guidance(missing))
        explicit = self.view('[Docs]\npath = /srv/docs\nread only = yes\nbrowseable = yes\n'
                             'guest ok = yes\nvalid users =\n').shares[0]
        self.assertEqual(explicit.missing_fields, ())
        text = declared_share_guidance(explicit)
        self.assertIn('explicitement vide', text)
        self.assertIn('Accès invité déclaré', text)
        self.assertNotIn('Réglages incomplets', text)

    def test_one_declaration_can_be_incomplete_ambiguous_and_unsupported(self):
        view = self.view('[Docs]\nread only = invalid\nvfs objects = recycle\n')
        for category in ('incomplete', 'ambiguous', 'unsupported'):
            self.assertEqual(view.filtered(category=category), view.shares)
        self.assertIn('missing_fields', view.report.to_dict()['shares'][0])
        self.assertIn('ambiguous_fields', view.report.to_dict()['shares'][0])

    def test_modification_readiness_reuses_writer_and_rejects_inspection_only_synonyms(self):
        from sambapilot.file_planning import FilePlanSession
        from sambapilot.inspection import ConfigurationSnapshot
        from sambapilot.planning import PlanError, digest
        supported = ('[Docs]\npath = /srv/docs\nread only = yes\nbrowseable = yes\n'
                     'guest ok = no\nvalid users = alex\n')
        with patch('pathlib.Path.open', side_effect=AssertionError('file')), \
                patch('subprocess.run', side_effect=AssertionError('process')):
            session = FilePlanSession(ConfigurationSnapshot('/chosen/smb.conf', supported, digest(supported)))
            self.assertTrue(session.draft_for('Docs').read_only)
            synonym = supported.replace('read only = yes', 'writable = no')
            self.assertTrue(self.view(synonym).shares[0].read_only)
            with self.assertRaises(PlanError):
                FilePlanSession(ConfigurationSnapshot('/chosen/smb.conf', synonym, digest(synonym))).draft_for('Docs')
