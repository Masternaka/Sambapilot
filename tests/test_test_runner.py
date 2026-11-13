import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import struct
import zlib

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/run_tests.py'
spec = importlib.util.spec_from_file_location('test_runner_support', SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)
smoke_spec = importlib.util.spec_from_file_location('installed_smoke_support', SCRIPT.with_name('smoke_installed.py'))
smoke = importlib.util.module_from_spec(smoke_spec)
smoke_spec.loader.exec_module(smoke)


class RunnerPolicyTests(unittest.TestCase):
    def result(self, skipped=None):
        result = unittest.TestResult()
        case = unittest.FunctionTestCase(lambda: None)
        result.startTest(case)
        if skipped is None:
            result.addSuccess(case)
        else:
            result.addSkip(case, skipped)
        result.stopTest(case)
        return result

    def counts(self):
        return {prefix: 1 for prefix in runner.OPTIONAL_SUITES}

    def test_successful_suite_reports_executed_tests(self):
        report = runner.summarize(self.result(), 1, self.counts(), True, {})
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['passed'], 1)
        self.assertEqual(report['tests_run'], 1)
        self.assertEqual(report['executed'], 1)

    def test_native_skip_cannot_be_reported_as_success(self):
        report = runner.summarize(self.result('dependency unavailable'), 1, self.counts(), True, {})
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['passed'], 0)
        self.assertTrue(report['policy_errors'])

    def test_absent_native_suite_fails_even_if_other_tests_pass(self):
        report = runner.summarize(self.result(), 1, {}, True, {})
        self.assertEqual(report['status'], 'failed')
        self.assertIn('absente', ' '.join(report['policy_errors']))

    def test_empty_or_incomplete_suite_fails(self):
        for result, discovered in ((unittest.TestResult(), 0), (self.result(), 2)):
            with self.subTest(discovered=discovered):
                self.assertEqual(runner.summarize(result, discovered, {}, False, {})['status'], 'failed')

    def test_unexpected_skip_fails_even_outside_native_mode(self):
        report = runner.summarize(self.result('unexpected skip'), 1, {}, False, {})
        self.assertEqual(report['status'], 'failed')

    def test_intentionally_disabled_native_suite_is_explicitly_reported(self):
        case = type('OptionalCase', (), {'id': lambda self: 'test_gtk_integration.Case.test_example'})()
        result = unittest.TestResult()
        result.testsRun = 1
        result.addSkip(case, 'GTK disabled')
        report = runner.summarize(result, 1, self.counts(), False, {})
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['passed'], 0)
        self.assertEqual(report['executed'], 0)
        self.assertEqual(report['skipped'][0]['test'], case.id())
        self.assertEqual(runner.summarize(result, 1, self.counts(), False, {'SAMBAPILOT_GTK_TESTS': '1'})['status'], 'failed')

    def test_failure_stays_failed_in_json_summary(self):
        result = self.result()
        result.errors.append((unittest.FunctionTestCase(lambda: None), 'fixture error'))
        report = runner.summarize(result, 1, self.counts(), False, {})
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['errors'], 1)

    def test_json_report_never_overwrites_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'report.json'
            data = runner.summarize(self.result(), 1, {}, False, {})
            runner.write_report(output, data)
            before = output.read_bytes(), output.stat().st_mtime_ns
            self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['status'], 'passed')
            with self.assertRaises(FileExistsError):
                runner.write_report(output, {'status': 'failed'})
            self.assertEqual((output.read_bytes(), output.stat().st_mtime_ns), before)

    def test_multiple_failed_subtests_do_not_produce_negative_success_count(self):
        class MultipleFailures(unittest.TestCase):
            def runTest(self):
                for number in range(3):
                    with self.subTest(number=number):
                        self.fail('fixture')
        result = unittest.TestResult()
        MultipleFailures().run(result)
        report = runner.summarize(result, 1, {}, False, {})
        self.assertEqual(report['passed'], 0)
        self.assertEqual(report['failures'], 3)
        self.assertEqual(report['status'], 'failed')

    def test_installed_smoke_refuses_source_checkout_before_creating_fixtures(self):
        from unittest.mock import patch
        for args in ([], ['--gtk']):
            with self.subTest(args=args), \
                    patch.object(smoke.tempfile, 'TemporaryDirectory', side_effect=AssertionError('fixture')), \
                    patch.object(smoke, 'check_gtk', side_effect=AssertionError('GTK')), \
                    patch.object(smoke, 'check_icons', side_effect=AssertionError('assets')), \
                    self.assertRaisesRegex(RuntimeError, 'paquet installé'):
                smoke.main(args)


class InstalledIconChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='sambapilot-icon-fixture-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for size in smoke.ICON_SIZES:
            path = self.icon_path(size)
            path.parent.mkdir(parents=True)
            path.write_bytes(self.png(size))

    def icon_path(self, size):
        return self.root / 'assets' / 'icons' / 'hicolor' / f'{size}x{size}' / 'apps' / (smoke.ICON_NAME + '.png')

    def png(self, size):
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
        header = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
        pixels = (b'\x00' + b'\x00\x00\xff\xff' * size) * size
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')

    def test_complete_icon_set_is_checked_without_loading_gtk(self):
        from unittest.mock import patch
        with patch.object(smoke, 'check_gtk', side_effect=AssertionError('GTK')):
            icons = smoke.check_icons(self.root)
        self.assertEqual(len(icons), 8)

    def test_missing_packaged_icon_is_an_error(self):
        self.icon_path(32).unlink()
        with self.assertRaises(FileNotFoundError):
            smoke.check_icons(self.root)

    def test_wrong_sized_png_cannot_pass_as_requested_size(self):
        self.icon_path(32).write_bytes(self.png(16))
        with self.assertRaisesRegex(RuntimeError, 'Dimensions'):
            smoke.check_icons(self.root)

    def test_truncated_or_non_png_resources_are_refused(self):
        for data in (b'', b'not an image', self.png(32)[:25]):
            with self.subTest(length=len(data)):
                self.icon_path(32).write_bytes(data)
                with self.assertRaisesRegex(RuntimeError, 'en-tête invalide'):
                    smoke.check_icons(self.root)
