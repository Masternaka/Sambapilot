import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/run_tests.py'
spec = importlib.util.spec_from_file_location('test_runner_support', SCRIPT)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


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
        script = SCRIPT.with_name('smoke_installed.py')
        smoke_spec = importlib.util.spec_from_file_location('installed_smoke_support', script)
        smoke = importlib.util.module_from_spec(smoke_spec)
        smoke_spec.loader.exec_module(smoke)
        with patch.object(smoke.tempfile, 'TemporaryDirectory', side_effect=AssertionError('fixture')), \
                self.assertRaisesRegex(RuntimeError, 'paquet installé'):
            smoke.main()
