import contextlib
from dataclasses import replace
import io
import json
import unittest
from unittest.mock import patch

from sambapilot.cli import main
from sambapilot.demo import access_demo, demo_configuration, demo_shares
from sambapilot.planning import (PlanError, PlanSession, ShareDraft, format_plan,
                                parse_identities, prepare_plan, render_section, scan_sections)


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.source = demo_configuration()
        self.draft = ShareDraft("Documents", "/srv/partages/documents", ("alex",), ("famille",))

    def test_create_preserves_all_existing_content_and_denies_guest(self):
        plan = prepare_plan(self.source, "create", self.draft.name, self.draft)
        self.assertTrue(plan.candidate.startswith(self.source))
        self.assertIn("valid users = alex +famille", plan.candidate)
        self.assertIn("[Documents]\n", plan.candidate)
        self.assertIn("+    guest ok = no", plan.diff)
        self.assertIn("+    read only = yes", plan.diff)
        self.assertFalse(plan.can_apply)

    def test_group_names_use_unix_only_prefix(self):
        content = render_section(replace(self.draft, users=()))
        self.assertIn("valid users = +famille", content)
        self.assertNotIn("@famille", content)

    def test_unicode_share_name_and_path_spaces_are_preserved(self):
        draft = replace(self.draft, name="Photos été", path="/srv/Photos été")
        plan = prepare_plan(self.source, "create", draft.name, draft)
        self.assertIn("[Photos été]", plan.candidate)
        self.assertIn("path = /srv/Photos été", plan.candidate)

    def test_duplicate_name_is_case_insensitive(self):
        draft = replace(self.draft, name="mEDIAS")
        with self.assertRaises(PlanError):
            prepare_plan(self.source, "create", draft.name, draft)

    def test_update_preserves_other_sections_and_target_comments(self):
        before = "# personnel\n[global]\n    workgroup = MAISON\n\n"
        target = "[Medias]\n# conserver ce commentaire\n    path = /old\n    read only = yes\n    comment = Mes films\n\n"
        after = "[Autre]\n    path = /other\n    vfs objects = fruit streams_xattr\n"
        draft = ShareDraft("Medias", "/srv/videos", groups=("famille",), read_only=False)
        plan = prepare_plan(before + target + after, "update", "Medias", draft)
        self.assertTrue(plan.candidate.startswith(before))
        self.assertTrue(plan.candidate.endswith(after))
        self.assertIn("# conserver ce commentaire\n", plan.candidate)
        self.assertIn("    comment = Mes films\n", plan.candidate)
        self.assertIn("    read only = no\n", plan.candidate)
        self.assertNotIn("path = /old", plan.candidate)
        self.assertEqual(plan.candidate.count("valid users = +famille"), 1)

    def test_no_op_update_has_no_diff(self):
        share = demo_shares()[0]
        draft = ShareDraft(share.name, share.path, share.allowed_users, share.allowed_groups, share.read_only)
        plan = prepare_plan(self.source, "update", share.name, draft)
        self.assertEqual(plan.candidate, self.source)
        self.assertEqual(plan.diff, "")
        self.assertIn("Aucun changement de contenu", format_plan(plan))

    def test_remove_only_deletes_the_target_section(self):
        plan = prepare_plan(self.source, "remove", "Medias")
        sections = {section.name for section in scan_sections(plan.candidate)}
        self.assertEqual(sections, {"global", "Famille", "Prive"})
        self.assertIn("[Famille]", plan.candidate)
        self.assertIn("conserver le dossier", plan.changes[0])
        self.assertFalse(plan.can_apply)

    def test_missing_update_or_remove_target_is_refused(self):
        for action, draft in (("remove", None), ("update", self.draft)):
            with self.subTest(action=action), self.assertRaises(PlanError):
                prepare_plan(self.source, action, self.draft.name, draft)

    def test_advanced_or_duplicate_target_options_are_refused_without_overwrite(self):
        for options in ("vfs objects = recycle", "read list = alex", "path = /duplicate", "writable = yes"):
            source = "[Documents]\npath = /srv/documents\n" + options + "\n"
            for action, draft in (("update", self.draft), ("remove", None)):
                with self.subTest(options=options, action=action), self.assertRaises(PlanError):
                    prepare_plan(source, action, "Documents", draft)

    def test_indirect_configurations_cannot_hide_duplicate_shares(self):
        for option in ("include = /other", "copy = other", "config file = /other", "registry shares = yes"):
            with self.subTest(option=option), self.assertRaises(PlanError):
                prepare_plan("[global]\n" + option + "\n", "create", self.draft.name, self.draft)

    def test_ambiguous_source_is_refused(self):
        for source in ("[Same]\npath = /a\n[same]\npath = /b\n", "path = /a\n",
                       "[Broken\n", "[global]\ninclude = \\\n  /other\n", "[global]\n\x1b[2J"):
            with self.subTest(source=source), self.assertRaises(PlanError):
                prepare_plan(source, "create", self.draft.name, self.draft)

    def test_reserved_and_injectable_share_names_are_refused(self):
        for name in ("global", "HOMES", "printers", "", " Name", "Name ", "Bad]\n[global", "x/y",
                     "x\\y", "%U", "name\x1b", "x" * 81):
            with self.subTest(name=name), self.assertRaises(PlanError):
                prepare_plan(self.source, "create", name, replace(self.draft, name=name))

    def test_unsafe_or_ambiguous_paths_are_refused(self):
        for path in ("", "relative", "/", "//srv/share", "/srv/../etc", "/srv/./x", "/srv/%U",
                     "/srv/x\n[global]", "/srv/x\\", '/srv/"x"', "/srv/x\t", "/srv/x "):
            with self.subTest(path=path), self.assertRaises(PlanError):
                prepare_plan(self.source, "create", self.draft.name, replace(self.draft, path=path))

    def test_empty_access_list_and_injectable_identities_are_refused(self):
        for users, groups in (((), ()), (("@famille",), ()), (("alex", "alex"), ()),
                              (("alex lea",), ()), ((), ("famille\nguest ok = yes",)), ((), ("+famille",))):
            with self.subTest(users=users, groups=groups), self.assertRaises(PlanError):
                prepare_plan(self.source, "create", self.draft.name,
                             replace(self.draft, users=users, groups=groups))

    def test_non_boolean_options_are_refused(self):
        for draft in (replace(self.draft, read_only="no"), replace(self.draft, browseable=1)):
            with self.subTest(draft=draft), self.assertRaises(PlanError):
                prepare_plan(self.source, "create", draft.name, draft)

    def test_hidden_and_writable_are_explicit_and_independent(self):
        draft = replace(self.draft, read_only=False, browseable=False)
        plan = prepare_plan(self.source, "create", draft.name, draft)
        self.assertIn("read only = no", plan.candidate)
        self.assertIn("browseable = no", plan.candidate)
        self.assertIn("guest ok = no", plan.candidate)
        self.assertTrue(any("accès directs" in note for note in plan.notes))

    def test_source_digest_detects_any_change(self):
        plan = prepare_plan(self.source, "create", self.draft.name, self.draft)
        self.assertTrue(plan.matches_source(self.source))
        self.assertFalse(plan.matches_source(self.source + "# externe\n"))
        self.assertNotEqual(plan.baseline_sha256, plan.candidate_sha256)

    def test_crlf_source_preserves_unmodified_bytes(self):
        source = self.source.replace("\n", "\r\n")
        plan = prepare_plan(source, "create", self.draft.name, self.draft)
        self.assertTrue(plan.candidate.startswith(source))
        self.assertNotIn("\n", plan.candidate.replace("\r\n", ""))

    def test_no_trailing_newline_still_produces_readable_diff(self):
        source = "[global]\nworkgroup = MAISON"
        plan = prepare_plan(source, "create", self.draft.name, self.draft)
        self.assertTrue(plan.candidate.startswith(source + "\n"))
        self.assertIn("\\ No newline at end of file\n", plan.diff)
        self.assertNotIn("MAISON+", plan.diff)

    def test_plan_session_invalidates_on_cancel_and_failed_preview(self):
        session = PlanSession(self.source)
        session.preview("create", self.draft.name, self.draft)
        session.discard()
        self.assertIsNone(session.current)
        session.preview("create", self.draft.name, self.draft)
        with self.assertRaises(PlanError):
            session.preview("create", "global", replace(self.draft, name="global"))
        self.assertIsNone(session.current)
        self.assertEqual(session.source, self.source)

    def test_form_identity_parser_does_not_silently_drop_empty_tokens(self):
        self.assertEqual(parse_identities(" alex, lea "), ("alex", "lea"))
        self.assertEqual(parse_identities(" "), ())
        for value in ("alex,", ",alex", "alex,,lea"):
            with self.subTest(value=value), self.assertRaises(PlanError):
                parse_identities(value)

    def test_demo_configuration_stays_consistent_with_access_matrix(self):
        sections = {section.name for section in scan_sections(self.source)} - {"global"}
        self.assertEqual(sections, {row.share for row in access_demo().decisions})

    def test_mismatched_draft_and_remove_with_settings_are_refused(self):
        for action, name, draft in (("update", "Famille", self.draft),
                                    ("remove", "Famille", self.draft),
                                    ("invalid", "Documents", self.draft)):
            with self.subTest(action=action), self.assertRaises(PlanError):
                prepare_plan(self.source, action, name, draft)

    def test_cli_preview_has_no_host_file_access_or_processes(self):
        with patch("pathlib.Path.open", side_effect=AssertionError("open")), \
                patch("pathlib.Path.stat", side_effect=AssertionError("stat")), \
                patch("subprocess.run", side_effect=AssertionError("process")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["plan-partage", "--demo", "--action", "create", "--name", "Documents",
                                   "--path", "/srv/documents", "--user", "alex", "--json"]), 0)
        data = json.loads(output.getvalue())
        self.assertFalse(data["can_apply"])
        self.assertEqual(data["mode"], "demo")
        self.assertIn("[Documents]", data["candidate"])

    def test_cli_remove_and_invalid_request(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["plan-partage", "--demo", "--action", "remove", "--name", "Medias"]), 0)
        self.assertIn("conserver le dossier", output.getvalue())
        for args in (["--demo", "--action", "create", "--name", "New"],
                     ["--demo", "--action", "remove", "--name", "Medias", "--user", "alex"],
                     ["--action", "remove", "--name", "Medias"]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as caught:
                main(["plan-partage", *args])
            self.assertEqual(caught.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
