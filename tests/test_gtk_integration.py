"""Essais GTK réels sur demande, avec GTK installé et une session graphique."""

import os
import unittest
from uuid import uuid4


@unittest.skipUnless(os.environ.get("SAMBAPILOT_GTK_TESTS") == "1",
                     "Essais natifs GTK non activés (SAMBAPILOT_GTK_TESTS=1).")
class GtkIntegrationTests(unittest.TestCase):
    def setUp(self):
        from sambapilot.gui import load_gtk
        self.Gtk = load_gtk()
        if not self.Gtk.init_check():
            self.fail("Les essais natifs exigent une session graphique accessible.")
        from gi.repository import Gio
        from sambapilot.gtk_app import SambaPilotWindow
        from sambapilot.presentation import DemoViewModel
        # NON_UNIQUE autorise plusieurs instances, mais n'isole pas leurs
        # chemins d'objets sur la connexion D-Bus partagée du processus.
        self.app = self.Gtk.Application(
            application_id="io.github.sambapilot.Tests.t" + uuid4().hex,
            flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.addCleanup(self.app.quit)
        self.assertTrue(self.app.register(None))
        self.window = SambaPilotWindow(self.app, DemoViewModel.create())
        self.addCleanup(self.window.destroy)

    def test_window_builds_all_pages_and_initial_selection(self):
        for name in ("dashboard", "installation", "shares", "access", "prepare", "configuration", "firewall", "maintenance"):
            self.assertIsNotNone(self.window.stack.get_child_by_name(name))
        self.assertEqual(len(self.window.visible_decisions), 12)
        self.assertIsNotNone(self.window.access_list.get_selected_row())

    def test_share_diagnostic_opens_without_probes_and_copies_only_prepared_address(self):
        from unittest.mock import Mock, patch
        with patch('pathlib.Path.open', side_effect=AssertionError('file')), \
                patch('sambapilot.gtk_share_diagnostic.HostVolumeProbe', side_effect=AssertionError('host')):
            self.window.open_share_diagnostic('Famille')
            sheet = self.window.share_diagnostic_window
            self.addCleanup(sheet.destroy)
            self.assertIsNone(sheet.prepared.connection)
            self.assertIsNone(sheet.prepared.volume)
            sheet.server.set_text('nas.local')
            self.assertEqual(sheet.prepared.connection.share, 'Famille')
            clipboard = Mock()
            with patch('sambapilot.gtk_share_diagnostic.ShareDiagnosticWindow.get_clipboard', return_value=clipboard):
                sheet.copy_address('macos')
                clipboard.set.assert_called_once_with('smb://nas.local/Famille')
            sheet.server.set_text('user:private-secret@nas')
            self.assertIsNone(sheet.prepared.connection)
            self.assertFalse(sheet.copy_buttons['macos'].get_sensitive())
            self.assertNotIn('private-secret', sheet.status.get_text())

    def test_share_diagnostic_demo_volume_is_explicit_and_invalidated_by_form_changes(self):
        from unittest.mock import patch
        self.window.open_share_diagnostic('Famille')
        sheet = self.window.share_diagnostic_window
        self.addCleanup(sheet.destroy)
        sheet.mountpoint.set_text('/srv/partages')
        sheet.volume_scenario.set_selected(1)
        with patch('sambapilot.gtk_share_diagnostic.HostVolumeProbe', side_effect=AssertionError('host')):
            sheet.examine_demo()
        self.assertFalse(sheet.prepared.volume.expected_mounted)
        sheet.symptom.set_selected(2)
        self.assertIsNone(sheet.prepared.volume)
        self.assertEqual(sheet.prepared.symptom, 'readonly')

    def file_share_diagnostic_fixture(self):
        from pathlib import Path
        import tempfile
        from sambapilot.inspection import read_configuration
        directory = tempfile.TemporaryDirectory(prefix='sambapilot-share-diagnostic-')
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'smb.conf'
        path.write_text('[Docs]\npath = /mnt/docs\n', encoding='utf-8')
        snapshot = read_configuration(str(path))
        self.window.file_shares_mode = True
        self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
        self.window.open_share_diagnostic('Docs')
        sheet = self.window.share_diagnostic_window
        self.addCleanup(sheet.destroy)
        return sheet, path, snapshot

    def test_share_diagnostic_local_volume_requires_confirmation_and_discards_old_results(self):
        from dataclasses import replace
        from unittest.mock import patch
        from sambapilot.volumes import DemoVolumeProbe, collect_volume
        sheet, _path, snapshot = self.file_share_diagnostic_fixture()
        self.assertEqual(sheet.prepared.read_at, snapshot.read_at)
        self.assertFalse(sheet.local_button.get_sensitive())
        sheet.mountpoint.set_text('/mnt')
        with patch('sambapilot.gtk_share_diagnostic.Thread') as thread:
            sheet.examine_local()
            thread.assert_not_called()
            sheet.local_confirm.set_active(True)
            sheet.examine_local()
            thread.assert_called_once()
        generation = sheet.generation
        volume = replace(collect_volume('/mnt/docs', '/mnt', DemoVolumeProbe('mounted', '/mnt')), mode='live')
        sheet.receive_volume(generation, volume)
        self.assertIs(sheet.prepared.volume, volume)
        sheet.server.set_text('autre.local')
        sheet.receive_volume(generation, volume)
        self.assertIsNone(sheet.prepared.volume)

    def test_share_diagnostic_closes_when_source_is_cleared(self):
        sheet, _path, _snapshot = self.file_share_diagnostic_fixture()
        self.window.clear_inspection()
        self.assertFalse(sheet.active)
        self.assertIsNone(self.window.share_diagnostic_window)

    def test_share_diagnostic_changed_file_refuses_local_probe_and_invalidates_sheet(self):
        from unittest.mock import patch
        sheet, path, _snapshot = self.file_share_diagnostic_fixture()
        sheet.mountpoint.set_text('/mnt')
        sheet.local_confirm.set_active(True)
        path.write_text('[Docs]\npath = /mnt/autre\n', encoding='utf-8')
        with patch('sambapilot.gtk_share_diagnostic.HostVolumeProbe', side_effect=AssertionError('host')), \
                patch('sambapilot.gtk_share_diagnostic.GLib.idle_add', side_effect=lambda callback, *args: callback(*args)):
            sheet.read_local(sheet.generation, '/mnt/docs', '/mnt')
        self.assertTrue(sheet.source_stale)
        self.assertIsNone(sheet.prepared)
        self.assertFalse(sheet.local_button.get_sensitive())

    def test_volume_examples_never_read_host_and_distinguish_missing_mount(self):
        from unittest.mock import patch
        page = self.window.volume_page
        self.window.stack.set_visible_child_name('maintenance')
        with patch('sambapilot.gtk_volumes.HostVolumeProbe', side_effect=AssertionError('host')), \
                patch('pathlib.Path.open', side_effect=AssertionError('file')):
            page.scenario.set_selected(1)
            self.assertFalse(page.report.expected_mounted)
            self.assertEqual(page.source, 'demo')
            self.assertEqual(self.window.mode_label.get_text(), 'Démonstration')
            page.scenario.set_selected(4)
            self.assertIsNone(page.report.expected_mounted)

    def test_volume_local_results_are_invalidated_after_path_change_demo_and_close(self):
        from dataclasses import replace
        from unittest.mock import patch
        page = self.window.volume_page
        local = replace(page.report, mode='live')
        self.window.stack.set_visible_child_name('maintenance')
        with patch('sambapilot.gtk_volumes.Thread'):
            page.examine_local()
        generation = page.generation
        self.assertIsNone(page.report)
        self.assertEqual(self.window.mode_label.get_text(), 'Lecture seule')
        page.path.set_text('/mnt/medias/autre')
        self.assertEqual(self.window.mode_label.get_text(), 'À examiner')
        page.receive_report(generation, local)
        self.assertIsNone(page.report)
        page.use_demo()
        page.receive_report(generation, local)
        self.assertEqual(page.report.mode, 'demo')
        page.close()
        page.receive_report(page.generation - 1, local)
        self.assertEqual(page.report.mode, 'demo')

    def test_invalid_volume_paths_never_start_local_thread(self):
        from unittest.mock import patch
        page = self.window.volume_page
        page.mountpoint.set_text('/autre')
        with patch('sambapilot.gtk_volumes.Thread') as thread:
            page.examine_local()
            thread.assert_not_called()
        self.assertIsNone(page.report)
        self.assertTrue(page.local.get_sensitive())

    def test_share_profile_prefills_creation_without_identity_or_automatic_preview(self):
        self.window.open_share_plan('create')
        source = self.window.plan_session.source
        self.window.share_profile.set_selected(3)
        self.window.fill_share_profile()
        self.assertEqual(self.window.plan_name.get_text(), 'Mediatheque')
        self.assertEqual(self.window.plan_path.get_text(), '/srv/partages/medias')
        self.assertEqual(self.window.plan_users.get_text(), '')
        self.assertEqual(self.window.plan_groups.get_text(), '')
        self.assertFalse(self.window.plan_writable.get_active())
        self.assertIsNone(self.window.plan_session.current)
        self.assertEqual(self.window.plan_session.source, source)
        self.window.preview_share_plan(None)
        self.assertIsNone(self.window.plan_session.current)
        self.window.plan_groups.set_text('famille')
        self.window.preview_share_plan(None)
        self.assertFalse(self.window.plan_session.current.can_apply)

    def test_share_profile_retains_entered_fields_and_invalidates_old_plan(self):
        self.window.open_share_plan('create')
        self.window.plan_name.set_text('Travail')
        self.window.plan_path.set_text('/srv/travail')
        self.window.plan_users.set_text('alex')
        self.window.preview_share_plan(None)
        self.assertIsNotNone(self.window.plan_session.current)
        self.window.share_profile.set_selected(1)
        self.assertIsNone(self.window.plan_session.current)
        self.window.fill_share_profile()
        self.assertEqual(self.window.plan_name.get_text(), 'Travail')
        self.assertEqual(self.window.plan_path.get_text(), '/srv/travail')
        self.assertEqual(self.window.plan_users.get_text(), 'alex')
        self.assertTrue(self.window.plan_writable.get_active())
        self.assertFalse(self.window.plan_browseable.get_active())
        self.assertFalse(self.window.validation_button.get_sensitive())

    def test_share_profiles_are_disabled_for_existing_share_changes(self):
        for action in ('update', 'remove'):
            with self.subTest(action=action):
                self.window.open_share_plan(action, 'Medias')
                before = (self.window.plan_name.get_text(), self.window.plan_path.get_text(), self.window.plan_users.get_text())
                self.assertFalse(self.window.share_profile.get_sensitive())
                self.window.share_profile.set_selected(1)
                self.window.fill_share_profile()
                self.assertEqual((self.window.plan_name.get_text(), self.window.plan_path.get_text(), self.window.plan_users.get_text()), before)
                self.assertFalse(self.window.profile_fill.get_sensitive())

    def test_connection_sheet_demo_and_edit_invalidation_use_no_host(self):
        from unittest.mock import Mock, patch
        with patch('subprocess.run', side_effect=AssertionError('process')), \
                patch('socket.getaddrinfo', side_effect=AssertionError('DNS')):
            self.window.open_connection('Famille')
            sheet = self.window.connection_window
            self.addCleanup(sheet.destroy)
            self.assertIsNone(sheet.card)
            sheet.server.set_text('nas.local')
            sheet.generate()
            self.assertEqual(sheet.card.guides[1].address, 'smb://nas.local/Famille')
            clipboard = Mock()
            with patch('sambapilot.gtk_connection.ConnectionWindow.get_clipboard', return_value=clipboard):
                sheet.copy_address('macos')
                clipboard.set.assert_called_once_with('smb://nas.local/Famille')
                sheet.server.set_text('autre.local')
                self.assertIsNone(sheet.card)
                self.assertFalse(sheet.copy_buttons['macos'].get_sensitive())
                clipboard.reset_mock()
                sheet.copy_address('macos')
                clipboard.set.assert_not_called()

    def test_connection_sheet_refuses_bad_server_and_closes_on_source_change(self):
        self.window.open_connection('Famille')
        sheet = self.window.connection_window
        self.addCleanup(sheet.destroy)
        sheet.server.set_text('nas.local')
        sheet.generate()
        self.assertIsNotNone(sheet.card)
        sheet.server.set_text('smb://user:private-secret@nas/Famille')
        sheet.generate()
        self.assertIsNone(sheet.card)
        self.assertNotIn('private-secret', sheet.status.get_text())
        self.window.show_demo_shares()
        self.assertFalse(sheet.active)
        self.assertIsNone(self.window.connection_window)

    def test_connection_sheet_file_retains_read_date_and_is_invalidated_on_clear(self):
        from pathlib import Path
        import tempfile
        from sambapilot.inspection import read_configuration
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            path.write_text('[Docs]\npath = /srv/docs\n', encoding='utf-8')
            snapshot = read_configuration(str(path))
            self.window.file_shares_mode = True
            self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
            self.window.open_connection('Docs')
            sheet = self.window.connection_window
            self.addCleanup(sheet.destroy)
            sheet.server.set_text('192.0.2.10')
            sheet.generate()
            self.assertEqual(sheet.card.mode, 'file')
            self.assertEqual(sheet.card.read_at, snapshot.read_at)
            self.assertEqual(sheet.card.source_sha256, snapshot.sha256)
            self.window.clear_inspection()
            self.assertFalse(sheet.active)
            self.assertIsNone(self.window.connection_window)

    def test_dashboard_demo_profiles_do_not_consult_host(self):
        from unittest.mock import patch
        page = self.window.diagnostic_page
        with patch("sambapilot.gtk_diagnostic.HostProbe", side_effect=AssertionError("host")):
            for index, family in enumerate(("arch", "debian", "fedora")):
                page.distribution.set_selected(index)
                page.use_demo()
                self.assertEqual(page.report.environment.distribution_family, family)
                self.assertEqual(page.source, "demo")
                page.symptom.set_selected(2)
                text = page.help_output.get_buffer()
                self.assertIn("Impossible d’écrire", text.get_text(text.get_start_iter(), text.get_end_iter(), False))

    def test_dashboard_discards_local_result_after_return_to_demo_and_close(self):
        from dataclasses import replace
        from unittest.mock import patch
        page = self.window.diagnostic_page
        self.window.stack.set_visible_child_name("dashboard")
        original = page.report
        with patch("sambapilot.gtk_diagnostic.Thread"):
            page.examine_local()
        generation = page.generation
        self.assertIsNone(page.report)
        self.assertEqual(self.window.mode_label.get_text(), "Lecture seule")
        local = replace(original, mode="live")
        page.use_demo()
        page.receive_report(generation, local)
        self.assertEqual(page.report.mode, "demo")
        self.assertEqual(self.window.mode_label.get_text(), "Démonstration")
        page.close()
        page.receive_report(page.generation - 1, local)
        self.assertEqual(page.report.mode, "demo")

    def test_dashboard_local_failure_clears_help_and_keeps_other_sources_separate(self):
        from unittest.mock import patch
        page = self.window.diagnostic_page
        accesses = self.window.visible_decisions
        with patch("sambapilot.gtk_diagnostic.Thread"):
            page.examine_local()
        page.receive_report(page.generation, None)
        self.assertIsNone(page.report)
        self.assertIn("interrompue", page.status.get_text())
        self.assertEqual(self.window.visible_decisions, accesses)
        text = page.help_output.get_buffer()
        self.assertEqual(text.get_text(text.get_start_iter(), text.get_end_iter(), False), "")

    def test_installation_page_uses_selected_distribution_for_demo(self):
        page = self.window.installation_page
        page.distribution.set_selected(1)
        page.prepare_demo()
        self.assertEqual(page.current_plan.diagnostic.environment.distribution_family, "debian")
        self.assertIn("samba-common-bin", [package.name for package in page.current_plan.packages])

    def test_conflict_navigation_and_reset(self):
        self.window.show_conflicts(None)
        self.assertEqual(self.window.stack.get_visible_child_name(), "access")
        self.assertEqual(len(self.window.visible_decisions), 1)
        self.assertTrue(self.window.visible_decisions[0].conflicts)
        self.window.reset_filters()
        self.assertEqual(len(self.window.visible_decisions), 12)

    def test_empty_filter_clears_selection_and_can_be_reset(self):
        self.window.search.set_text("not-found")
        self.window.update_accesses()
        self.assertEqual(self.window.visible_decisions, ())
        self.assertIsNone(self.window.access_list.get_selected_row())
        self.window.reset_filters()
        self.assertEqual(len(self.window.visible_decisions), 12)

    def test_share_navigation_filters_the_same_report(self):
        self.window.show_share("Medias")
        self.assertEqual(len(self.window.visible_decisions), 4)
        self.assertTrue(all(row.share == "Medias" for row in self.window.visible_decisions))

    def test_create_form_preview_is_discarded_after_edit_and_cancel(self):
        self.window.open_share_plan("create")
        self.window.plan_name.set_text("Documents")
        self.window.plan_path.set_text("/srv/documents")
        self.window.plan_users.set_text("alex")
        self.window.preview_share_plan(None)
        self.assertIsNotNone(self.window.plan_session.current)
        self.assertIn("[Documents]", self.window.plan_session.current.candidate)
        self.window.plan_path.set_text("/srv/other")
        self.assertIsNone(self.window.plan_session.current)
        self.window.preview_share_plan(None)
        self.window.cancel_share_plan(None)
        self.assertIsNone(self.window.plan_session.current)
        self.assertEqual(self.window.plan_name.get_text(), "")
        self.assertEqual(self.window.stack.get_visible_child_name(), "shares")

    def test_edit_and_remove_use_existing_share_without_changing_demo(self):
        source = self.window.plan_session.source
        self.window.open_share_plan("update", "Medias")
        self.assertEqual(self.window.plan_path.get_text(), "/srv/partages/medias")
        self.window.plan_writable.set_active(True)
        self.window.preview_share_plan(None)
        self.assertEqual(self.window.plan_session.current.action, "update")
        self.window.open_share_plan("remove", "Medias")
        self.assertFalse(self.window.plan_path.get_sensitive())
        self.window.preview_share_plan(None)
        self.assertNotIn("[Medias]", self.window.plan_session.current.candidate)
        self.assertEqual(self.window.plan_session.source, source)
        self.assertEqual(len(self.window.visible_decisions), 12)

    def test_invalid_form_cannot_keep_previous_preview(self):
        self.window.open_share_plan("update", "Medias")
        self.window.preview_share_plan(None)
        self.assertIsNotNone(self.window.plan_session.current)
        self.window.plan_groups.set_text("")
        self.window.preview_share_plan(None)
        self.assertIsNone(self.window.plan_session.current)
        self.assertIn("refusé", self.window.plan_status.get_text())

    def test_inspection_example_does_not_replace_demo_or_plan_source(self):
        source = self.window.plan_session.source
        self.window.stack.set_visible_child_name("configuration")
        self.window.inspect_configuration_example(None)
        self.assertEqual(len(self.window.inspection_report.shares), 3)
        self.assertEqual(self.window.mode_label.get_text(), "Lecture seule")
        self.assertEqual(self.window.plan_session.source, source)
        self.assertEqual(len(self.window.visible_decisions), 12)
        self.window.stack.set_visible_child_name("dashboard")
        self.assertEqual(self.window.mode_label.get_text(), "Démonstration")

    def test_stale_inspection_result_cannot_overwrite_newer_report(self):
        from sambapilot.demo import demo_configuration
        from sambapilot.inspection import inspect_content
        generation = self.window.inspection_generation
        report = inspect_content(demo_configuration())
        self.window.clear_inspection()
        self.window.receive_inspection(generation, report)
        self.assertIsNone(self.window.inspection_report)
        self.window.receive_inspection(self.window.inspection_generation, report)
        self.assertIsNotNone(self.window.inspection_report)
        self.window.receive_inspection(self.window.inspection_generation, None, "Lecture refusée")
        self.assertIsNone(self.window.inspection_report)
        self.assertIn("refusée", self.window.inspection_status.get_text())

    def test_file_plan_prefill_cancel_and_demo_remain_separate(self):
        from pathlib import Path
        import tempfile
        from sambapilot.demo import demo_configuration
        from sambapilot.inspection import read_configuration
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "smb.conf"
            source.write_text(demo_configuration(), encoding="utf-8")
            snapshot = read_configuration(str(source))
            self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
            self.window.config_share.set_selected(self.window.config_share_names.index("Medias"))
            self.window.open_file_share_plan("update")
            self.assertEqual(self.window.mode_label.get_text(), "Aperçu fichier")
            self.assertEqual(self.window.plan_path.get_text(), "/srv/partages/medias")
            self.window.preview_share_plan(None)
            self.assertEqual(self.window.plan_session.current.mode, "file")
            self.window.cancel_share_plan(None)
            self.assertEqual(self.window.stack.get_visible_child_name(), "configuration")
            self.assertEqual(self.window.plan_session.mode, "demo")
            self.assertEqual(len(self.window.visible_decisions), 12)

    def test_changed_file_refuses_preview_and_clearing_discards_file_session(self):
        from pathlib import Path
        import tempfile
        from sambapilot.demo import demo_configuration
        from sambapilot.inspection import read_configuration
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "smb.conf"
            source.write_text(demo_configuration(), encoding="utf-8")
            snapshot = read_configuration(str(source))
            self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
            self.window.open_file_share_plan("remove")
            self.window.preview_share_plan(None)
            self.assertIsNotNone(self.window.plan_session.current)
            source.write_text(demo_configuration() + "# changed\n", encoding="utf-8")
            self.window.preview_share_plan(None)
            self.assertIsNone(self.window.plan_session.current)
            self.assertIn("changé", self.window.plan_status.get_text())
            self.window.clear_inspection()
            self.assertEqual(self.window.plan_session.mode, "demo")
            self.assertFalse(self.window.config_create.get_sensitive())

    def test_validation_is_bound_to_current_preview_and_discarded_on_edit(self):
        from sambapilot.validation import ValidationResult
        self.window.open_share_plan("update", "Medias")
        self.assertFalse(self.window.validation_button.get_sensitive())
        self.window.preview_share_plan(None)
        plan = self.window.plan_session.current
        self.assertTrue(self.window.validation_button.get_sensitive())
        generation = self.window.validation_generation
        accepted = ValidationResult("accepted", plan.candidate_sha256, "Résultat simulé")
        self.window.receive_validation(generation, plan, accepted)
        self.assertEqual(self.window.plan_validation, accepted)
        self.window.plan_path.set_text("/srv/new")
        self.assertIsNone(self.window.plan_validation)
        self.assertFalse(self.window.validation_button.get_sensitive())
        self.window.receive_validation(generation, plan, accepted)
        self.assertIsNone(self.window.plan_validation)

    def test_stale_validation_clears_candidate_without_applying_anything(self):
        from sambapilot.validation import ValidationResult
        self.window.open_share_plan("update", "Medias")
        self.window.preview_share_plan(None)
        plan = self.window.plan_session.current
        stale = ValidationResult("stale", plan.candidate_sha256, "Source modifiée")
        self.window.receive_validation(self.window.validation_generation, plan, stale)
        self.assertIsNone(self.window.plan_session.current)
        self.assertEqual(self.window.plan_validation.status, "stale")
        self.assertFalse(self.window.validation_button.get_sensitive())

    def test_installation_examples_remain_descriptive_and_do_not_mix_sources(self):
        from unittest.mock import patch
        page = self.window.installation_page
        self.window.stack.set_visible_child_name("installation")
        with patch("subprocess.run", side_effect=AssertionError("process")):
            page.scenario.set_selected(0)
            page.prepare_demo()
            self.assertEqual(page.current_plan.packages[0].status, "missing")
            self.assertFalse(page.current_plan.can_apply)
            page.scenario.set_selected(1)
            page.prepare_demo()
            self.assertEqual(page.current_plan.packages[0].status, "installed")
        self.assertEqual(self.window.mode_label.get_text(), "Démonstration")

    def test_installation_stale_local_result_is_ignored(self):
        from dataclasses import replace
        page = self.window.installation_page
        old_generation = page.generation
        old_result = replace(page.current_plan, mode="live")
        page.prepare_demo()
        page.receive_plan(old_generation, old_result)
        self.assertEqual(page.current_plan.mode, "demo")
        page.source = "live"
        self.window.stack.set_visible_child_name("installation")
        self.window.update_mode_banner()
        self.assertEqual(self.window.mode_label.get_text(), "Lecture seule")
        page.receive_plan(page.generation, None)
        self.assertIsNone(page.current_plan)

    def test_firewall_has_no_default_scope_and_invalidates_after_edit(self):
        from unittest.mock import patch
        editor = self.window.firewall_editor
        self.assertIsNone(editor.current_plan)
        self.assertEqual(editor.manager.get_selected(), 0)
        self.assertEqual(editor.sources.get_text(), "")
        self.assertFalse(editor.legacy.get_active())
        self.window.stack.set_visible_child_name("firewall")
        self.assertEqual(self.window.mode_label.get_text(), "Aperçu réseau")
        editor.manager.set_selected(1)
        editor.interface.set_text("enp3s0")
        editor.sources.set_text("192.168.1.0/24")
        with patch("subprocess.run", side_effect=AssertionError("process")):
            editor.preview()
        self.assertIsNotNone(editor.current_plan)
        self.assertEqual(len(editor.current_plan.rules), 1)
        editor.sources.set_text("192.168.2.0/24")
        self.assertIsNone(editor.current_plan)

    def test_firewall_zone_validation_and_cancellation(self):
        editor = self.window.firewall_editor
        editor.manager.set_selected(2)
        self.assertTrue(editor.zone.get_sensitive())
        editor.interface.set_text("enp3s0")
        editor.sources.set_text("192.168.1.0/24")
        editor.preview()
        self.assertIsNone(editor.current_plan)
        editor.zone.set_text("home")
        editor.preview()
        self.assertIsNotNone(editor.current_plan)
        editor.reset()
        self.assertIsNone(editor.current_plan)
        self.assertEqual(editor.sources.get_text(), "")
        self.assertFalse(editor.zone.get_sensitive())

    def test_file_shares_are_explicit_and_demo_accesses_remain_separate(self):
        from pathlib import Path
        import tempfile
        from sambapilot.inspection import read_configuration
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'smb.conf'
            source.write_text('[UniqueFileShare]\npath = /srv/unique\n', encoding='utf-8')
            snapshot = read_configuration(str(source))
            self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
            self.assertFalse(self.window.file_shares_mode)
            self.assertIsNone(self.window.declared_shares_view)
            self.assertTrue(self.window.config_show_shares.get_sensitive())
            self.window.show_file_shares()
            self.assertEqual(self.window.stack.get_visible_child_name(), 'shares')
            self.assertEqual(self.window.mode_label.get_text(), 'Lecture seule')
            self.assertIn(str(source), self.window.shares_origin.get_text())
            self.assertEqual([share.name for share in self.window.declared_shares_view.shares], ['UniqueFileShare'])
            self.assertEqual(len(self.window.visible_decisions), 12)
            self.window.show_declared_share('UniqueFileShare')
            self.assertEqual(self.window.config_share_names[self.window.config_share.get_selected()], 'UniqueFileShare')
            self.assertEqual(self.window.stack.get_visible_child_name(), 'configuration')

    def test_return_to_examples_preserves_inspection_and_demo_actions(self):
        from sambapilot.inspection import ConfigurationSnapshot
        from sambapilot.planning import digest
        content = '[Chosen]\npath = /srv/chosen\n'
        snapshot = ConfigurationSnapshot('/chosen/smb.conf', content, digest(content))
        self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
        self.window.show_file_shares()
        self.window.show_demo_shares()
        self.assertFalse(self.window.file_shares_mode)
        self.assertIsNone(self.window.declared_shares_view)
        self.assertEqual(self.window.inspection_snapshot, snapshot)
        self.assertEqual(self.window.mode_label.get_text(), 'Démonstration')
        self.window.open_share_plan('update', 'Medias')
        self.assertEqual(self.window.plan_session.mode, 'demo')
        self.assertEqual(self.window.plan_path.get_text(), '/srv/partages/medias')

    def test_clear_error_and_old_result_cannot_leave_file_shares_visible(self):
        from sambapilot.inspection import ConfigurationSnapshot
        from sambapilot.planning import digest
        content = '[Chosen]\npath = /srv/chosen\n'
        snapshot = ConfigurationSnapshot('/chosen/smb.conf', content, digest(content))
        generation = self.window.inspection_generation
        self.window.receive_inspection(generation, snapshot.inspect(), snapshot=snapshot)
        self.window.show_file_shares()
        self.window.clear_inspection()
        self.window.receive_inspection(generation, snapshot.inspect(), snapshot=snapshot)
        self.assertIsNone(self.window.declared_shares_view)
        self.assertTrue(self.window.file_shares_mode)
        self.assertFalse(self.window.shares_reload.get_sensitive())
        self.assertFalse(self.window.config_show_shares.get_sensitive())
        self.window.receive_inspection(self.window.inspection_generation, None, 'Fichier inaccessible')
        self.assertIsNone(self.window.declared_shares_view)
        self.assertIn('inaccessible', self.window.shares_status.get_text())

    def test_blocked_file_shares_keep_explanations_without_demo_fallback(self):
        from sambapilot.inspection import ConfigurationSnapshot
        from sambapilot.planning import digest
        content = '[Docs]\npath = /srv/docs\n[Docs]\npath = /srv/other\n'
        snapshot = ConfigurationSnapshot('/chosen/ambiguous.conf', content, digest(content))
        self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
        self.window.show_file_shares()
        self.assertEqual(self.window.declared_shares_view.shares, ())
        self.assertIn('Analyse bloquée', self.window.shares_status.get_text())
        self.assertIn('ambiguous.conf', self.window.shares_origin.get_text())
        self.assertFalse(self.window.config_create.get_sensitive())

    def test_reload_discards_old_shares_before_reading_and_can_return_to_examples(self):
        from sambapilot.inspection import ConfigurationSnapshot
        from sambapilot.planning import digest
        from unittest.mock import patch
        content = '[Chosen]\npath = /srv/chosen\n'
        snapshot = ConfigurationSnapshot('/chosen/smb.conf', content, digest(content))
        self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
        self.window.show_file_shares()
        with patch('sambapilot.gtk_app.Thread') as thread:
            self.window.reload_shares_configuration(None)
            self.assertIsNone(self.window.declared_shares_view)
            self.assertIn('Lecture', self.window.shares_status.get_text())
            self.assertEqual(thread.call_args.kwargs['args'][0], '/chosen/smb.conf')
        self.window.show_demo_shares()
        self.assertEqual(self.window.mode_label.get_text(), 'Démonstration')


    def test_cancelled_file_selection_leaves_no_old_shares_or_demo_fallback(self):
        from gi.repository import GLib
        from unittest.mock import Mock
        self.window.file_shares_mode = True
        self.window.clear_inspection()
        dialog = Mock()
        dialog.open_finish.side_effect = GLib.Error("Sélection annulée")
        self.window.configuration_selected(dialog, None, self.window.inspection_generation)
        self.assertIsNone(self.window.declared_shares_view)
        self.assertTrue(self.window.file_shares_mode)
        self.assertIn('annulée', self.window.shares_status.get_text())
        self.assertEqual(self.window.plan_session.mode, 'demo')


    def test_declared_share_filters_intersect_and_reset_without_changing_source(self):
        from sambapilot.inspection import ConfigurationSnapshot
        from sambapilot.planning import digest
        content = '[Alpha]\npath = /a\nvfs objects = recycle\n[Beta]\npath = /b\n'
        snapshot = ConfigurationSnapshot('/chosen/smb.conf', content, digest(content))
        self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
        self.window.show_file_shares()
        self.window.shares_category.set_selected(3)
        self.assertEqual([row.name for row in self.window.visible_declared_shares], ['Alpha'])
        self.window.shares_query.set_text('beta')
        self.window.refresh_shares()
        self.assertEqual(self.window.visible_declared_shares, ())
        self.assertIn('0 déclaration(s) affichée(s) sur 2', self.window.shares_status.get_text())
        self.window.reset_declared_share_filters()
        self.assertEqual(len(self.window.visible_declared_shares), 2)
        self.assertEqual(self.window.inspection_snapshot, snapshot)
        self.assertEqual(len(self.window.visible_decisions), 12)
        self.window.clear_inspection()
        self.assertEqual(self.window.shares_query.get_text(), '')
        self.assertFalse(self.window.shares_query.get_sensitive())
        self.assertEqual(self.window.visible_declared_shares, ())

    def test_only_writer_supported_declarations_offer_direct_modification(self):
        from pathlib import Path
        import tempfile
        from sambapilot.inspection import read_configuration
        content = ('[Supported]\npath = /srv/docs\nread only = yes\nbrowseable = yes\n'
                   'guest ok = no\nvalid users = alex\n[Incomplete]\npath = /srv/other\n')
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'smb.conf'
            source.write_text(content, encoding='utf-8')
            snapshot = read_configuration(str(source))
            self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
            self.window.show_file_shares()
            self.assertTrue(self.window.declared_share_actions['Supported'].get_sensitive())
            self.assertFalse(self.window.declared_share_actions['Incomplete'].get_sensitive())
            self.window.prepare_declared_share('Supported')
            self.assertEqual(self.window.stack.get_visible_child_name(), 'prepare')
            self.assertEqual(self.window.plan_session.mode, 'file')
            self.assertEqual(self.window.plan_name.get_text(), 'Supported')
            self.window.preview_share_plan(None)
            self.assertIsNotNone(self.window.plan_session.current)
            self.assertFalse(self.window.plan_session.current.can_apply)
            self.assertEqual(source.read_text(encoding='utf-8'), content)

    def test_direct_modification_refusal_clears_preview_and_is_visible_on_shares_page(self):
        from sambapilot.inspection import ConfigurationSnapshot
        from sambapilot.planning import digest
        content = '[Incomplete]\npath = /srv/other\n'
        snapshot = ConfigurationSnapshot('/chosen/smb.conf', content, digest(content))
        self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
        self.window.open_share_plan('update', 'Medias')
        self.window.preview_share_plan(None)
        self.assertIsNotNone(self.window.plan_session.current)
        self.window.show_file_shares()
        self.window.prepare_declared_share('Incomplete')
        self.assertIsNone(self.window.plan_session.current)
        self.assertEqual(self.window.stack.get_visible_child_name(), 'shares')
        self.assertIn('Préparation refusée', self.window.shares_status.get_text())
        self.window.prepare_declared_share('absent')
        self.assertIn('Préparation refusée', self.window.shares_status.get_text())


    def test_export_preview_includes_entire_inventory_independently_of_filters(self):
        from sambapilot.inspection import ConfigurationSnapshot
        from sambapilot.planning import digest
        content = '[Alpha]\npath = /srv/a\n[Beta]\npath = /srv/b\n'
        snapshot = ConfigurationSnapshot('/chosen/smb.conf', content, digest(content))
        self.assertFalse(self.window.config_export.get_sensitive())
        self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
        self.window.show_file_shares()
        self.window.shares_query.set_text('Alpha')
        self.window.refresh_shares()
        self.assertEqual(len(self.window.visible_declared_shares), 1)
        self.assertTrue(self.window.shares_export.get_sensitive())
        self.window.open_report_export()
        preview = self.window.report_export_window
        self.assertTrue(preview.is_current())
        self.assertIn('### Alpha', preview.prepared.markdown)
        self.assertIn('### Beta', preview.prepared.markdown)
        self.assertFalse(preview.preview.get_editable())

    def test_export_save_uses_preview_bytes_and_refuses_existing_destination(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import Mock
        self.window.inspect_configuration_example(None)
        self.window.open_report_export()
        preview = self.window.report_export_window
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rapport.md'
            dialog = Mock()
            dialog.save_finish.return_value.get_path.return_value = str(path)
            preview.destination_selected(dialog, None)
            self.assertEqual(path.read_text(encoding='utf-8'), preview.prepared.markdown)
            preview.destination_selected(dialog, None)
            self.assertIn('existe déjà', preview.status.get_text())
            self.assertEqual(path.read_text(encoding='utf-8'), preview.prepared.markdown)

    def test_export_callback_after_source_clear_cannot_create_a_file(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import Mock
        self.window.inspect_configuration_example(None)
        self.window.open_report_export()
        preview = self.window.report_export_window
        self.window.clear_inspection()
        self.assertIsNone(self.window.report_export_window)
        self.assertFalse(self.window.config_export.get_sensitive())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'obsolete.md'
            dialog = Mock()
            dialog.save_finish.return_value.get_path.return_value = str(path)
            preview.destination_selected(dialog, None)
            self.assertFalse(path.exists())

    def test_export_cancel_and_preview_close_do_not_write(self):
        from gi.repository import GLib
        from unittest.mock import Mock, patch
        self.window.inspect_configuration_example(None)
        self.window.open_report_export()
        preview = self.window.report_export_window
        dialog = Mock()
        dialog.save_finish.side_effect = GLib.Error('Annulation')
        with patch('sambapilot.gtk_report.save_report', side_effect=AssertionError('write')):
            preview.destination_selected(dialog, None)
            self.assertIn('annulé', preview.status.get_text())
            preview.close()
            self.assertFalse(preview.is_current())


    def test_source_reload_review_and_adoption_preserve_exact_form_text(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from sambapilot.demo import demo_configuration
        from sambapilot.inspection import read_configuration
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            path.write_text(demo_configuration(), encoding='utf-8')
            snapshot = read_configuration(str(path))
            self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
            self.window.config_share.set_selected(self.window.config_share_names.index('Medias'))
            self.window.open_file_share_plan('update')
            self.window.plan_path.set_text('/srv/my-choice')
            self.window.plan_users.set_text(' alex, lea ')
            self.window.plan_groups.set_text(' famille ')
            self.window.plan_writable.set_active(True)
            self.window.plan_browseable.set_active(False)
            before = (self.window.plan_path.get_text(), self.window.plan_users.get_text(),
                      self.window.plan_groups.get_text(), self.window.plan_writable.get_active(),
                      self.window.plan_browseable.get_active())
            outside = demo_configuration().replace('/srv/partages/medias', '/srv/outside-change')
            path.write_text(outside, encoding='utf-8')
            metadata = path.stat().st_mtime_ns
            self.window.preview_share_plan(None)
            self.assertIsNone(self.window.plan_session.current)
            session = self.window.plan_session
            with patch('sambapilot.gtk_app.Thread'):
                self.window.request_source_reload(None)
            review = session.prepare_reload()
            self.window.receive_source_reload(self.window.source_reload_generation, session, review)
            self.assertEqual(session.snapshot.sha256, snapshot.sha256)
            self.assertTrue(self.window.source_adopt_button.get_sensitive())
            self.window.adopt_source_reload(None)
            after = (self.window.plan_path.get_text(), self.window.plan_users.get_text(),
                     self.window.plan_groups.get_text(), self.window.plan_writable.get_active(),
                     self.window.plan_browseable.get_active())
            self.assertEqual(after, before)
            self.assertIsNone(self.window.plan_session.current)
            self.assertIsNone(self.window.plan_validation)
            self.assertFalse(self.window.validation_button.get_sensitive())
            self.assertEqual(self.window.inspection_snapshot.sha256, self.window.plan_session.snapshot.sha256)
            self.window.preview_share_plan(None)
            self.assertIn('/srv/my-choice', self.window.plan_session.current.candidate)
            self.assertIn('/srv/outside-change', self.window.plan_session.current.diff)
            self.assertEqual(path.read_text(encoding='utf-8'), outside)
            self.assertEqual(path.stat().st_mtime_ns, metadata)

    def test_obsolete_reload_result_after_cancellation_is_ignored(self):
        from pathlib import Path
        import tempfile
        from unittest.mock import patch
        from sambapilot.demo import demo_configuration
        from sambapilot.inspection import read_configuration
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            path.write_text(demo_configuration(), encoding='utf-8')
            snapshot = read_configuration(str(path))
            self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
            self.window.open_file_share_plan('create')
            session = self.window.plan_session
            with patch('sambapilot.gtk_app.Thread'):
                self.window.request_source_reload(None)
            generation = self.window.source_reload_generation
            review = session.prepare_reload()
            self.window.cancel_share_plan(None)
            self.window.receive_source_reload(generation, session, review)
            self.assertIsNone(self.window.source_reload_review)
            self.assertEqual(self.window.plan_session.mode, 'demo')
            self.assertFalse(self.window.source_adopt_button.get_sensitive())
            self.assertFalse(self.window.source_reload_button.get_sensitive())

    def test_second_source_change_refuses_adoption_without_losing_form(self):
        from pathlib import Path
        import tempfile
        from sambapilot.demo import demo_configuration
        from sambapilot.inspection import read_configuration
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            path.write_text(demo_configuration(), encoding='utf-8')
            snapshot = read_configuration(str(path))
            self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
            self.window.open_file_share_plan('create')
            self.window.plan_name.set_text('Documents')
            self.window.plan_users.set_text('invalid, raw, ; input')
            session = self.window.plan_session
            review = session.prepare_reload()
            self.window.receive_source_reload(self.window.source_reload_generation, session, review)
            path.write_text(demo_configuration() + '# another change\n', encoding='utf-8')
            self.window.adopt_source_reload(None)
            self.assertIs(self.window.plan_session, session)
            self.assertEqual(self.window.plan_users.get_text(), 'invalid, raw, ; input')
            self.assertIn('encore changé', self.window.source_reload_status.get_text())
            self.assertIsNone(self.window.source_reload_review)
            self.assertFalse(self.window.source_adopt_button.get_sensitive())
            self.assertTrue(self.window.source_reload_button.get_sensitive())

    def test_reload_failure_preserves_even_invalid_input_and_keeps_preview_disabled(self):
        from pathlib import Path
        import tempfile
        from sambapilot.demo import demo_configuration
        from sambapilot.inspection import read_configuration
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'smb.conf'
            path.write_text(demo_configuration(), encoding='utf-8')
            snapshot = read_configuration(str(path))
            self.window.receive_inspection(self.window.inspection_generation, snapshot.inspect(), snapshot=snapshot)
            self.window.open_file_share_plan('create')
            self.window.plan_path.set_text('not yet a valid path')
            self.window.receive_source_reload(self.window.source_reload_generation, self.window.plan_session,
                                              None, 'Fichier illisible')
            self.assertEqual(self.window.plan_path.get_text(), 'not yet a valid path')
            self.assertIn('Saisie conservée', self.window.source_reload_status.get_text())
            self.assertIsNone(self.window.plan_session.current)
            self.assertFalse(self.window.validation_button.get_sensitive())
            self.assertFalse(self.window.source_adopt_button.get_sensitive())


if __name__ == "__main__":
    unittest.main()
