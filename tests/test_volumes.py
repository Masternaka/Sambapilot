import contextlib
import errno
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from sambapilot.cli import main
from sambapilot.volume_system import HostVolumeProbe
from sambapilot.volumes import (DemoVolumeProbe, DirectoryObservation, MAX_MOUNTINFO_BYTES,
                                VOLUME_SCENARIOS, VolumeError, collect_volume, format_volume,
                                parse_mountinfo)


ROOT_TABLE = '1 0 8:1 / / rw - ext4 /dev/fictif rw\n'
MOUNT_TABLE = ROOT_TABLE + '2 1 8:2 / /mnt/medias rw shared:1 - ext4 /dev/fictif2 rw\n'


class VolumeTests(unittest.TestCase):
    def probe(self, table=MOUNT_TABLE, observation=None):
        probe = Mock(mode='live')
        probe.system.return_value = 'Linux'
        probe.mountinfo.return_value = (table, None)
        probe.directory.return_value = observation or DirectoryObservation('present', '8:2')
        return probe

    def test_expected_volume_and_device_are_distinct_from_permissions(self):
        result = collect_volume('/mnt/medias/films', '/mnt/medias', self.probe())
        self.assertTrue(result.expected_mounted)
        self.assertTrue(result.on_expected_mount)
        self.assertEqual(result.directory_status, 'present')
        self.assertFalse(result.read_only)
        self.assertFalse(result.can_apply)
        self.assertTrue(any('UUID' in note for note in result.notes))

    def test_parent_filesystem_does_not_prove_expected_volume_is_mounted(self):
        probe = self.probe(ROOT_TABLE)
        result = collect_volume('/mnt/medias/films', '/mnt/medias', probe)
        self.assertFalse(result.expected_mounted)
        self.assertFalse(result.on_expected_mount)
        self.assertEqual(result.actual_mount, '/')
        probe.directory.assert_not_called()

    def test_nested_mount_is_not_mistaken_for_expected_mount(self):
        probe = self.probe(MOUNT_TABLE + '3 2 8:3 / /mnt/medias/films rw - ext4 /dev/fictif3 rw\n')
        result = collect_volume('/mnt/medias/films/archives', '/mnt/medias', probe)
        self.assertTrue(result.expected_mounted)
        self.assertFalse(result.on_expected_mount)
        self.assertEqual(result.actual_mount, '/mnt/medias/films')
        probe.directory.assert_not_called()

    def test_readonly_per_mount_or_superblock_is_reported(self):
        for mount_flags, super_flags in (('ro', 'rw'), ('rw', 'ro'), ('ro', 'ro')):
            table = ROOT_TABLE + f'2 1 8:2 / /mnt/medias {mount_flags} - ext4 /dev/fictif2 {super_flags}\n'
            with self.subTest(mount_flags=mount_flags, super_flags=super_flags):
                result = collect_volume('/mnt/medias/films', '/mnt/medias', self.probe(table))
                self.assertTrue(result.read_only)

    def test_device_mismatch_discards_directory_confirmation(self):
        result = collect_volume('/mnt/medias/films', '/mnt/medias',
                                self.probe(observation=DirectoryObservation('present', '8:99')))
        self.assertIsNone(result.on_expected_mount)
        self.assertEqual(result.directory_status, 'unknown')

    def test_missing_inaccessible_and_nondirectory_paths_are_distinct(self):
        for status in ('missing', 'unknown', 'not-directory'):
            with self.subTest(status=status):
                result = collect_volume('/mnt/medias/films', '/mnt/medias',
                                        self.probe(observation=DirectoryObservation(status)))
                self.assertEqual(result.directory_status, status)
                self.assertIsNone(result.on_expected_mount)

    def test_unreadable_or_malformed_table_never_implies_absence(self):
        for content, error in (('', 'permission'), ('broken', None), ('', None)):
            probe = self.probe(content)
            probe.mountinfo.return_value = (content, error)
            with self.subTest(content=content, error=error):
                result = collect_volume('/mnt/medias/films', '/mnt/medias', probe)
                self.assertIsNone(result.expected_mounted)
                probe.directory.assert_not_called()

    def test_stacked_mounts_remain_unknown(self):
        probe = self.probe(MOUNT_TABLE + '3 2 8:3 / /mnt/medias rw - ext4 /dev/fictif3 rw\n')
        result = collect_volume('/mnt/medias/films', '/mnt/medias', probe)
        self.assertIsNone(result.expected_mounted)
        probe.directory.assert_not_called()

    def test_automatic_remote_or_unknown_filesystems_do_not_probe_directory(self):
        for filesystem in ('autofs', 'nfs4', 'cifs', 'fuse.sshfs', 'unknownfs'):
            probe = self.probe(MOUNT_TABLE.replace('- ext4 /dev/fictif2', '- ' + filesystem + ' /dev/fictif2'))
            with self.subTest(filesystem=filesystem):
                result = collect_volume('/mnt/medias/films', '/mnt/medias', probe)
                self.assertEqual(result.directory_status, 'not-checked')
                self.assertIsNone(result.on_expected_mount)
                probe.directory.assert_not_called()

    def test_changed_table_or_failed_second_read_discards_results(self):
        for following in ((ROOT_TABLE, None), ('', 'denied')):
            probe = self.probe()
            probe.mountinfo.side_effect = [(MOUNT_TABLE, None), following]
            with self.subTest(following=following):
                result = collect_volume('/mnt/medias/films', '/mnt/medias', probe)
                self.assertIsNone(result.expected_mounted)
                self.assertIsNone(result.read_only)
                self.assertIsNone(result.basis_sha256)

    def test_non_linux_stops_before_other_probes(self):
        probe = self.probe()
        probe.system.return_value = 'Darwin'
        result = collect_volume('/mnt/medias/films', '/mnt/medias', probe)
        self.assertIsNone(result.expected_mounted)
        probe.mountinfo.assert_not_called()
        probe.directory.assert_not_called()

    def test_bad_paths_are_refused_before_probes(self):
        for path, point in (('/mnt/medias/../secret', '/mnt/medias'), ('relative', '/mnt/medias'),
                            ('/mnt/medias-other', '/mnt/medias'), ('/mnt/medias/', '/mnt/medias'),
                            ('/mnt/medias/a\n', '/mnt/medias'), ('/mnt/medias/%U', '/mnt/medias'),
                            ('/mnt/medias', '/'), ('//mnt/medias', '/mnt/medias')):
            probe = self.probe()
            with self.subTest(path=path, point=point), self.assertRaises(VolumeError):
                collect_volume(path, point, probe)
            probe.system.assert_not_called()

    def test_escaped_points_and_no_raw_mount_source_in_report(self):
        table = ROOT_TABLE + '2 1 8:2 / /mnt/mes\\040medias rw - ext4 user:private-secret@host rw\n'
        result = collect_volume('/mnt/mes medias/films', '/mnt/mes medias', self.probe(table))
        self.assertTrue(result.on_expected_mount)
        self.assertNotIn('private-secret', format_volume(result))
        self.assertNotIn('private-secret', json.dumps(result.to_dict()))

    def test_invalid_records_options_and_duplicate_ids_are_refused(self):
        for table in ('', 'broken', MOUNT_TABLE + MOUNT_TABLE, MOUNT_TABLE.replace('8:2', 'invalid'),
                       MOUNT_TABLE.replace('/mnt/medias', '/mnt/medias\\099'),
                       MOUNT_TABLE.replace('/mnt/medias', '/mnt//medias'),
                       MOUNT_TABLE.replace('rw shared:1', 'rw,ro shared:1'), 'x' * (MAX_MOUNTINFO_BYTES + 1)):
            with self.subTest(length=len(table)), self.assertRaises(VolumeError):
                parse_mountinfo(table)

    def test_all_demo_scenarios_never_read_host_or_launch_processes(self):
        with patch('pathlib.Path.open', side_effect=AssertionError('file')), \
                patch('os.open', side_effect=AssertionError('metadata')), \
                patch('subprocess.run', side_effect=AssertionError('process')):
            for scenario in VOLUME_SCENARIOS:
                result = collect_volume('/mnt/medias/films', '/mnt/medias', DemoVolumeProbe(scenario, '/mnt/medias'))
                self.assertEqual(result.mode, 'demo')
                self.assertFalse(result.can_apply)
                self.assertIn('DÉMONSTRATION', format_volume(result))


