import contextlib
from dataclasses import replace
import io
import json
import unittest
from unittest.mock import Mock, patch

from sambapilot.access import build_matrix
from sambapilot.cli import main
from sambapilot.demo import DemoProbe, access_demo
from sambapilot.diagnostic import collect
from sambapilot.gui import GtkUnavailable, launch_demo, load_gtk
from sambapilot.presentation import AccessFilters, DemoViewModel, decision_details, decision_status, right_text


class PresentationTests(unittest.TestCase):
    def setUp(self):
        self.model = DemoViewModel.create()

    def test_gui_reuses_the_same_reports_as_terminal(self):
        self.assertEqual(self.model.diagnostic, collect(DemoProbe("configured")))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            main(["permissions", "--demo", "--json"])
        self.assertEqual(json.loads(json.dumps(self.model.accesses.to_dict())), json.loads(output.getvalue()))

    def test_creating_view_model_never_probes_host(self):
        with patch("pathlib.Path.open", side_effect=AssertionError("open")), \
                patch("pathlib.Path.stat", side_effect=AssertionError("stat")), \
                patch("subprocess.run", side_effect=AssertionError("process")):
            model = DemoViewModel.create()
        self.assertEqual(model.users, ("alex", "inconnu", "lea", "visiteur"))
        self.assertEqual(model.shares, ("Famille", "Medias", "Prive"))
        self.assertEqual(model.conflict_count, 1)
        self.assertEqual(model.unknown_count, 2)

    def test_live_report_cannot_be_used_in_demo_window(self):
        with self.assertRaises(ValueError):
            DemoViewModel(replace(self.model.diagnostic, mode="live"), self.model.accesses)
        with self.assertRaises(ValueError):
            DemoViewModel(self.model.diagnostic, replace(self.model.accesses, mode="declared"))

    def test_combined_filters_do_not_mix_users_or_shares(self):
        rows = self.model.filtered(AccessFilters(user="lea", share="Medias"))
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0].user, rows[0].share), ("lea", "Medias"))
        self.assertIs(rows[0].write, False)

    def test_conflict_filter_does_not_include_normal_read_only_access(self):
        rows = self.model.filtered(AccessFilters(conflicts_only=True))
        self.assertEqual([(row.user, row.share) for row in rows], [("alex", "Famille")])

    def test_search_is_case_insensitive_and_matches_paths(self):
        rows = self.model.filtered(AccessFilters(query="  /SRV/PARTAGES/MEDIAS  "))
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row.share == "Medias" for row in rows))
        self.assertEqual(len(self.model.filtered(AccessFilters(query="LEA"))), 3)

    def test_empty_results_do_not_fall_back_to_all_accesses(self):
        self.assertEqual(self.model.filtered(AccessFilters(user="lea", conflicts_only=True)), ())
        self.assertEqual(self.model.filtered(AccessFilters(query="does-not-exist")), ())
        self.assertEqual(len(self.model.filtered(AccessFilters())), 12)

    def test_empty_matrix_has_zero_counts(self):
        model = replace(self.model, accesses=build_matrix((), (), (), mode="demo"))
        self.assertEqual(model.users, ())
        self.assertEqual(model.shares, ())
        self.assertEqual(model.conflict_count, 0)
        self.assertEqual(model.unknown_count, 0)

    def test_unknown_rights_and_layers_are_explained(self):
        row = self.model.filtered(AccessFilters(user="inconnu", share="Famille"))[0]
        self.assertEqual(decision_status(row), "À vérifier")
        self.assertEqual(right_text(None), "Inconnu")
        text = decision_details(row)
        self.assertIn("Lecture estimée : Inconnu", text)
        self.assertIn("Règles Samba déclarées", text)
        self.assertIn("Permissions de fichiers déclarées", text)
        self.assertIn("aucun accès réel", text)

    def test_conflict_details_keep_linux_and_samba_distinct(self):
        row = self.model.filtered(AccessFilters(conflicts_only=True))[0]
        self.assertEqual(decision_status(row), "Conflit")
        self.assertIn("Conflit en écriture", decision_details(row))
        self.assertEqual(right_text(False), "Refusé")


class GuiLaunchTests(unittest.TestCase):
    def test_missing_gtk_is_reported_without_launching_application(self):
        with patch("sambapilot.gui.load_gtk", side_effect=GtkUnavailable("Dépendance manquante")), \
                contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(launch_demo(), 3)
        self.assertIn("Dépendance manquante", output.getvalue())

    def test_no_display_is_reported_without_importing_app(self):
        gtk = Mock()
        gtk.init_check.return_value = False
        with patch("sambapilot.gui.load_gtk", return_value=gtk), \
                contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(launch_demo(), 3)
        self.assertIn("session graphique", output.getvalue())

    def test_optional_import_failure_has_actionable_message(self):
        with patch.dict("sys.modules", {"gi": None}), self.assertRaises(GtkUnavailable) as caught:
            load_gtk()
        self.assertIn("4.10", str(caught.exception))
        self.assertIn("Aucune installation", str(caught.exception))

    def test_old_gtk_is_rejected_before_creating_a_window(self):
        gtk = Mock()
        gtk.check_version.return_value = "GTK trop ancien"
        gi = Mock()
        repository = Mock(Gtk=gtk)
        with patch.dict("sys.modules", {"gi": gi, "gi.repository": repository}), \
                self.assertRaises(GtkUnavailable):
            load_gtk()

    def test_gui_requires_demo_and_routes_only_to_graphical_launcher(self):
        with patch("sambapilot.gui.launch_demo", return_value=0) as launch, \
                patch("sambapilot.cli.HostProbe", side_effect=AssertionError("host")):
            self.assertEqual(main(["gui", "--demo"]), 0)
            launch.assert_called_once_with()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["gui"])
        self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
