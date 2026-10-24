"""Offline regression tests for media resolution and stream selection."""
import unittest
from unittest.mock import patch
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import echo360_tool as tool


class ToolkitTests(unittest.TestCase):
    def test_duration(self):
        self.assertEqual(tool.duration_seconds('PT2H3M4.5S'), 7384.5)
        self.assertEqual(tool.duration_seconds('PT939.55S'), 939.55)
        with self.assertRaises(ValueError):
            tool.duration_seconds('PT')

    def test_highest_resolution_and_relative_urls(self):
        master = '#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=200,RESOLUTION=640x360\nlow/list.m3u8\n#EXT-X-STREAM-INF:BANDWIDTH=800,RESOLUTION=1280x720\nhigh/list.m3u8\n'
        media = '#EXTM3U\n#EXT-X-MAP:URI="video.mp4",BYTERANGE="20@0"\n#EXTINF:5,\n#EXT-X-BYTERANGE:100@20\nvideo.mp4\n'
        with patch.object(tool, 'request_text', side_effect=[master, media]):
            self.assertEqual(tool.media_url(None, {'uri': 'https://example.org/a/master.m3u8', 'isHls': True}), 'https://example.org/a/high/video.mp4')

    def test_encryption_rejected(self):
        with patch.object(tool, 'request_text', return_value='#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\n'):
            with self.assertRaisesRegex(RuntimeError, 'Encrypted'):
                tool.media_url(None, {'uri': 'https://example.org/list.m3u8', 'isHls': True})

    def test_multiple_mp4_segments_rejected(self):
        text = '#EXTM3U\n#EXT-X-MAP:URI="init.mp4"\npart1.mp4\npart2.mp4\n'
        with patch.object(tool, 'request_text', return_value=text):
            with self.assertRaisesRegex(RuntimeError, 'separate media segments'):
                tool.media_url(None, {'uri': 'https://example.org/list.m3u8', 'isHls': True})

    def test_roles_use_source_id_not_array_order(self):
        tracks, audio = tool.select_tracks({'playableMedias': [
            {'sourceIndex': 2, 'trackType': ['Video'], 'isHls': True},
            {'sourceIndex': 0, 'trackType': ['Audio'], 'isHls': True},
            {'sourceIndex': 1, 'trackType': ['Video'], 'isHls': True}]})
        self.assertEqual(list(tracks), [1, 2])
        self.assertEqual(audio['sourceIndex'], 0)

    def test_prevent_overwriting_inputs(self):
        with self.assertRaisesRegex(ValueError, 'three different'):
            tool.combine('a.mp4', 'b.mp4', 'a.mp4')


if __name__ == '__main__':
    unittest.main()
