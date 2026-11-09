"""Contrôles testparm réels, uniquement sur activation explicite sous Linux."""

import contextlib
import io
import json
import os
from pathlib import Path
import platform
import tempfile
import unittest

from sambapilot.cli import main
from sambapilot.demo import demo_configuration
from sambapilot.file_planning import FilePlanSession
from sambapilot.planning import ShareDraft, prepare_plan
from sambapilot.system import HostProbe
from sambapilot.validation import validate_plan


@unittest.skipUnless(os.environ.get('SAMBAPILOT_SAMBA_TESTS') == '1',
                     'Essais natifs Samba non activés (SAMBAPILOT_SAMBA_TESTS=1).')
class SambaIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if platform.system() != 'Linux' or HostProbe().tool('testparm') is None:
            raise RuntimeError('Essais natifs demandés : Linux et testparm système déjà installé sont requis.')

    def assert_accepted(self, plan):
        result = validate_plan(plan)
        self.assertEqual(result.status, 'accepted', result.message + '\n' + result.diagnostics)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.candidate_sha256, plan.candidate_sha256)
        self.assertFalse(result.can_apply)
        self.assertFalse(plan.can_apply)

    def test_created_share_is_accepted_by_real_samba(self):
        draft = ShareDraft('Documents', '/srv/sambapilot-test/documents', ('alex',))
        self.assert_accepted(prepare_plan(demo_configuration(), 'create', draft.name, draft, mode='demo'))

    def test_update_and_removal_are_accepted_by_real_samba(self):
        for action in ('update', 'remove'):
            with self.subTest(action=action):
                draft = ShareDraft('Medias', '/srv/sambapilot-test/medias', groups=('famille',))
                self.assert_accepted(prepare_plan(demo_configuration(), action, 'Medias',
                                                 draft if action == 'update' else None, mode='demo'))

    def test_minimal_configuration_is_accepted_by_real_samba(self):
        draft = ShareDraft('Documents', '/srv/sambapilot-test/documents', ('alex',))
        self.assert_accepted(prepare_plan('', 'create', draft.name, draft, mode='demo'))

    def test_chosen_source_and_cli_json_remain_unchanged_after_real_control(self):
        with tempfile.TemporaryDirectory(prefix='sambapilot-native-test-') as directory:
            source = Path(directory) / 'smb.conf'
            source.write_text(demo_configuration(), encoding='utf-8')
            before = source.read_bytes(), source.stat().st_mtime_ns
            plan = FilePlanSession.open(str(source)).preview('remove', 'Medias')
            self.assert_accepted(plan)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = main(['plan-partage', '--config', str(source), '--action', 'remove',
                             '--name', 'Medias', '--validate', '--json'])
            report = json.loads(output.getvalue())
            self.assertEqual(code, 0, report)
            self.assertEqual(report['validation']['status'], 'accepted')
            self.assertEqual(report['validation']['candidate_sha256'], plan.candidate_sha256)
            self.assertFalse(report['can_apply'])
            self.assertFalse(report['validation']['can_apply'])
            self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns), before)
