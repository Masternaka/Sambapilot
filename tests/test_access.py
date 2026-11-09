import contextlib
from dataclasses import replace
import io
import json
import unittest
from unittest.mock import patch

from sambapilot.access import FileAccess, Share, User, build_matrix, evaluate
from sambapilot.cli import main, render_access
from sambapilot.demo import access_demo


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.user = User("alex", ("famille",), True)
        self.share = Share("Documents", "/srv/documents", allowed_groups=("famille",), read_only=False)
        self.files = FileAccess("alex", "Documents", True, True, True, "Données de test.")

    def test_allowed_group_and_files_allow_read_and_write(self):
        decision = evaluate(self.user, self.share, self.files)
        self.assertIs(decision.read, True)
        self.assertIs(decision.write, True)
        self.assertEqual(decision.conflicts, ())

    def test_read_only_share_keeps_linux_write_rights_distinct(self):
        decision = evaluate(self.user, replace(self.share, read_only=True), self.files)
        self.assertIs(decision.read, True)
        self.assertIs(decision.write, False)
        self.assertIs(decision.filesystem_write, True)
        self.assertEqual(decision.conflicts, ())

    def test_explicit_writer_overrides_read_only(self):
        for exceptions in ({"write_users": ("alex",)}, {"write_groups": ("famille",)}):
            with self.subTest(exceptions=exceptions):
                share = replace(self.share, read_only=True, **exceptions)
                self.assertIs(evaluate(self.user, share, self.files).write, True)

    def test_write_exception_never_bypasses_share_access_list(self):
        share = replace(self.share, allowed_users=("lea",), allowed_groups=(),
                        read_only=True, write_users=("alex",))
        decision = evaluate(self.user, share, self.files)
        self.assertIs(decision.read, False)
        self.assertIs(decision.write, False)

    def test_no_access_list_still_requires_enabled_account(self):
        share = replace(self.share, allowed_groups=())
        self.assertIs(evaluate(self.user, share, self.files).read, True)
        self.assertIsNone(evaluate(replace(self.user, samba_enabled=None), share, self.files).read)
        self.assertIs(evaluate(replace(self.user, samba_enabled=False), share, self.files).read, False)

    def test_unknown_groups_are_not_treated_as_empty_groups(self):
        self.assertIsNone(evaluate(replace(self.user, groups=None), self.share, self.files).read)
        self.assertIs(evaluate(replace(self.user, groups=()), self.share, self.files).read, False)

    def test_explicit_user_does_not_require_known_groups(self):
        share = replace(self.share, allowed_users=("alex",))
        self.assertIs(evaluate(replace(self.user, groups=None), share, self.files).read, True)

    def test_unknown_write_group_does_not_hide_known_read_access(self):
        share = replace(self.share, allowed_users=("alex",), read_only=True, write_groups=("editors",))
        decision = evaluate(replace(self.user, groups=None), share, self.files)
        self.assertIs(decision.read, True)
        self.assertIsNone(decision.write)

    def test_linux_write_denied_is_reported_as_conflict(self):
        decision = evaluate(self.user, self.share, replace(self.files, write=False))
        self.assertIs(decision.read, True)
        self.assertIs(decision.write, False)
        self.assertEqual(len(decision.conflicts), 1)
        self.assertIn("écriture", decision.conflicts[0])

    def test_unknown_permissions_never_imply_granted_access(self):
        decision = evaluate(self.user, self.share, FileAccess("alex", "Documents"))
        self.assertIsNone(decision.read)
        self.assertIsNone(decision.write)
        self.assertIs(decision.samba_read, True)

    def test_known_denial_survives_missing_information(self):
        decision = evaluate(replace(self.user, samba_enabled=None), self.share,
                            replace(self.files, traverse=False))
        self.assertIs(decision.read, False)
        self.assertIs(decision.write, False)

    def test_missing_traversal_blocks_conclusions(self):
        decision = evaluate(self.user, self.share, replace(self.files, traverse=None))
        self.assertIsNone(decision.read)
        self.assertIsNone(decision.write)

    def test_write_without_read_is_representable(self):
        decision = evaluate(self.user, self.share, replace(self.files, read=False))
        self.assertIs(decision.read, False)
        self.assertIs(decision.write, True)

    def test_unsupported_options_prevent_claiming_access(self):
        share = replace(self.share, unsupported_options=("force user", "read list"))
        decision = evaluate(self.user, share, self.files)
        self.assertIsNone(decision.read)
        self.assertIsNone(decision.write)
        self.assertIsNone(decision.filesystem_read)
        self.assertIn("force user", decision.reasons[0])

    def test_disabled_share_denies_without_filesystem_facts(self):
        decision = evaluate(self.user, replace(self.share, enabled=False), FileAccess("alex", "Documents"))
        self.assertIs(decision.read, False)
        self.assertIs(decision.write, False)

    def test_observations_cannot_be_used_for_another_identity(self):
        for facts in (replace(self.files, user="lea"), replace(self.files, share="Other")):
            with self.subTest(facts=facts), self.assertRaises(ValueError):
                evaluate(self.user, self.share, facts)

    def test_missing_observations_produce_unknown_matrix_entries(self):
        report = build_matrix((self.user,), (self.share,), ())
        self.assertEqual(len(report.decisions), 1)
        self.assertIsNone(report.decisions[0].read)
        self.assertIsNone(report.decisions[0].write)

    def test_duplicate_names_and_observations_are_rejected(self):
        for users, shares, facts in (
            ((self.user, self.user), (self.share,), ()),
            ((self.user,), (self.share, self.share), ()),
            ((self.user,), (self.share,), (self.files, self.files)),
        ):
            with self.subTest(users=users, shares=shares, facts=facts), self.assertRaises(ValueError):
                build_matrix(users, shares, facts)

    def test_unreferenced_observations_are_rejected(self):
        with self.assertRaises(ValueError):
            build_matrix((self.user,), (self.share,), (replace(self.files, share="Other"),))

    def test_permissions_demo_has_no_host_access_and_json_keeps_null(self):
        with patch("sambapilot.cli.HostProbe", side_effect=AssertionError("host")), \
                patch("subprocess.run", side_effect=AssertionError("process")), \
                patch("pathlib.Path.open", side_effect=AssertionError("open")), \
                patch("pathlib.Path.stat", side_effect=AssertionError("stat")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["permissions", "--demo", "--json"]), 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["mode"], "demo")
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(len(data["decisions"]), 12)
        self.assertTrue(any(row["read"] is None for row in data["decisions"]))
        self.assertTrue(any(row["conflicts"] for row in data["decisions"]))

    def test_permissions_command_requires_explicit_demo(self):
        with patch("sambapilot.cli.HostProbe", side_effect=AssertionError("host")), \
                contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            main(["permissions"])
        self.assertEqual(caught.exception.code, 2)

    def test_terminal_includes_layers_and_sanitizes_identity_and_path(self):
        user = replace(self.user, name="alex\x1b[2J")
        share = replace(self.share, path="/srv/\x07docs", allowed_users=(user.name,))
        facts = replace(self.files, user=user.name)
        text = render_access(build_matrix((user,), (share,), (facts,)))
        self.assertNotIn("\x1b", text)
        self.assertNotIn("\x07", text)
        self.assertIn("Samba :", text)
        self.assertIn("fichiers :", text)

    def test_empty_matrix_and_demo_text_render(self):
        self.assertIn("Utilisateur", render_access(build_matrix((), (), ())))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["permissions", "--demo"]), 0)
        self.assertIn("DÉMONSTRATION", output.getvalue())
        self.assertIn("Conflit en écriture", output.getvalue())
        self.assertIn("inconnu", output.getvalue())


if __name__ == "__main__":
    unittest.main()
