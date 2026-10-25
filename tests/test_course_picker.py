"""Public syllabus parsing, console selection, and selected-lesson batches."""
import io
import json
import os
import re
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import course_picker as picker
import echo360_tool as tool


def entry(identity, start='2026-09-01T14:00:00.000', medias=None, **values):
    content = dict(lesson={'id': identity, 'name': 'Test lecture', 'timing': {'start': start},
                           'timeZone': {'id': 'Europe/Tallinn'}},
                   medias=[{'mediaType': 'Video', 'isAvailable': True}] if medias is None else medias)
    content.update(values)
    return {'type': 'SyllabusLessonType', 'lesson': content}


def parse(items):
    return picker.parse_syllabus({'status': 'ok', 'data': items}, 'https://example.org')


class CourseTests(unittest.TestCase):
    def test_groups_duplicates_sorting_and_exact_lesson_ids(self):
        long_id = 'G_abc_2026-09-01T14:00:00.000'
        rows = parse([entry('later', '2026-09-02T16:00:00.000'),
                      {'type': 'SyllabusGroupType', 'lessons': [entry(long_id), entry(long_id)]}])
        self.assertEqual([r['id'] for r in rows], [long_id, 'later'])
        self.assertEqual(rows[0]['lesson_url'], f'https://example.org/lesson/{long_id}/classroom')
        self.assertIn('2026-09-01 14:00 (Europe/Tallinn)', picker.lesson_label(rows[0]))

    def test_future_hidden_processing_and_live_rows_are_disabled(self):
        rows = parse([entry('future', medias=[], isFuture=True), entry('live', isLive=True),
                      entry('processing', medias=[{'mediaType': 'Video', 'isAvailable': True, 'isProcessing': True}]),
                      entry('hidden', medias=[{'mediaType': 'Video', 'isAvailable': False}]),
                      entry('slides', medias=[{'mediaType': 'Presentation', 'isAvailable': True}])])
        self.assertTrue(all(not r['available'] for r in rows))
        self.assertEqual(next(r for r in rows if r['id'] == 'future')['reason'], 'Not recorded yet')

    def test_invalid_response_does_not_masquerade_as_empty_course(self):
        with self.assertRaisesRegex(RuntimeError, 'Could not load'):
            picker.parse_syllabus({'status': 'error', 'data': []}, 'https://example.org')

    def test_remote_title_cannot_inject_terminal_controls(self):
        row = entry('a')
        row['lesson']['lesson']['name'] = 'Hello\x1b[2J\nWorld'
        title = parse([row])[0]['title']
        self.assertNotIn('\x1b', title)
        self.assertNotIn('\n', title)

    def test_loader_uses_internal_section_id_in_same_session(self):
        config = json.dumps(json.dumps({'sectionId': 'internal-123'}))
        responses = [f'Echo["sectionHomeApp"]({config});'.encode(),
                     json.dumps({'status': 'ok', 'data': [entry('actual-lesson')]}).encode()]
        opener = MagicMock()
        opener.open.side_effect = [io.BytesIO(body) for body in responses]
        with patch.object(picker.urllib.request, 'build_opener', return_value=opener):
            rows = picker.load_course('https://example.org/section/public-link-id/public')
        self.assertEqual(rows[0]['id'], 'actual-lesson')
        self.assertEqual([c.args[0] for c in opener.open.call_args_list],
                         ['https://example.org/section/public-link-id/public',
                          'https://example.org/section/internal-123/syllabus'])

    def test_lesson_url_is_not_accepted_as_course_url(self):
        with self.assertRaisesRegex(ValueError, 'public course URL'):
            picker.load_course('https://example.org/lesson/abc/classroom')

    def test_line_mode_toggles_ranges_and_shows_x(self):
        rows = parse([entry('a'), entry('b'), entry('c')])
        output = io.StringIO()
        with patch('builtins.input', side_effect=['1-3', '2', '']), patch('sys.stdout', output):
            selected = picker.choose_by_line(rows)
        self.assertEqual([r['id'] for r in selected], ['a', 'c'])
        self.assertIn('[X]', output.getvalue())

    def test_invalid_toggle_is_atomic_and_unavailable_rows_rejected(self):
        selected = {0}
        for value in ('1,99', '2', '3-1', 'oops'):
            with self.assertRaises(ValueError):
                picker.selection_command(value, selected, {0, 2}, 3)
            self.assertEqual(selected, {0})
        self.assertEqual(picker.selection_command('a', selected, {0, 2}, 3), {0, 2})
        self.assertEqual(picker.selection_command('n', selected, {0, 2}, 3), set())

    def test_keyboard_marking_skips_unavailable_and_keeps_order(self):
        rows = parse([entry('a'), entry('b', medias=[]), entry('c')])
        keys = iter(['space', 'down', 'space', 'down', 'x', 'enter'])
        renders = []
        selected = picker.choose_by_keys(rows, lambda: next(keys), lambda c, s: renders.append((c, set(s))), 2)
        self.assertEqual([r['id'] for r in selected], ['a', 'c'])
        self.assertEqual(renders[-1], (2, {0, 2}))

    def test_keyboard_page_navigation_all_none_and_cancel(self):
        rows = parse([entry(str(i)) for i in range(10)])
        keys = iter(['pagedown', 'space', 'pageup', 'a', 'n', 'end', 'home', 'q'])
        renders = []
        self.assertEqual(picker.choose_by_keys(rows, lambda: next(keys), lambda c, s: renders.append((c, set(s))), 3), [])
        self.assertEqual(renders[1][0], 3)
        self.assertEqual(len(renders[5][1]), 0)
        self.assertEqual(renders[6][0], 9)

    def test_empty_selection_does_not_start_on_enter(self):
        rows = parse([entry('a')])
        keys = iter(['enter', 'q'])
        self.assertEqual(picker.choose_by_keys(rows, lambda: next(keys), lambda *_: None, 10), [])

    def test_course_screen_matches_file_picker_and_resizes_footer(self):
        rows = parse([entry(str(i)) for i in range(40)])
        sizes = [(120, 25), (80, 20), (40, 25), (100, 25)]
        with patch.object(picker, 'windows_terminal', return_value=True), \
                patch.object(picker, 'read_windows_key', side_effect=['space', 'pagedown', 'pagedown', 'enter']), \
                patch.object(picker.shutil, 'get_terminal_size',
                             side_effect=[os.terminal_size(size) for size in sizes]), \
                patch.dict(os.environ), patch('sys.stdout', new_callable=io.StringIO) as output:
            os.environ.pop('NO_COLOR', None)
            selected = picker.choose_lessons(rows)
        self.assertEqual(selected, [rows[0]])
        screens = output.getvalue().split('\033[H\033[2J')[1:]
        for (width, height), screen in zip(sizes, screens):
            with self.subTest(width=width):
                self.assertIn('\033[1;36mECHO360 RIPPER', screen)
                self.assertIn('\033[92m>', screen)
                self.assertIn('\033[94mUp/Down\033[0m: move', screen)
                plain = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', screen).splitlines()
                self.assertEqual(len(plain), height)
                self.assertTrue(all(len(line) < width for line in plain))
                footer = '\n'.join(plain[plain.index('-' * (width - 1), 2) + 1:])
                for label in ('Up/Down: move', 'Space/X: mark', 'A: all', 'N: none',
                              'Enter: next', 'Q/Esc: cancel', 'PgUp/PgDn: page', 'Home/End: first/last'):
                    self.assertIn(label, footer)
                if width == 120:
                    self.assertEqual(len(footer.splitlines()), 2)  # Count line, then all controls.
        # Page movement uses the height and wrapped footer from the current render.
        plain = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', screens[2])
        self.assertIn('> [ ]  11.', plain)

    def test_course_screen_honors_no_color_and_restores_on_cancel(self):
        with patch.object(picker, 'windows_terminal', return_value=True), \
                patch.object(picker, 'read_windows_key', return_value='escape'), \
                patch.dict(os.environ, {'NO_COLOR': '1'}), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(picker.choose_lessons(parse([entry('a')])), [])
        self.assertNotRegex(output.getvalue(), r'\x1b\[[0-9;]*m')
        self.assertTrue(output.getvalue().endswith('\033[?25h\033[?1049l'))

    def test_course_wizard_builds_only_selected_download_jobs(self):
        rows = parse([entry('a'), entry('b'), entry('c')])
        with patch('builtins.input', side_effect=['3', 'https://example.org/section/abc/public', 'DevOps', '', 'n']), \
                patch.object(tool, 'load_course', return_value=rows), \
                patch.object(tool, 'choose_lessons', return_value=[rows[0], rows[2]]), \
                patch.object(tool, 'start_background', return_value=Path('job')) as start, \
                patch.object(tool, 'watch_job', return_value=0) as watch, patch('sys.stdout', io.StringIO()):
            self.assertEqual(tool.wizard(), 0)
        jobs = start.call_args.args[0]['jobs']
        self.assertEqual([j['lesson_url'] for j in jobs], [rows[0]['lesson_url'], rows[2]['lesson_url']])
        self.assertTrue(all(j['action'] == 'download' for j in jobs))
        self.assertTrue(all(Path(j['output_root']) == tool.HOME/'downloads'/'DevOps' for j in jobs))
        self.assertNotEqual(jobs[0]['name'], jobs[1]['name'])
        watch.assert_called_once_with(Path('job'))

    def test_cancel_does_not_start_worker(self):
        with patch('builtins.input', return_value='https://example.org/section/abc/public'), \
                patch.object(tool, 'load_course', return_value=parse([entry('a')])), \
                patch.object(tool, 'choose_lessons', return_value=[]), \
                patch.object(tool, 'start_background') as start, patch('sys.stdout', io.StringIO()):
            tool.course_wizard()
        start.assert_not_called()

    def test_course_merge_uses_one_layout_for_every_selected_lesson_without_previews(self):
        rows = parse([entry('a'), entry('b'), entry('c')])
        course = 'https://example.org/section/abc/public'
        for ids, choices, expected in [((1, 2), ['2'], (2, 1)),
                                       ((3, 7, 9), ['7', '9'], (7, 9))]:
            video = {'playableMedias': [{'trackType': ['Video'], 'sourceIndex': i} for i in ids]}
            with self.subTest(ids=ids), \
                    patch('builtins.input', side_effect=[course, 'Course', '', '', *choices, '']) as prompts, \
                    patch.object(tool, 'load_course', return_value=rows), \
                    patch.object(tool, 'choose_lessons', return_value=[rows[0], rows[2]]), \
                    patch.object(tool, 'player', return_value=(None, video)) as player, \
                    patch.object(tool, 'preview_files') as preview, \
                    patch.object(tool, 'start_background', return_value=Path('job')) as start, \
                    patch.object(tool, 'watch_job', return_value=0), patch('sys.stdout', io.StringIO()):
                tool.course_wizard()
            jobs = start.call_args.args[0]['jobs']
            self.assertEqual([j['lesson_url'] for j in jobs], [rows[0]['lesson_url'], rows[2]['lesson_url']])
            self.assertTrue(all((j['action'], j['large_source'], j['small_source'], j['encoder']) ==
                                ('combine', *expected, 'auto') for j in jobs))
            player.assert_called_once_with(rows[0]['lesson_url'], course)
            preview.assert_not_called()
            labels = [call.args[0] for call in prompts.call_args_list]
            self.assertIn("Merge each selected lesson's streams into its own video? [yes] no: ", labels)
            self.assertEqual(sum('LARGE' in label for label in labels), 1)
            self.assertEqual(sum('SMALL' in label for label in labels), int(len(ids) > 2))
            self.assertIn(f'Source ID for the LARGE video on the LEFT for all lessons ({", ".join(map(str, ids))}): ', labels)

    def test_course_merge_with_one_source_does_not_start_worker(self):
        rows = parse([entry('a')])
        video = {'playableMedias': [{'trackType': ['Video'], 'sourceIndex': 1}]}
        with patch('builtins.input', side_effect=['https://example.org/section/abc/public', '', '', '']), \
                patch.object(tool, 'load_course', return_value=rows), \
                patch.object(tool, 'choose_lessons', return_value=rows), \
                patch.object(tool, 'player', return_value=(None, video)), \
                patch.object(tool, 'start_background') as start, patch('sys.stdout', io.StringIO()):
            with self.assertRaisesRegex(ValueError, 'fewer than two'):
                tool.course_wizard()
        start.assert_not_called()

    def test_merge_batch_keeps_layout_and_continues_after_missing_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            full = {'streams': [{'source_id': i, 'file': f'source_{i}.mp4'} for i in (1, 2)]}
            single = {'streams': full['streams'][:1]}
            jobs = [dict(action='combine', lesson_url=name, large_source=2, small_source=1, encoder='cpu')
                    for name in ('first', 'missing', 'last')]
            with patch.object(tool, 'download', side_effect=[(directory / 'first', full),
                                                           (directory / 'missing', single),
                                                           (directory / 'last', full)]), \
                    patch.object(tool, 'combine', return_value={'ok': True}) as combine, \
                    patch.object(tool, 'preview_files') as preview, patch('sys.stdout', io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, '1 batch item'):
                    tool.run_batch(jobs, directory)
            self.assertEqual(combine.call_count, 2)
            for call, name in zip(combine.call_args_list, ('first', 'last')):
                folder = directory / name
                self.assertEqual(call.args, (folder / 'source_2.mp4', folder / 'source_1.mp4',
                                             folder / 'combined_large-2_small-1.mp4'))
                self.assertEqual(call.kwargs['encoder'], 'cpu')
            report = tool.read_json(directory / 'batch-report.json')
            self.assertEqual(report['failures'][0]['item'], 2)
            self.assertEqual(len(report['files']), 2)
            preview.assert_not_called()

    def test_download_batch_never_encodes_and_continues_after_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            jobs = [{'action': 'download', 'lesson_url': name} for name in ('bad', 'good')]
            manifest = {'streams': [{'source_id': 1, 'file': 'source_1.mp4'}]}
            with patch.object(tool, 'download', side_effect=[RuntimeError('Unavailable'), (directory, manifest)]) as download, \
                    patch.object(tool, 'combine') as combine, patch('sys.stdout', io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, '1 batch item'):
                    tool.run_batch(jobs, directory)
            report = tool.read_json(directory/'batch-report.json')
            self.assertEqual(len(report['downloads']), 1)
            self.assertEqual(report['failures'][0]['item'], 1)
            self.assertEqual(download.call_count, 2)
            combine.assert_not_called()

    def test_existing_json_jobs_still_combine(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = {'streams': [{'source_id': i, 'file': f'{i}.mp4'} for i in (1, 2)]}
            with patch.object(tool, 'download', return_value=(Path(temporary), manifest)), \
                    patch.object(tool, 'combine', return_value={'file': 'combined.mp4'}) as combine, \
                    patch('sys.stdout', io.StringIO()):
                report = tool.run_batch([{'lesson_url': 'test', 'large_source': 2, 'small_source': 1}])
            self.assertEqual(report['files'], [{'file': 'combined.mp4'}])
            self.assertEqual(combine.call_args.args[:2], (Path(temporary)/'2.mp4', Path(temporary)/'1.mp4'))


if __name__ == '__main__':
    unittest.main()
