"""Regression tests for the interactive download and merge choices."""
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import echo360_tool as tool


class WizardTests(unittest.TestCase):
    lesson = 'https://example.org/lesson/test/classroom'
    course = 'https://example.org/section/test/public'

    def run_wizard(self, answers, ids=(1, 2)):
        folder = tool.HOME / 'downloads' / 'DevOps' / '02'
        manifest = {'streams': [{'source_id': i, 'file': f'source_{i}.mp4'} for i in ids]}
        with patch('builtins.input', side_effect=answers) as prompts, \
                patch.object(tool, 'download', return_value=(folder, manifest)) as download, \
                patch.object(tool, 'start_background') as background, \
                patch.object(tool, 'watch_job', return_value=0), \
                patch.object(tool, 'preview_files') as generate_preview, \
                patch.object(tool.os, 'startfile', create=True) as open_preview, \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            tool.wizard()
        self.assertEqual(generate_preview.call_count, 1 if background.called else 0)
        return prompts, download, background, open_preview, output.getvalue()

    def test_course_then_video_folders_and_optional_merge(self):
        prompts, download, background, preview, output = self.run_wizard(
            ['1', self.lesson, 'DevOps', '02', '', 'n'])
        labels = [call.args[0] for call in prompts.call_args_list]
        self.assertIn('Course folder name', labels[2])
        self.assertIn('Video subfolder name', labels[3])
        download.assert_called_once_with(self.lesson, name='02', output_root=tool.HOME/'downloads'/'DevOps')
        background.assert_not_called()
        preview.assert_not_called()
        self.assertIn('Download complete', output)
        self.assertNotIn('SOURCE_PREVIEWS.jpg', output)
        self.assertFalse(any('Public course' in label for label in labels))

    def test_enter_accepts_merge_and_two_streams_only_ask_for_large_source(self):
        prompts, _, background, preview, output = self.run_wizard(
            ['1', self.lesson, 'DevOps', '02', '', '', '2', ''])
        labels = [call.args[0] for call in prompts.call_args_list]
        self.assertIn('Combine the downloaded streams into one video? [yes] no: ', labels)
        self.assertIn('Source ID for the LARGE video on the LEFT (1, 2): ', labels)
        self.assertFalse(any('SMALL video' in label for label in labels))
        options = background.call_args.args[0]['options']
        self.assertTrue(options['large'].endswith('source_2.mp4'))
        self.assertTrue(options['small'].endswith('source_1.mp4'))
        self.assertNotIn('AI', output)
        self.assertNotIn('tokens', output)
        self.assertIn('R I P P E R', output)
        self.assertIn('separate source streams, not the final merged layout', output)
        if tool.os.name == 'nt':
            self.assertEqual(preview.call_args.args[0].name, 'SOURCE_PREVIEWS.jpg')

    def test_course_url_is_only_requested_after_access_failure(self):
        expected = (Path('downloaded'), {'streams': []})
        with patch.object(tool, 'download', side_effect=[tool.PublicAccessRequired('session required'), expected]) as download, \
                patch('builtins.input', return_value=self.course) as prompts, \
                patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(tool.wizard_download(self.lesson, '02', Path('DevOps')), expected)
        prompts.assert_called_once_with('Public course/section URL: ')
        download.assert_called_with(self.lesson, course_url=self.course, name='02', output_root=Path('DevOps'))

    def test_server_error_does_not_prompt_for_course(self):
        failure = HTTPError(self.lesson, 503, 'Unavailable', {}, None)
        with patch.object(tool, 'download', side_effect=failure), patch('builtins.input') as prompts:
            with self.assertRaises(HTTPError):
                tool.wizard_download(self.lesson, '02', Path('DevOps'))
        prompts.assert_not_called()

    def test_source_prompt_lists_real_ids_and_rejects_invalid_choice(self):
        with patch('builtins.input', side_effect=['9', '7']) as prompts, patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(tool.choose_source('Large source', {7: 'b', 3: 'a'}), 7)
        self.assertTrue(all(call.args[0] == 'Large source (3, 7): ' for call in prompts.call_args_list))

    def test_single_stream_finishes_without_merge_question(self):
        prompts, _, background, _, output = self.run_wizard(['1', self.lesson, 'DevOps', '02', ''], ids=(1,))
        self.assertEqual(prompts.call_count, 5)
        background.assert_not_called()
        self.assertIn('Only one stream', output)

    def test_more_than_two_streams_requires_unambiguous_small_choice(self):
        prompts, _, background, _, _ = self.run_wizard(
            ['1', self.lesson, 'DevOps', '02', '', 'y', '3', '2', 'cpu'], ids=(1, 2, 3))
        self.assertIn('Source ID for the SMALL video on the RIGHT (1, 2): ', [call.args[0] for call in prompts.call_args_list])
        self.assertTrue(background.call_args.args[0]['options']['small'].endswith('source_2.mp4'))

    def test_preview_is_announced_only_after_merge_acceptance(self):
        folder = tool.HOME / 'downloads' / 'DevOps' / '02'
        manifest = {'streams': [{'source_id': i, 'file': f'source_{i}.mp4'} for i in (1, 2)]}
        answers = iter(['1', self.lesson, 'DevOps', '02', '', 'y', '2', 'cpu'])
        output = io.StringIO()

        def respond(prompt):
            if prompt.startswith('Combine the downloaded'):
                self.assertNotIn('SOURCE_PREVIEWS.jpg', output.getvalue())
            if prompt.startswith('Source ID for the LARGE'):
                self.assertIn(str(folder / 'SOURCE_PREVIEWS.jpg'), output.getvalue())
                self.assertIn('> [PREVIEW]', output.getvalue())
            return next(answers)

        with patch('builtins.input', side_effect=respond), \
                patch.object(tool, 'download', return_value=(folder, manifest)), \
                patch.object(tool, 'start_background'), \
                patch.object(tool, 'watch_job', return_value=0), \
                patch.object(tool, 'preview_files'), \
                patch.object(tool.os, 'startfile', create=True), \
                patch('sys.stdout', output):
            tool.wizard()

    def test_redirected_status_has_labels_but_no_ansi_codes(self):
        output = io.StringIO()
        tool.status_line('Source 1 is ready', 'READY', stream=output)
        tool.status_line('Something failed', 'ERROR', stream=output)
        self.assertIn('> [READY] Source 1 is ready', output.getvalue())
        self.assertIn('> [ERROR] Something failed', output.getvalue())
        self.assertNotIn('\033[', output.getvalue())

    def test_local_merge_names_output_without_prompt(self):
        folder = tool.HOME / 'downloads' / 'Course' / '02'
        for large_id, small_id in ((2, 1), (1, 2)):
            with self.subTest(large_id=large_id), \
                    patch('builtins.input', side_effect=[
                        '2', f'"{folder / f"source_{large_id}.mp4"}"',
                        str(folder / f'source_{small_id}.mp4'), '']) as prompts, \
                    patch.object(tool, 'start_background') as background, \
                    patch.object(tool, 'watch_job', return_value=0), \
                    patch('sys.stdout', new_callable=io.StringIO) as output:
                tool.wizard()
                expected = str(folder / f'combined_large-{large_id}_small-{small_id}.mp4')
                options = background.call_args.args[0]['options']
                self.assertEqual(options['output'], expected)
                self.assertEqual(options['encoder'], 'auto')
                self.assertEqual(prompts.call_count, 4)
                self.assertFalse(any('output' in call.args[0].lower() for call in prompts.call_args_list))
                self.assertIn(expected, output.getvalue())

    def test_local_merge_with_custom_names_uses_large_input_folder(self):
        large = tool.HOME / 'lectures' / 'teacher.mp4'
        small = tool.HOME / 'screens' / 'slides.mp4'
        self.assertEqual(tool.local_merge_output(large, small),
                         large.parent / 'combined_large-teacher_small-slides.mp4')


if __name__ == '__main__':
    unittest.main()
