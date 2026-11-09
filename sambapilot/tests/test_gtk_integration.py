"""Essais GTK réels sur demande, avec GTK installé et une session graphique."""

import os
import unittest


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
        self.app = self.Gtk.Application(application_id="io.github.sambapilot.Tests",
                                        flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.app.register(None)
        self.window = SambaPilotWindow(self.app, DemoViewModel.create())

    def tearDown(self):
        self.window.destroy()
        self.app.quit()

    def test_window_builds_all_pages_and_initial_selection(self):
        for name in ("dashboard", "installation", "shares", "access", "prepare", "configuration", "firewall", "maintenance"):
            self.assertIsNotNone(self.window.stack.get_child_by_name(name))
        self.assertEqual(len(self.window.visible_decisions), 12)
        self.assertIsNotNone(self.window.access_list.get_selected_row())

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


if __name__ == "__main__":
    unittest.main()
