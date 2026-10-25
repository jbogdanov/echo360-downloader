"""Real process contention and automatic lock cleanup."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import echo360_tool as tool


class LockTests(unittest.TestCase):
    def test_contender_cannot_remove_owner_lock_and_can_retry_afterward(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'.download.lock'
            script = 'import sys; from echo360_tool import exclusive\nwith exclusive(sys.argv[1]): print("ACQUIRED")'
            def attempt():
                return subprocess.run([sys.executable, '-c', script, str(path)], cwd=tool.HOME,
                                      capture_output=True, text=True, timeout=15, creationflags=tool.NO_WINDOW)
            with tool.exclusive(path):
                self.assertTrue(path.exists())
                rejected = attempt()
                self.assertNotEqual(rejected.returncode, 0)
                self.assertIn('Another job', rejected.stderr)
                self.assertTrue(path.exists())
                self.assertNotEqual(attempt().returncode, 0)
            self.assertFalse(path.exists())
            self.assertEqual(attempt().returncode, 0)
            self.assertFalse(path.exists())

    def test_exception_removes_lock_and_old_inactive_lock_is_reusable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'combined.mp4.lock'
            path.write_bytes(b'0')
            with self.assertRaisesRegex(ValueError, 'failed'):
                with tool.exclusive(path):
                    raise ValueError('failed')
            self.assertFalse(path.exists())
            with tool.exclusive(path):
                self.assertTrue(path.exists())
            self.assertFalse(path.exists())

    @unittest.skipUnless(sys.platform == 'win32', 'Compatibility with old Windows workers')
    def test_old_byte_lock_still_blocks_new_worker(self):
        import msvcrt
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'.download.lock'
            with path.open('a+b') as handle:
                handle.write(b'0')
                handle.flush()
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                try:
                    with self.assertRaisesRegex(RuntimeError, 'Another job'):
                        with tool.exclusive(path):
                            self.fail('Acquired a lock still owned by an old worker')
                    self.assertTrue(path.exists())
                finally:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            with tool.exclusive(path):
                pass
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
