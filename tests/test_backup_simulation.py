import contextlib
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from sambapilot.backup_simulation import BackupSandbox, SimulationError, main


ORIGINAL = b'\xef\xbb\xbf# Configuration fictive\r\n[Docs]\r\npath = /srv/fictif\r\n'
MODIFIED = b'# Autre configuration fictive\n[Photos]\npath = /srv/photos\n'


class BackupSimulationTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = BackupSandbox(ORIGINAL)
        self.addCleanup(self.sandbox.close)

    def assert_no_stages(self):
        self.assertEqual(list(self.sandbox.configuration_path.parent.glob('.restore-*')), [])

    def changed_preview(self):
        backup = self.sandbox.create_backup()
        self.sandbox.edit_fictional_configuration(MODIFIED)
        return backup, self.sandbox.prepare_restore(backup)

    def test_dated_backup_preserves_exact_bytes_and_has_private_permissions(self):
        before = self.sandbox.configuration_path.stat().st_mtime_ns
        record = self.sandbox.create_backup()
        data = self.sandbox.backup_path(record)
        self.assertEqual(data.read_bytes(), ORIGINAL)
        self.assertEqual(record.sha256, hashlib.sha256(ORIGINAL).hexdigest())
        self.assertEqual(record.size, len(ORIGINAL))
        self.assertIsNotNone(datetime.fromisoformat(record.created_at).utcoffset())
        self.assertRegex(record.name, r'^\d{8}T\d{12}Z-[0-9a-f]{32}$')
        self.assertEqual(stat.S_IMODE(data.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(data.parent.stat().st_mode), 0o700)
        metadata = data.with_name('metadata.json')
        self.assertEqual(stat.S_IMODE(metadata.stat().st_mode), 0o600)
        self.assertEqual(json.loads(metadata.read_text())['mode'], 'simulation')
        self.assertEqual(self.sandbox.configuration_path.stat().st_mtime_ns, before)

    def test_preview_is_read_only_and_never_applicable_to_real_configuration(self):
        backup = self.sandbox.create_backup()
        self.sandbox.edit_fictional_configuration(MODIFIED)
        before = self.sandbox.configuration_path.read_bytes(), self.sandbox.configuration_path.stat().st_mtime_ns
        preview = self.sandbox.prepare_restore(backup)
        self.assertIn('-[Photos]', preview.diff)
        self.assertIn('+[Docs]', preview.diff)
        self.assertFalse(preview.can_apply)
        self.assertEqual(preview.mode, 'simulation')
        self.assertEqual(len(self.sandbox.backups), 1)
        self.assertEqual((self.sandbox.configuration_path.read_bytes(), self.sandbox.configuration_path.stat().st_mtime_ns), before)

    def test_round_trip_restores_original_and_can_recover_the_replaced_state(self):
        backup, preview = self.changed_preview()
        result = self.sandbox.restore(preview, confirmed=True)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), ORIGINAL)
        self.assertEqual(result.restored_sha256, backup.sha256)
        self.assertEqual(self.sandbox.backup_path(result.recovery_backup).read_bytes(), MODIFIED)
        self.assertEqual(self.sandbox.backup_path(backup).read_bytes(), ORIGINAL)
        recovery_preview = self.sandbox.prepare_restore(result.recovery_backup)
        self.sandbox.restore(recovery_preview, confirmed=True)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), MODIFIED)
        self.assert_no_stages()

    def test_confirmation_is_explicit_and_a_preview_cannot_be_reused(self):
        _, preview = self.changed_preview()
        for confirmation in (False, 1, 'yes'):
            with self.subTest(confirmation=confirmation), self.assertRaises(SimulationError):
                self.sandbox.restore(preview, confirmed=confirmation)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), MODIFIED)
        self.sandbox.restore(preview, confirmed=True)
        with self.assertRaises(SimulationError):
            self.sandbox.restore(preview, confirmed=True)
        with self.assertRaises(SimulationError):
            self.sandbox.restore(None, confirmed=True)

    def test_modified_target_refuses_restore_and_preserves_external_changes(self):
        _, preview = self.changed_preview()
        changed = b'# External fictional change\n'
        self.sandbox.edit_fictional_configuration(changed)
        with self.assertRaisesRegex(SimulationError, 'changé'):
            self.sandbox.restore(preview, confirmed=True)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), changed)
        self.assertEqual(len(self.sandbox.backups), 1)

    def test_replaced_target_with_identical_content_is_also_stale(self):
        _, preview = self.changed_preview()
        self.sandbox.edit_fictional_configuration(MODIFIED)
        with self.assertRaises(SimulationError):
            self.sandbox.restore(preview, confirmed=True)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), MODIFIED)

    def test_corrupted_backup_is_refused_before_preview_and_after_preview(self):
        backup, preview = self.changed_preview()
        self.sandbox.backup_path(backup).write_bytes(b'altered bytes\n')
        with self.assertRaises(SimulationError):
            self.sandbox.restore(preview, confirmed=True)
        with self.assertRaises(SimulationError):
            self.sandbox.prepare_restore(backup)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), MODIFIED)

    def test_altered_metadata_is_refused_even_if_backup_content_matches(self):
        backup, preview = self.changed_preview()
        metadata = self.sandbox.backup_path(backup).with_name('metadata.json')
        metadata.write_text('{}\n', encoding='utf-8')
        with self.assertRaises(SimulationError):
            self.sandbox.restore(preview, confirmed=True)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), MODIFIED)
        self.assertEqual(self.sandbox.backup_path(backup).read_bytes(), ORIGINAL)

    def test_forged_record_and_foreign_preview_are_refused(self):
        record = self.sandbox.create_backup()
        for forged in (replace(record, name='../../outside'), replace(record, sha256='0' * 64), None):
            with self.subTest(record=forged), self.assertRaises(SimulationError):
                self.sandbox.prepare_restore(forged)
        with BackupSandbox(ORIGINAL) as other:
            preview = other.prepare_restore(other.create_backup())
            with self.assertRaises(SimulationError):
                self.sandbox.restore(preview, confirmed=True)

    def test_symlink_target_is_refused_without_reading_or_changing_its_victim(self):
        record = self.sandbox.create_backup()
        with tempfile.TemporaryDirectory() as directory:
            victim = Path(directory) / 'fictitious-victim.conf'
            victim.write_bytes(b'preserve outside fixture')
            self.sandbox.configuration_path.unlink()
            self.sandbox.configuration_path.symlink_to(victim)
            original_open = os.open
            def guarded_open(path, *args, **kwargs):
                self.assertNotEqual(Path(path), victim)
                return original_open(path, *args, **kwargs)
            with patch('sambapilot.backup_simulation.os.open', side_effect=guarded_open), self.assertRaises(SimulationError):
                self.sandbox.prepare_restore(record)
            self.assertEqual(victim.read_bytes(), b'preserve outside fixture')

    def test_linked_backup_and_linked_backup_directory_are_refused(self):
        backup = self.sandbox.create_backup()
        path = self.sandbox.backup_path(backup)
        path.unlink()
        path.symlink_to(self.sandbox.configuration_path)
        with self.assertRaises(SimulationError):
            self.sandbox.prepare_restore(backup)
        path.unlink()
        path.with_name('metadata.json').unlink()
        folder = path.parent
        folder.rmdir()
        folder.symlink_to(self.sandbox.configuration_path.parent, target_is_directory=True)
        with self.assertRaises(SimulationError):
            self.sandbox.prepare_restore(backup)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), ORIGINAL)

    def test_hardlinked_or_special_targets_are_refused(self):
        record = self.sandbox.create_backup()
        link = self.sandbox.configuration_path.with_name('extra-link')
        os.link(self.sandbox.configuration_path, link)
        with self.assertRaises(SimulationError):
            self.sandbox.prepare_restore(record)
        link.unlink()
        self.sandbox.configuration_path.unlink()
        self.sandbox.configuration_path.mkdir()
        with self.assertRaises(SimulationError):
            self.sandbox.prepare_restore(record)

    def test_unreadable_target_is_refused_without_touching_backups(self):
        backup, preview = self.changed_preview()
        original_read = self.sandbox._read
        def read(path):
            if path == self.sandbox.configuration_path:
                raise PermissionError('simulated refusal')
            return original_read(path)
        with patch.object(self.sandbox, '_read', side_effect=read), self.assertRaises(PermissionError):
            self.sandbox.restore(preview, confirmed=True)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), MODIFIED)
        self.assertEqual(self.sandbox.backup_path(backup).read_bytes(), ORIGINAL)

    def test_backup_write_failure_cleans_its_own_incomplete_files(self):
        with patch('sambapilot.backup_simulation.os.fsync', side_effect=OSError('write failure')), self.assertRaises(OSError):
            self.sandbox.create_backup()
        self.assertEqual(self.sandbox.backups, ())
        self.assertEqual(list(self.sandbox.configuration_path.parent.joinpath('backups').iterdir()), [])
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), ORIGINAL)

    def test_failed_replacement_preserves_target_and_valid_recovery_backup(self):
        backup, preview = self.changed_preview()
        with patch('sambapilot.backup_simulation.os.replace', side_effect=OSError('replace failure')), self.assertRaises(OSError):
            self.sandbox.restore(preview, confirmed=True)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), MODIFIED)
        self.assertEqual(self.sandbox.backup_path(backup).read_bytes(), ORIGINAL)
        self.assertEqual(self.sandbox.backup_path(self.sandbox.backups[-1]).read_bytes(), MODIFIED)
        self.assert_no_stages()
        self.sandbox.restore(self.sandbox.prepare_restore(backup), confirmed=True)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), ORIGINAL)

    def test_staging_write_failure_preserves_current_file_and_cleans_stage(self):
        _, preview = self.changed_preview()
        original_write = self.sandbox._write_new
        def write(path, data):
            if path.name.startswith('.restore-'):
                with patch('sambapilot.backup_simulation.os.fsync', side_effect=OSError('stage failure')):
                    return original_write(path, data)
            return original_write(path, data)
        with patch.object(self.sandbox, '_write_new', side_effect=write), self.assertRaises(OSError):
            self.sandbox.restore(preview, confirmed=True)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), MODIFIED)
        self.assert_no_stages()

    def test_external_edit_during_staging_is_detected_before_replacement(self):
        _, preview = self.changed_preview()
        original_write = self.sandbox._write_new
        changed = b'# fictional edit during staging\n'
        def write(path, data):
            original_write(path, data)
            if path.name.startswith('.restore-'):
                self.sandbox.configuration_path.write_bytes(changed)
        with patch.object(self.sandbox, '_write_new', side_effect=write), self.assertRaises(SimulationError):
            self.sandbox.restore(preview, confirmed=True)
        self.assertEqual(self.sandbox.configuration_path.read_bytes(), changed)
        self.assert_no_stages()

    def test_backup_name_collision_never_replaces_an_existing_backup(self):
        fixed = datetime(2026, 11, 9, 18, 0, tzinfo=timezone.utc)
        with patch('sambapilot.backup_simulation.datetime') as clock, \
                patch('sambapilot.backup_simulation.uuid4', return_value=Mock(hex='a' * 32)):
            clock.now.return_value = fixed
            record = self.sandbox.create_backup()
            before = self.sandbox.backup_path(record).read_bytes()
            with self.assertRaises(FileExistsError):
                self.sandbox.create_backup()
        self.assertEqual(self.sandbox.backup_path(record).read_bytes(), before)
        self.assertEqual(len(self.sandbox.backups), 1)

    def test_closing_removes_only_the_temporary_simulation_and_disables_it(self):
        root = self.sandbox.configuration_path.parent
        self.sandbox.create_backup()
        self.sandbox.close()
        self.assertFalse(root.exists())
        with self.assertRaises(SimulationError):
            self.sandbox.create_backup()


class BackupSimulationEntryTests(unittest.TestCase):
    def test_invalid_contents_are_refused_before_creating_a_workspace(self):
        from sambapilot.inspection import MAX_CONFIG_BYTES
        with patch('sambapilot.backup_simulation.tempfile.TemporaryDirectory', side_effect=AssertionError('directory')):
            for content in (None, 'text instead of bytes', b'\xff', b'x' * (MAX_CONFIG_BYTES + 1)):
                with self.subTest(content_type=type(content)), self.assertRaises(SimulationError):
                    BackupSandbox(content)

    def test_missing_demo_or_source_argument_is_refused_before_workspace_creation(self):
        for args in ([], ['--demo', '--config', '/etc/samba/smb.conf']):
            with self.subTest(args=args), patch('sambapilot.backup_simulation.BackupSandbox', side_effect=AssertionError('workspace')), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(args)
            self.assertEqual(caught.exception.code, 2)

    def test_demo_restores_fictional_data_without_processes(self):
        with patch('subprocess.run', side_effect=AssertionError('process')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['--demo']), 0)
        self.assertIn('SIMULATION', output.getvalue())
        self.assertIn('Contenu initial restauré : True', output.getvalue())
        self.assertIn('dossier temporaire supprimé', output.getvalue())