class VolumeSystemTests(unittest.TestCase):
    def test_fixed_proc_path_is_read_with_size_limit_only(self):
        stream = io.BytesIO(MOUNT_TABLE.encode())
        with patch.object(Path, 'open', autospec=True, return_value=stream) as opened:
            table, error = HostVolumeProbe().mountinfo()
        opened.assert_called_once_with(Path('/proc/self/mountinfo'), 'rb')
        self.assertEqual(table, MOUNT_TABLE)
        self.assertIsNone(error)

    def test_oversized_invalid_utf8_and_inaccessible_tables_are_unknown(self):
        for data in (b'x' * (MAX_MOUNTINFO_BYTES + 1), b'\xff'):
            with patch.object(Path, 'open', return_value=io.BytesIO(data)):
                self.assertIsNotNone(HostVolumeProbe().mountinfo()[1])
        with patch.object(Path, 'open', side_effect=PermissionError()):
            self.assertIsNotNone(HostVolumeProbe().mountinfo()[1])

    def test_metadata_walk_uses_no_follow_and_never_opens_for_writing(self):
        with patch.object(os, 'O_PATH', 0x200000, create=True), \
                patch('os.open', side_effect=[10, 11, 12]) as opened, \
                patch('os.close') as closed, patch('os.fstat', return_value=SimpleNamespace(st_dev=os.makedev(8, 2))):
            observation = HostVolumeProbe().directory('/mnt/medias')
        self.assertEqual((observation.status, observation.device), ('present', '8:2'))
        self.assertEqual([call.args[0] for call in opened.call_args_list], ['/', 'mnt', 'medias'])
        self.assertEqual(opened.call_args_list[1].kwargs['dir_fd'], 10)
        self.assertEqual(opened.call_args_list[2].kwargs['dir_fd'], 11)
        for call in opened.call_args_list:
            flags = call.args[1]
            self.assertTrue(flags & os.O_NOFOLLOW)
            self.assertFalse(flags & os.O_CREAT)
            self.assertFalse(flags & os.O_TRUNC)
        self.assertEqual([call.args[0] for call in closed.call_args_list], [10, 11, 12])

    def test_permission_symlink_and_missing_errors_close_descriptors(self):
        for error, expected in ((FileNotFoundError(), 'missing'), (PermissionError(), 'unknown'),
                                (OSError(errno.ENOTDIR, 'notdir'), 'not-directory'), (OSError(errno.ELOOP, 'link'), 'not-directory')):
            with self.subTest(expected=expected), patch.object(os, 'O_PATH', 0x200000, create=True), \
                    patch('os.open', side_effect=[10, error]), patch('os.close') as closed:
                self.assertEqual(HostVolumeProbe().directory('/mnt').status, expected)
                closed.assert_called_once_with(10)


class VolumeCliTests(unittest.TestCase):
    def test_demo_command_is_available_without_linux_or_host_access(self):
        with patch('sambapilot.cli.HostVolumeProbe', side_effect=AssertionError('host')), \
                patch('subprocess.run', side_effect=AssertionError('process')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['examiner-volume', '--demo', 'unmounted', '--path', '/mnt/medias/films',
                                   '--mountpoint', '/mnt/medias', '--json']), 0)
        report = json.loads(output.getvalue())
        self.assertFalse(report['expected_mounted'])
        self.assertFalse(report['can_apply'])

    def test_source_and_paths_are_required_and_exclusive(self):
        for args in ([], ['--local'], ['--demo', '--local', '--path', '/mnt/a', '--mountpoint', '/mnt/a']):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(['examiner-volume', *args])

    def test_non_linux_local_report_is_unknown_and_does_not_read_proc(self):
        with patch('sambapilot.volume_system.platform.system', return_value='Darwin'), \
                patch.object(HostVolumeProbe, 'mountinfo', side_effect=AssertionError('proc')), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(['examiner-volume', '--local', '--path', '/mnt/a', '--mountpoint', '/mnt/a', '--json']), 2)
        self.assertIsNone(json.loads(output.getvalue())['expected_mounted'])
