import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sambapilot.cli import main
from sambapilot.demo import demo_configuration
from sambapilot.planning import PlanError, prepare_plan, render_section
from sambapilot.share_profiles import SHARE_PROFILES, draft_from_profile, profile_values


class ShareProfileTests(unittest.TestCase):
    def test_profile_defaults_are_explicit_without_host_or_process(self):
        with patch('pathlib.Path.open', side_effect=AssertionError('file')), \
                patch('pathlib.Path.home', side_effect=AssertionError('home')), \
                patch('subprocess.run', side_effect=AssertionError('process')):
            personal = draft_from_profile('personal', users=('alex',))
            family = draft_from_profile('family', groups=('famille',))
            media = draft_from_profile('media', groups=('famille',))
        self.assertEqual((personal.read_only, personal.browseable), (False, False))
        self.assertEqual((family.read_only, family.browseable), (False, True))
        self.assertEqual((media.read_only, media.browseable), (True, True))
        self.assertEqual(personal.name, 'Personnel')
        self.assertEqual(media.path, '/srv/partages/medias')

    def test_no_profile_supplies_a_default_account_or_group(self):
        for profile in SHARE_PROFILES:
            with self.subTest(profile=profile.key), self.assertRaisesRegex(PlanError, 'utilisateur ou un groupe'):
                draft_from_profile(profile.key)

    def test_invalid_or_duplicate_identities_use_the_shared_refusals(self):
        for users, groups in ((('alex;reboot',), ()), ((), ('@famille',)), (('alex', 'alex'), ())):
            with self.subTest(users=users, groups=groups), self.assertRaises(PlanError):
                draft_from_profile('family', users=users, groups=groups)

    def test_custom_name_path_and_identities_are_preserved(self):
        draft = draft_from_profile('media', 'Photos été', '/srv/Photos été', ('alex',), ('photos',))
        self.assertEqual((draft.name, draft.path, draft.users, draft.groups),
                         ('Photos été', '/srv/Photos été', ('alex',), ('photos',)))

    def test_access_and_visibility_overrides_are_validated_and_retained(self):
        draft = draft_from_profile('personal', users=('alex',), read_only=True, browseable=True)
        self.assertTrue(draft.read_only)
        self.assertTrue(draft.browseable)
        with self.assertRaises(PlanError):
            draft_from_profile('media', users=('alex',), read_only='yes')

    def test_unvalidated_form_text_is_preserved_until_normal_validation(self):
        fields = profile_values('media', ' Nom invalide ', '/srv/../docs')
        self.assertEqual(fields.name, ' Nom invalide ')
        self.assertEqual(fields.path, '/srv/../docs')
        with self.assertRaises(PlanError):
            draft_from_profile('media', fields.name, fields.path, users=('alex',))

    def test_unknown_profile_is_refused_and_catalogue_is_unchanged(self):
        initial = tuple(SHARE_PROFILES)
        fields = profile_values('personal', 'Autre', '/srv/autre')
        self.assertEqual(fields.name, 'Autre')
        self.assertEqual(tuple(SHARE_PROFILES), initial)
        with self.assertRaises(PlanError):
            profile_values('unknown')

    def test_generated_profile_plans_preserve_source_bom_comments_and_line_endings(self):
        source = '\ufeff# conserver\r\n[global]\r\n    workgroup = MAISON\r\n\r\n[Ancien]\r\n    path = /srv/ancien\r\n    vfs objects = fruit\r\n'
        for profile in SHARE_PROFILES:
            with self.subTest(profile=profile.key):
                draft = draft_from_profile(profile.key, users=('alex',))
                plan = prepare_plan(source, 'create', draft.name, draft)
                self.assertTrue(plan.candidate.startswith(source))
                self.assertNotIn('\n', plan.candidate.replace('\r\n', ''))
                self.assertIn('guest ok = no', plan.candidate)
                self.assertFalse(plan.can_apply)

    def test_existing_profile_name_is_never_overwritten(self):
        draft = draft_from_profile('media', users=('alex',))
        source = render_section(draft)
        with self.assertRaisesRegex(PlanError, 'déjà ce nom'):
            prepare_plan(source, 'create', draft.name, draft)


class ShareProfileCliTests(unittest.TestCase):
    def test_demo_profiles_generate_plans_without_host_or_process(self):
        with patch('pathlib.Path.open', side_effect=AssertionError('file')), \
                patch('subprocess.run', side_effect=AssertionError('process')):
            for profile in SHARE_PROFILES:
                with self.subTest(profile=profile.key), contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(['plan-partage', '--demo', '--action', 'create', '--profile', profile.key,
                                           '--user', 'alex', '--json']), 0)
                plan = json.loads(output.getvalue())
                self.assertEqual(plan['profile'], profile.key)
                self.assertEqual(plan['name'], profile.name)
                self.assertFalse(plan['can_apply'])

    def test_missing_identities_are_refused_before_reading_file(self):
        with patch('sambapilot.cli.FilePlanSession.open', side_effect=AssertionError('file')), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(['plan-partage', '--config', '/unused', '--action', 'create', '--profile', 'personal'])

    def test_cli_overrides_profile_access_and_visibility(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['plan-partage', '--demo', '--action', 'create', '--profile', 'personal',
                                   '--name', 'Travail', '--path', '/srv/travail', '--user', 'alex',
                                   '--read-only', '--visible', '--json']), 0)
        plan = json.loads(output.getvalue())
        self.assertIn('read only = yes', plan['candidate'].split('[Travail]')[1])
        self.assertIn('browseable = yes', plan['candidate'].split('[Travail]')[1])

    def test_conflicting_switches_are_refused(self):
        for flags in (['--writable', '--read-only'], ['--hidden', '--visible']):
            with self.subTest(flags=flags), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(['plan-partage', '--demo', '--action', 'create', '--profile', 'media', '--user', 'alex', *flags])

    def test_profiles_are_refused_for_update_and_remove_before_file_read(self):
        for action in ('update', 'remove'):
            with self.subTest(action=action), \
                    patch('sambapilot.cli.FilePlanSession.open', side_effect=AssertionError('file')), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(['plan-partage', '--config', '/unused', '--action', action, '--name', 'Docs',
                      '--profile', 'media', '--user', 'alex'])

    def test_file_based_profile_creation_never_changes_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            path.write_text(demo_configuration(), encoding='utf-8')
            before = path.read_bytes(), path.stat().st_mtime_ns
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(['plan-partage', '--config', str(path), '--action', 'create',
                                       '--profile', 'media', '--group', 'famille', '--json']), 0)
            self.assertEqual(json.loads(output.getvalue())['source'], str(path))
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_manual_defaults_and_name_requirement_are_preserved(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['plan-partage', '--demo', '--action', 'create', '--name', 'Docs',
                                   '--path', '/srv/docs', '--user', 'alex', '--json']), 0)
        plan = json.loads(output.getvalue())
        self.assertNotIn('profile', plan)
        self.assertIn('read only = yes', plan['candidate'].split('[Docs]')[1])
        self.assertIn('browseable = yes', plan['candidate'].split('[Docs]')[1])
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(['plan-partage', '--demo', '--action', 'create', '--path', '/srv/docs', '--user', 'alex'])
