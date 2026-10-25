"""Exercise real HTTP downloads, muxing, verification and cache reuse without Echo360."""
import functools
import io
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import echo360_tool as tool


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class DownloadIntegration(unittest.TestCase):
    def test_http_two_stream_download_and_checksum_reuse(self):
        with tempfile.TemporaryDirectory(prefix='echo360-toolkit-test-') as directory:
            root = Path(directory)
            for index, color in ((1, 'red'), (2, 'blue')):
                tool.ff_run(['-v', 'error', '-f', 'lavfi', '-i', f'color=c={color}:s=160x90:r=10',
                             '-t', '2', '-c:v', 'libx264', '-threads', '1', '-y', str(root/f'video{index}.mp4')])
                (root/f'video{index}.m3u8').write_text(f'#EXTM3U\n#EXT-X-MAP:URI="video{index}.mp4"\n#EXTINF:2,\nvideo{index}.mp4\n', encoding='utf-8')
            tool.ff_run(['-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100',
                         '-t', '2', '-c:a', 'aac', '-y', str(root/'audio.mp4')])
            server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(root)))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            video = {'duration': 'PT2S', 'playableMedias': [
                {'sourceIndex': 1, 'trackType': ['Video'], 'isHls': True, 'uri': base+'/video1.m3u8'},
                {'sourceIndex': 2, 'trackType': ['Video'], 'isHls': True, 'uri': base+'/video2.m3u8'},
                {'sourceIndex': 0, 'trackType': ['Audio'], 'isHls': False, 'uri': base+'/audio.mp4'}]}
            try:
                with patch.object(tool, 'player', return_value=(urllib.request.build_opener(), video)):
                    with patch('sys.stdout', new_callable=io.StringIO) as console:
                        folder, manifest = tool.download('https://example.org/lesson/test/classroom', name='HTTP test', output_root=root/'outputs', announce_preview=False)
                    self.assertNotIn('SOURCE_PREVIEWS.jpg', console.getvalue())
                    self.assertEqual(len(manifest['streams']), 2)
                    self.assertFalse((folder/'.download.lock').exists())
                    self.assertTrue((folder/'SOURCE_PREVIEWS.jpg').exists())
                    for row in manifest['streams']:
                        self.assertTrue(row['audio'])
                        self.assertEqual(row['sha256'], tool.digest(folder/row['file']))
                    with patch.object(tool, 'fetch_file', side_effect=AssertionError('Cache must avoid full transfers')):
                        _, reused = tool.download('https://example.org/lesson/test/classroom', name='HTTP test', output_root=root/'outputs')
                        self.assertEqual(reused['streams'], manifest['streams'])
                    # Exercise selected-lesson batches with real HTTP transfers
                    # and media checks, without encoding combined files.
                    jobs = [dict(action='download', lesson_url=f'https://example.org/lesson/{name}/classroom',
                                 name=name, output_root=str(root/'batch')) for name in ('selected-a', 'selected-c')]
                    with patch('sys.stdout', new_callable=io.StringIO) as batch_console:
                        report = tool.run_batch(jobs, root/'job')
                    self.assertEqual(len(report['downloads']), 2)
                    self.assertEqual(report['failures'], [])
                    self.assertEqual(report['files'], [])
                    self.assertNotIn('SOURCE_PREVIEWS.jpg', batch_console.getvalue())
                    for row in report['downloads']:
                        self.assertEqual(len(row['streams']), 2)
                        self.assertTrue((Path(row['folder'])/'source_1.mp4').exists())
                        self.assertTrue((Path(row['folder'])/'source_2.mp4').exists())
                    self.assertFalse((root/'batch'/'unselected-b').exists())
                    with patch('sys.stdout', io.StringIO()):
                        output = folder/'combined.mp4'
                        tool.combine(folder/'source_1.mp4', folder/'source_2.mp4', output, encoder='cpu')
                    self.assertTrue(output.exists())
                    self.assertTrue(output.with_suffix('.verification.json').exists())
                    self.assertFalse(output.with_suffix('.mp4.lock').exists())
                    self.assertFalse(output.with_suffix('.ffmpeg.log').exists())
                    # Even an empty encoder log is retained if verification fails.
                    with patch.object(tool, 'verify', side_effect=RuntimeError('Verification failed')), \
                            patch('sys.stdout', io.StringIO()):
                        failed = folder/'failed.mp4'
                        with self.assertRaisesRegex(RuntimeError, 'Verification failed'):
                            tool.combine(folder/'source_1.mp4', folder/'source_2.mp4', failed, encoder='cpu')
                    self.assertTrue(failed.with_suffix('.ffmpeg.log').exists())
                    self.assertFalse(failed.with_suffix('.mp4.lock').exists())
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
