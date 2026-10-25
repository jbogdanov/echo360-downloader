"""Monitor background jobs without controlling their worker process."""
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import echo360_tool as tool


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        tool.write_json(self.folder / 'job.json', {'type': 'combine'})
        self.output = io.StringIO()

    def state(self, **values):
        tool.write_json(self.folder / 'status.json', values)

    def test_progress_updates_until_verified_completion(self):
        self.state(state='running', phase='encoding', pid=123, percent=25,
                   speed_x=2.5, eta_seconds=90, encoder='cpu', item=1, total=2)
        (self.folder / 'run.log').write_text('> [ENCODE] Example output\n> [PROGRESS] 25%\n', encoding='utf-8')
        def finish(_):
            self.state(state='complete', output='result.mp4')
        with patch('sys.stdout', self.output), patch.object(tool, 'process_alive', return_value=True), \
                patch.object(tool.time, 'sleep', side_effect=finish):
            self.assertEqual(tool.watch_job(self.folder), 0)
        text = self.output.getvalue()
        self.assertIn('Job 1/2 | [#####---------------]', text)
        self.assertIn('25.0% | 2.5x | ETA 00:01:30', text)
        self.assertIn('[ENCODE] Example output', text)
        self.assertNotIn('[PROGRESS] 25%\n', text)
        self.assertIn('All output checks passed', text)
        self.assertIn('Output: result.mp4', text)
        self.assertNotIn('\033[', text)

    def test_failure_is_reported_with_nonzero_result(self):
        self.state(state='failed', error='Encoding failed: disk full')
        with patch('sys.stdout', self.output):
            self.assertEqual(tool.watch_job(self.folder / 'status.json'), 1)
        self.assertIn('[ERROR] Encoding failed: disk full', self.output.getvalue())

    def test_ctrl_c_leaves_worker_status_unchanged(self):
        self.state(state='running', phase='verifying', pid=123)
        before = (self.folder / 'status.json').read_bytes()
        with patch('sys.stdout', self.output), patch.object(tool, 'process_alive', return_value=True), \
                patch.object(tool.time, 'sleep', side_effect=KeyboardInterrupt):
            self.assertEqual(tool.watch_job(self.folder), 0)
        self.assertEqual((self.folder / 'status.json').read_bytes(), before)
        self.assertIn('Verifying the output', self.output.getvalue())
        self.assertIn('background job continues', self.output.getvalue())

    def test_dead_worker_is_not_reported_as_complete(self):
        self.state(state='running', phase='encoding', percent=50, pid=123)
        with patch('sys.stdout', self.output), patch.object(tool, 'process_alive', return_value=False), \
                patch.object(tool.time, 'sleep'), patch.object(tool.time, 'monotonic', side_effect=[10, 11, 11, 14]):
            self.assertEqual(tool.watch_job(self.folder), 1)
        self.assertIn('did not report completion', self.output.getvalue())
        self.assertNotIn('All output checks passed', self.output.getvalue())

    def test_defaults_to_latest_job(self):
        for name in ('20261025-100000-a', '20261025-110000-b'):
            folder = self.folder / 'jobs' / name
            folder.mkdir(parents=True)
            tool.write_json(folder / 'job.json', {})
            tool.write_json(folder / 'status.json', {'state': 'complete'})
        with patch.object(tool, 'HOME', self.folder), patch('sys.stdout', self.output):
            self.assertEqual(tool.watch_job(), 0)
        self.assertIn('Live status: 20261025-110000-b', self.output.getvalue())

    def test_no_jobs_has_clear_error(self):
        with patch.object(tool, 'HOME', self.folder):
            with self.assertRaisesRegex(FileNotFoundError, 'No background jobs'):
                tool.watch_job()


if __name__ == '__main__':
    unittest.main()
