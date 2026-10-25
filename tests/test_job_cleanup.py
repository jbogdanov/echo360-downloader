"""Completed-job cleanup must preserve monitoring, reruns, and failure evidence."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import echo360_tool as tool


class JobCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        home = patch.object(tool, 'HOME', self.root)
        home.start()
        self.addCleanup(home.stop)
        self.folder = self.root/'jobs'/'20261025-120000-abcdef'
        self.job = {'type': 'batch', 'jobs': [{'action': 'download', 'lesson_url': 'https://example.org/lesson/a/classroom'}]}
        tool.write_json(self.folder/'job.json', self.job)
        tool.write_json(self.folder/'status.json', {'state': 'complete', 'total': 1, 'pid': 123})
        tool.write_json(self.folder/'launcher.json', {'pid': 124})
        tool.write_json(self.folder/'result.json', {'downloads': [{'folder': 'output'}], 'failures': []})
        (self.folder/'run.log').write_text('done', encoding='utf-8')

    def clean(self):
        with patch.object(tool, 'process_alive', return_value=False):
            return tool.cleanup_completed_job(self.folder)

    def test_success_removes_folder_and_preserves_batch_and_result(self):
        self.assertTrue(self.clean())
        self.assertFalse(self.folder.exists())
        record = tool.read_json(tool.history_path(self.folder))
        self.assertEqual(record['jobs'], self.job['jobs'])
        self.assertEqual(record['result']['failures'], [])
        for target in (None, self.folder, self.folder/'STATUS.txt', tool.history_path(self.folder)):
            with patch('sys.stdout', new_callable=io.StringIO) as output:
                self.assertEqual(tool.watch_job(target), 0)
            self.assertIn('Completion record:', output.getvalue())
            self.assertNotIn('Batch report:', output.getvalue())

    def test_running_and_failed_jobs_are_kept(self):
        for state in ('running', 'failed'):
            tool.write_json(self.folder/'status.json', {'state': state})
            self.assertFalse(self.clean())
            self.assertTrue((self.folder/'run.log').exists())
        self.assertFalse(tool.history_path(self.folder).exists())

    def test_completion_waits_for_worker_and_launcher_to_exit(self):
        for responses in ([True], [False, True], [None]):
            with patch.object(tool, 'process_alive', side_effect=responses):
                self.assertFalse(tool.cleanup_completed_job(self.folder))
            self.assertTrue(self.folder.exists())

    def test_unexpected_user_files_are_preserved(self):
        (self.folder/'notes.txt').write_text('Keep me', encoding='utf-8')
        self.assertFalse(self.clean())
        self.assertTrue((self.folder/'run.log').exists())
        self.assertTrue((self.folder/'notes.txt').exists())

    def test_cleanup_rejects_paths_outside_jobs(self):
        with self.assertRaises(ValueError):
            tool.cleanup_completed_job(self.root)
        self.assertTrue(self.folder.exists())

    def test_cleanup_can_retry_after_partial_file_removal(self):
        tool.archive_completed_job(self.folder)
        (self.folder/'result.json').unlink()
        (self.folder/'job.json').unlink()
        self.assertTrue(self.clean())
        self.assertFalse(self.folder.exists())

    @unittest.skipUnless(sys.platform == 'win32', 'Windows read-only attributes')
    def test_read_only_completed_files_and_folder_can_be_cleaned(self):
        (self.folder/'run.log').chmod(0o400)
        self.folder.chmod(0o500)
        self.assertTrue(self.clean())
        self.assertFalse(self.folder.exists())

    def test_monitor_handles_cleanup_between_progress_updates(self):
        tool.write_json(self.folder/'status.json', {'state': 'running', 'phase': 'downloading', 'pid': 123})
        def finish(_):
            tool.write_json(self.folder/'status.json', {'state': 'complete'})
            self.assertTrue(self.clean())
        with patch('sys.stdout', new_callable=io.StringIO) as output, \
                patch.object(tool, 'process_alive', return_value=True), \
                patch.object(tool.time, 'sleep', side_effect=finish):
            self.assertEqual(tool.watch_job(self.folder), 0)
        self.assertIn('All output checks passed', output.getvalue())


if __name__ == '__main__':
    unittest.main()
