"""Keyboard navigation and terminal restoration for the main menu."""
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import echo360_tool as tool


class MainMenuTests(unittest.TestCase):
    def choose(self, keys):
        with patch.object(tool, 'windows_terminal', return_value=True), \
                patch.object(tool, 'read_windows_key', side_effect=keys), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            choice = tool.choose_main_menu()
        self.assertTrue(output.getvalue().endswith('\033[?25h\033[?1049l'))
        return choice, output.getvalue()

    def test_enter_selects_first_option_and_displays_marker(self):
        choice, output = self.choose(['enter'])
        self.assertEqual(choice, '1')
        self.assertIn('> Download a lesson', output)
        self.assertIn('R I P P E R', output)
        self.assertIn('Up/Down: move | Enter: choose', output)
        self.assertNotIn('Choose 1, 2', output)

    def test_arrows_wrap_and_home_end_navigate(self):
        cases = [(['down', 'down', 'up', 'enter'], '2'),
                 (['down', 'down', 'enter'], '3'),
                 (['up', 'enter'], '4'),
                 (['end', 'down', 'enter'], '1'),
                 (['end', 'home', 'enter'], '1')]
        for keys, expected in cases:
            with self.subTest(keys=keys):
                self.assertEqual(self.choose(keys)[0], expected)

    def test_cancel_exits_wizard_without_starting_work(self):
        for key in ('q', 'escape'):
            with self.subTest(key=key), \
                    patch.object(tool, 'windows_terminal', return_value=True), \
                    patch.object(tool, 'read_windows_key', return_value=key), \
                    patch.object(tool, 'start_background') as start, \
                    patch('builtins.input') as prompts, patch('sys.stdout', io.StringIO()):
                self.assertEqual(tool.wizard(), 0)
            prompts.assert_not_called()
            start.assert_not_called()

    def test_interrupt_restores_cursor_and_original_screen(self):
        with patch.object(tool, 'windows_terminal', return_value=True), \
                patch.object(tool, 'read_windows_key', return_value='interrupt'), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            with self.assertRaises(KeyboardInterrupt):
                tool.choose_main_menu()
        self.assertTrue(output.getvalue().endswith('\033[?25h\033[?1049l'))

    def test_noninteractive_terminal_keeps_numbered_fallback(self):
        with patch.object(tool, 'windows_terminal', return_value=False), \
                patch('builtins.input', return_value='3'), \
                patch.object(tool, 'read_windows_key') as read_key, \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(tool.choose_main_menu(), '3')
        read_key.assert_not_called()
        self.assertNotIn('\033[', output.getvalue())


if __name__ == '__main__':
    unittest.main()
