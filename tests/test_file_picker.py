"""Local file navigation, cancellation, and merge-wizard integration."""
import io
import os
import re
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import file_picker as picker
import echo360_tool as tool


class FilePickerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.lesson = self.root / 'Course lesson'
        self.lesson.mkdir()
        self.large = self.lesson / 'source_2.mp4'
        self.small = self.lesson / 'source_1.mp4'
        self.large.touch()
        self.small.touch()

    def browse(self, keys, start=None, excluded=None, inputs=()):
        with patch.object(picker, 'windows_terminal', return_value=True), \
                patch.object(picker, 'read_windows_key', side_effect=keys), \
                patch('builtins.input', side_effect=inputs), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            result = picker.choose_video('LARGE / LEFT', start or self.root, excluded)
        self.assertTrue(output.getvalue().endswith('\033[?25h\033[?1049l'))
        return result, output.getvalue()

    def test_enter_opens_folder_and_selects_video(self):
        result, output = self.browse(['down', 'enter', 'end', 'enter'])
        self.assertEqual(result, str(self.large))
        self.assertIn(str(self.root), output)
        self.assertIn('[folder] Course lesson', output)
        self.assertIn('> source_2.mp4', output)

    def test_parent_navigation_and_paging(self):
        result, _ = self.browse(['backspace', 'end', 'enter', 'pagedown', 'pageup',
                                 'home', 'down', 'enter'], start=self.lesson)
        self.assertEqual(result, str(self.small))

    def test_footer_keeps_all_shortcuts_visible_when_window_resizes(self):
        widths = (120, 100, 80, 40)
        with patch.object(picker.shutil, 'get_terminal_size',
                          side_effect=[os.terminal_size((width, 25)) for width in widths]):
            _, output = self.browse(['', '', '', 'q'])
        screens = output.split('\033[H\033[2J')[1:]
        self.assertEqual(len(screens), len(widths))
        for width, screen in zip(widths, screens):
            with self.subTest(width=width):
                rows = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', screen).splitlines()
                self.assertEqual(len(rows), 25)
                self.assertTrue(all(len(row) < width for row in rows))
                footer = '\n'.join(rows[rows.index('-' * (width - 1), 2) + 1:])
                for control in ('Up/Down: move', 'Enter: open/select', 'Backspace: parent',
                                'P: paste path', 'Q/Esc: cancel', 'PgUp/PgDn: page'):
                    self.assertIn(control, footer)
                if width == 120:
                    self.assertEqual(len(footer.splitlines()), 1)

    def test_filters_nonvideos_and_excludes_large_source(self):
        (self.lesson / 'manifest.json').touch()
        (self.lesson / 'SOURCE_PREVIEWS.jpg').touch()
        self.assertEqual(picker.video_entries(self.lesson, self.large), [self.root, self.small])
        result, output = self.browse(['end', 'enter'], start=self.lesson, excluded=self.large)
        self.assertEqual(result, str(self.small))
        self.assertNotIn('source_2.mp4', output)

    def test_paste_folder_then_select_and_paste_quoted_file(self):
        result, _ = self.browse(['p', 'end', 'enter'], inputs=[str(self.lesson)])
        self.assertEqual(result, str(self.large))
        result, _ = self.browse(['p'], inputs=[f'"{self.small}"'])
        self.assertEqual(result, str(self.small))

    def test_bad_pasted_path_and_duplicate_are_rejected_then_recover(self):
        result, output = self.browse(['p', 'p', 'p'], excluded=self.large,
                                     inputs=[str(self.root / 'missing.mp4'), str(self.large), str(self.small)])
        self.assertEqual(result, str(self.small))
        self.assertIn('Choose an existing video', output)
        self.assertIn('Choose a different video', output)

    def test_unreadable_folder_can_be_cancelled(self):
        with patch.object(picker, 'video_entries', side_effect=PermissionError('Access denied')):
            result, output = self.browse(['escape'])
        self.assertIsNone(result)
        self.assertIn('Access denied', output)

    def test_interrupt_restores_terminal(self):
        with patch.object(picker, 'windows_terminal', return_value=True), \
                patch.object(picker, 'read_windows_key', return_value='interrupt'), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            with self.assertRaises(KeyboardInterrupt):
                picker.choose_video('LARGE / LEFT', self.root)
        self.assertTrue(output.getvalue().endswith('\033[?25h\033[?1049l'))

    def test_wizard_starts_in_downloads_then_large_input_folder(self):
        with patch.object(tool, 'choose_main_menu', return_value='2'), \
                patch.object(tool, 'choose_video', side_effect=[str(self.large), str(self.small)]) as choose, \
                patch.object(tool, 'choose_encoder', return_value='cpu'), \
                patch.object(tool, 'start_background') as start, \
                patch.object(tool, 'watch_job', return_value=0), patch('sys.stdout', io.StringIO()):
            tool.wizard()
        self.assertEqual(choose.call_args_list[0].args, ('LARGE / LEFT', tool.HOME / 'downloads'))
        self.assertEqual(choose.call_args_list[1].args, ('SMALL / RIGHT', self.lesson))
        self.assertEqual(choose.call_args_list[1].kwargs, {'excluded': str(self.large)})
        self.assertEqual(start.call_args.args[0]['options']['output'],
                         str(self.lesson / 'combined_large-2_small-1.mp4'))

    def test_cancelling_either_selection_does_not_start_job(self):
        for selections in ([None], [str(self.large), None]):
            with self.subTest(selections=selections), \
                    patch.object(tool, 'choose_main_menu', return_value='2'), \
                    patch.object(tool, 'choose_video', side_effect=selections), \
                    patch.object(tool, 'choose_encoder') as encoder, \
                    patch.object(tool, 'start_background') as start, patch('sys.stdout', io.StringIO()):
                self.assertEqual(tool.wizard(), 0)
            start.assert_not_called()
            encoder.assert_not_called()


if __name__ == '__main__':
    unittest.main()
