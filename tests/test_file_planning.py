import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sambapilot.cli import main
from sambapilot.demo import demo_configuration
from sambapilot.file_planning import FilePlanSession
from sambapilot.inspection import InspectionError, read_configuration
from sambapilot.planning import PlanError, ShareDraft, format_plan


class FilePlanningTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "smb.conf"
        self.path.write_text(demo_configuration(), encoding="utf-8")
        self.draft = ShareDraft("Documents", "/srv/documents", ("alex",))

    def test_snapshot_keeps_exact_utf8_bytes_and_uses_absolute_path(self):
        data = b"\xef\xbb\xbf" + demo_configuration().replace("\n", "\r\n").encode("utf-8")
        self.path.write_bytes(data)
        snapshot = read_configuration(str(self.path))
        self.assertEqual(snapshot.content.encode("utf-8"), data)
        self.assertEqual(snapshot.sha256, hashlib.sha256(data).hexdigest())
        self.assertTrue(Path(snapshot.source).is_absolute())
        self.assertEqual(len(snapshot.inspect().shares), 3)

    def test_real_file_preview_preserves_source_bytes_and_mtime(self):
        before = self.path.read_bytes()
        metadata = self.path.stat()
        with patch("subprocess.run", side_effect=AssertionError("process")):
            session = FilePlanSession.open(str(self.path))
            plan = session.preview("create", self.draft.name, self.draft)
        self.assertEqual(plan.mode, "file")
        self.assertEqual(plan.source, str(self.path))
        self.assertFalse(plan.can_apply)
        self.assertEqual(plan.baseline_sha256, hashlib.sha256(before).hexdigest())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(self.path.stat().st_mtime_ns, metadata.st_mtime_ns)
        self.assertTrue(plan.candidate.startswith(before.decode("utf-8")))

    def test_file_change_invalidates_previously_valid_preview(self):
        session = FilePlanSession.open(str(self.path))
        session.preview("create", self.draft.name, self.draft)
        self.path.write_text(demo_configuration() + "# extérieur\n", encoding="utf-8")
        with self.assertRaisesRegex(PlanError, "changé"):
            session.preview("create", self.draft.name, self.draft)
        self.assertIsNone(session.current)
        self.assertNotIn("extérieur", session.source)

    def test_bom_only_change_and_newline_only_change_are_detected(self):
        for new_content in (b"\xef\xbb\xbf" + demo_configuration().encode("utf-8"),
                            demo_configuration().replace("\n", "\r\n").encode("utf-8")):
            with self.subTest(content=new_content[:10]):
                self.path.write_text(demo_configuration(), encoding="utf-8")
                session = FilePlanSession.open(str(self.path))
                self.path.write_bytes(new_content)
                with self.assertRaises(PlanError):
                    session.preview("create", self.draft.name, self.draft)

    def test_missing_or_replaced_by_symlink_source_clears_preview(self):
        session = FilePlanSession.open(str(self.path))
        session.preview("create", self.draft.name, self.draft)
        self.path.unlink()
        with self.assertRaises(InspectionError):
            session.preview("create", self.draft.name, self.draft)
        self.assertIsNone(session.current)
        target = self.path.parent / "other.conf"
        target.write_text(demo_configuration(), encoding="utf-8")
        self.path.symlink_to(target)
        with self.assertRaises(InspectionError):
            session.preview("create", self.draft.name, self.draft)

    def test_unreadable_source_cannot_reuse_old_plan(self):
        session = FilePlanSession.open(str(self.path))
        session.preview("create", self.draft.name, self.draft)
        with patch("sambapilot.file_planning.read_configuration", side_effect=InspectionError("refusé")), \
                self.assertRaises(InspectionError):
            session.preview("create", self.draft.name, self.draft)
        self.assertIsNone(session.current)

    def test_blocked_configuration_cannot_become_plan_source(self):
        self.path.write_text("[global]\ninclude = /never-open.conf\n", encoding="utf-8")
        with self.assertRaises(PlanError):
            FilePlanSession.open(str(self.path))

    def test_prefill_reuses_explicit_permissions_and_visibility(self):
        self.path.write_text("[Files]\npath = /srv/files\nvalid users = alex +famille\n"
                             "read only = no\nbrowseable = no\nguest ok = no\n", encoding="utf-8")
        session = FilePlanSession.open(str(self.path))
        draft = session.draft_for("Files")
        self.assertEqual(draft.users, ("alex",))
        self.assertEqual(draft.groups, ("famille",))
        self.assertFalse(draft.read_only)
        self.assertFalse(draft.browseable)
        self.assertEqual(session.preview("update", "Files", draft).diff, "")

    def test_prefill_does_not_invent_undeclared_or_guest_settings(self):
        for content in ("[Files]\npath = /files\nvalid users = alex\n",
                        "[Files]\npath = /files\nvalid users = alex\nread only = yes\nbrowseable = yes\nguest ok = yes\n",
                        "[Files]\npath = /files\nvalid users = @famille\nread only = yes\nbrowseable = yes\nguest ok = no\n"):
            with self.subTest(content=content):
                self.path.write_text(content, encoding="utf-8")
                with self.assertRaises(PlanError):
                    FilePlanSession.open(str(self.path)).draft_for("Files")

    def test_supported_inspection_aliases_do_not_bypass_planning_limits(self):
        self.path.write_text("[Files]\npath = /files\nvalid users = alex\n"
                             "writable = yes\nbrowseable = yes\nguest ok = no\n", encoding="utf-8")
        with self.assertRaises(PlanError):
            FilePlanSession.open(str(self.path)).draft_for("Files")

    def test_advanced_target_is_preserved_and_edit_refused(self):
        self.path.write_text("[Documents]\npath = /srv/documents\nvfs objects = recycle\n", encoding="utf-8")
        before = self.path.read_bytes()
        session = FilePlanSession.open(str(self.path))
        for action, draft in (("update", self.draft), ("remove", None)):
            with self.subTest(action=action), self.assertRaises(PlanError):
                session.preview(action, "Documents", draft)
        self.assertEqual(self.path.read_bytes(), before)

    def test_adding_share_preserves_unrelated_advanced_section(self):
        self.path.write_text("[global]\nworkgroup = MAISON\n[Other]\npath = /other\nvfs objects = recycle\n", encoding="utf-8")
        session = FilePlanSession.open(str(self.path))
        plan = session.preview("create", self.draft.name, self.draft)
        self.assertTrue(plan.candidate.startswith(session.source))
        self.assertIn("vfs objects = recycle", plan.candidate)

    def test_removal_and_update_preserve_bom_and_crlf(self):
        data = b"\xef\xbb\xbf" + demo_configuration().replace("\n", "\r\n").encode("utf-8")
        self.path.write_bytes(data)
        session = FilePlanSession.open(str(self.path))
        for action, draft in (("remove", None), ("update", session.draft_for("Medias"))):
            with self.subTest(action=action):
                plan = session.preview(action, "Medias", draft)
                self.assertTrue(plan.candidate.startswith("\ufeff"))
                self.assertEqual(plan.candidate.count("\ufeff"), 1)
                self.assertNotIn("\n", plan.candidate.replace("\r\n", ""))
                self.assertEqual(plan.baseline_sha256, hashlib.sha256(data).hexdigest())
                self.assertEqual(plan.candidate_sha256, hashlib.sha256(plan.candidate.encode("utf-8")).hexdigest())
        self.assertEqual(self.path.read_bytes(), data)

    def test_bom_is_kept_when_first_section_is_removed(self):
        self.path.write_bytes(b"\xef\xbb\xbf[Documents]\r\npath = /srv/documents\r\n")
        plan = FilePlanSession.open(str(self.path)).preview("remove", "Documents")
        self.assertEqual(plan.candidate, "\ufeff")

    def test_cancellation_and_invalid_new_request_discard_candidate(self):
        session = FilePlanSession.open(str(self.path))
        session.preview("create", self.draft.name, self.draft)
        session.discard()
        self.assertIsNone(session.current)
        session.preview("create", self.draft.name, self.draft)
        with self.assertRaises(PlanError):
            session.preview("remove", "Missing")
        self.assertIsNone(session.current)

    def test_source_path_is_sanitized_in_terminal_preview(self):
        unusual = self.path.parent / "source\x1b[2J.conf"
        unusual.write_text(demo_configuration(), encoding="utf-8")
        plan = FilePlanSession.open(str(unusual)).preview("create", self.draft.name, self.draft)
        self.assertNotIn("\x1b", format_plan(plan))

    def test_cli_real_plan_is_json_and_never_launches_a_program(self):
        before = self.path.read_bytes()
        with patch("subprocess.run", side_effect=AssertionError("process")), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(["plan-partage", "--config", str(self.path), "--action", "create",
                                   "--name", "Documents", "--path", "/srv/documents", "--user", "alex", "--json"]), 0)
        report = json.loads(output.getvalue())
        self.assertEqual(report["source"], str(self.path))
        self.assertEqual(report["mode"], "file")
        self.assertFalse(report["can_apply"])
        self.assertEqual(self.path.read_bytes(), before)

    def test_cli_source_is_required_and_exclusive_without_read(self):
        for source_args in ([], ["--config", str(self.path), "--demo"]):
            with self.subTest(source_args=source_args), \
                    patch("sambapilot.file_planning.read_configuration", side_effect=AssertionError("read")), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(["plan-partage", *source_args, "--action", "remove", "--name", "Medias"])
            self.assertEqual(caught.exception.code, 2)


    def test_reload_review_discards_preview_without_adopting_or_writing_source(self):
        session = FilePlanSession.open(str(self.path))
        session.preview('create', self.draft.name, self.draft)
        initial = session.snapshot
        self.path.write_text(demo_configuration() + '# outside change\n', encoding='utf-8')
        before = self.path.read_bytes(), self.path.stat().st_mtime_ns
        with patch('subprocess.run', side_effect=AssertionError('process')):
            review = session.prepare_reload()
        self.assertIs(review.origin, initial)
        self.assertIs(session.snapshot, initial)
        self.assertIsNone(session.current)
        self.assertIn('outside change', review.diff)
        self.assertNotEqual(review.latest.sha256, initial.sha256)
        self.assertEqual((self.path.read_bytes(), self.path.stat().st_mtime_ns), before)

    def test_explicit_adoption_requires_a_new_preview_and_keeps_supplied_settings(self):
        session = FilePlanSession.open(str(self.path))
        self.path.write_text(demo_configuration() + '# changed\n', encoding='utf-8')
        review = session.prepare_reload()
        replacement = session.adopt_reload(review, 'create', self.draft.name)
        self.assertIsNone(replacement.current)
        self.assertNotEqual(session.snapshot.sha256, replacement.snapshot.sha256)
        self.assertNotIn('# changed', session.source)
        plan = replacement.preview('create', self.draft.name, self.draft)
        self.assertIn(self.draft.path, plan.candidate)
        self.assertIn('# changed', plan.candidate)
        self.assertEqual(plan.baseline_sha256, replacement.snapshot.sha256)
        self.assertFalse(plan.can_apply)
        self.assertEqual(self.path.read_text(encoding='utf-8'), review.latest.content)

    def test_second_source_change_prevents_adoption(self):
        from sambapilot.file_planning import SourceChangedError
        session = FilePlanSession.open(str(self.path))
        self.path.write_text(demo_configuration() + '# first\n', encoding='utf-8')
        review = session.prepare_reload()
        self.path.write_text(demo_configuration() + '# second\n', encoding='utf-8')
        with self.assertRaises(SourceChangedError):
            session.adopt_reload(review, 'create', self.draft.name)
        self.assertIsNone(session.current)
        self.assertNotIn('# first', session.source)
        self.assertNotIn('# second', session.source)

    def test_review_from_another_session_cannot_be_adopted(self):
        first = FilePlanSession.open(str(self.path))
        other = FilePlanSession.open(str(self.path))
        review = first.prepare_reload()
        with self.assertRaises(PlanError):
            other.adopt_reload(review, 'create', self.draft.name)
        self.assertIsNone(other.current)

    def test_blocked_reloaded_structure_is_refused_and_original_source_is_kept(self):
        session = FilePlanSession.open(str(self.path))
        original = session.source
        self.path.write_text('[global]\ninclude = /never-read.conf\n', encoding='utf-8')
        with self.assertRaises(PlanError):
            session.prepare_reload()
        self.assertEqual(session.source, original)
        self.assertIsNone(session.current)

    def test_disappeared_incomplete_or_advanced_target_cannot_be_adopted_for_update(self):
        for content in ('[Other]\npath = /other\n',
                        '[Medias]\npath = /srv/medias\n',
                        demo_configuration().replace('[Medias]', '[Medias]\nvfs objects = recycle')):
            with self.subTest(content=content):
                self.path.write_text(demo_configuration(), encoding='utf-8')
                session = FilePlanSession.open(str(self.path))
                self.path.write_text(content, encoding='utf-8')
                review = session.prepare_reload()
                with self.assertRaises(PlanError):
                    session.adopt_reload(review, 'update', 'Medias')
                self.assertEqual(session.source, demo_configuration())

    def test_creation_collision_is_refused_case_insensitively_after_reload(self):
        session = FilePlanSession.open(str(self.path))
        self.path.write_text(demo_configuration() + '[documents]\npath = /external\n', encoding='utf-8')
        review = session.prepare_reload()
        with self.assertRaises(PlanError):
            session.adopt_reload(review, 'create', 'Documents')
        self.assertIsNone(session.current)

    def test_adoption_preserves_latest_bom_crlf_and_source_metadata(self):
        session = FilePlanSession.open(str(self.path))
        data = b'\xef\xbb\xbf' + demo_configuration().replace('\n', '\r\n').encode('utf-8')
        self.path.write_bytes(data)
        before = self.path.stat().st_mtime_ns
        replacement = session.adopt_reload(session.prepare_reload(), 'create', self.draft.name)
        plan = replacement.preview('create', self.draft.name, self.draft)
        self.assertTrue(plan.candidate.startswith('\ufeff'))
        self.assertNotIn('\n', plan.candidate.replace('\r\n', ''))
        self.assertEqual(self.path.read_bytes(), data)
        self.assertEqual(self.path.stat().st_mtime_ns, before)

    def test_removal_of_new_advanced_target_is_refused_after_reload(self):
        session = FilePlanSession.open(str(self.path))
        self.path.write_text(demo_configuration().replace('[Medias]', '[Medias]\nvfs objects = recycle'), encoding='utf-8')
        with self.assertRaises(PlanError):
            session.adopt_reload(session.prepare_reload(), 'remove', 'Medias')
        self.assertIsNone(session.current)

    def test_unreadable_source_at_adoption_cannot_reuse_old_preview(self):
        session = FilePlanSession.open(str(self.path))
        session.preview('create', self.draft.name, self.draft)
        review = session.prepare_reload()
        with patch('sambapilot.file_planning.read_configuration', side_effect=InspectionError('denied')), \
                self.assertRaises(InspectionError):
            session.adopt_reload(review, 'create', self.draft.name)
        self.assertIsNone(session.current)


if __name__ == "__main__":
    unittest.main()
