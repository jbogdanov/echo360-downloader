"""Public course discovery and a console checklist; no extra dependencies."""
import ctypes
import http.cookiejar
import json
import os
import re
import shutil
import sys
import textwrap
import urllib.parse
import urllib.request


def clean_text(value):
    # Remote titles must never become terminal control sequences.
    return ' '.join(re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', str(value or '')).split())


def parse_syllabus(data, origin):
    if not isinstance(data, dict) or data.get('status') != 'ok' or not isinstance(data.get('data'), list):
        raise RuntimeError('Could not load the public course lesson list. Check the course URL and viewing access.')
    lessons = {}

    def visit(items):
        for item in items:
            if item.get('type') == 'SyllabusGroupType':
                visit(item.get('lessons', []))
            elif item.get('type') == 'SyllabusLessonType':
                content = item.get('lesson', {})
                lesson = content.get('lesson', {})
                identity = lesson.get('id')
                if not identity:
                    raise RuntimeError('The course returned a lesson without an ID; its format may have changed.')
                medias = [m for m in content.get('medias', []) if m.get('mediaType') == 'Video']
                ready = any(m.get('isAvailable') and not any(m.get(k) for k in
                            ('isProcessing', 'isFailed', 'isScheduled', 'isHiddenDueToCaptions', 'isAudioOnly')) for m in medias)
                if content.get('isLive'):
                    reason = 'Live now'
                elif ready:
                    reason = ''
                elif any(m.get('isProcessing') for m in medias):
                    reason = 'Processing'
                elif content.get('isFuture'):
                    reason = 'Not recorded yet'
                else:
                    reason = 'No available video'
                start = (lesson.get('timing') or {}).get('start') or content.get('captureStartedAt') or ''
                lessons[identity] = dict(
                    id=identity, title=clean_text(lesson.get('displayName') or lesson.get('name') or 'Untitled lesson'),
                    start=clean_text(start), timezone=clean_text((lesson.get('timeZone') or {}).get('id')),
                    lesson_url=f'{origin}/lesson/{urllib.parse.quote(identity, safe=":_-")}/classroom',
                    available=not reason, reason=reason)
    visit(data['data'])
    return sorted(lessons.values(), key=lambda row: (row['start'] or '9999', row['id']))


def load_course(course_url):
    parsed = urllib.parse.urlparse(course_url)
    if parsed.scheme != 'https' or not parsed.netloc or not re.fullmatch(r'/section/[\w-]+/public/?', parsed.path):
        raise ValueError('Use a public course URL: https://echo360.org.uk/section/<course-id>/public')
    origin = f'{parsed.scheme}://{parsed.netloc}'
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    opener.addheaders = [('User-Agent', 'Echo360OfflineToolkit/1.0')]
    with opener.open(course_url, timeout=90) as response:
        html = response.read().decode('utf-8')
    match = re.search(r'Echo\["sectionHomeApp"\]\(("(?:\\.|[^"\\])*")', html)
    if not match:
        raise RuntimeError('Public course configuration not found. Login-only courses and changed page formats are unsupported.')
    config = json.loads(json.loads(match[1]))
    section = config.get('sectionId')
    if not isinstance(section, str) or not re.fullmatch(r'[\w-]+', section):
        raise RuntimeError('The public course page did not provide a valid section ID.')
    # Public-link IDs and internal section IDs differ. Use the page's own ID,
    # keeping the viewing-session cookies for its complete syllabus request.
    with opener.open(f'{origin}/section/{section}/syllabus', timeout=90) as response:
        data = json.loads(response.read().decode('utf-8'))
    return parse_syllabus(data, origin)


def lesson_label(lesson):
    date = lesson['start'][:16].replace('T', ' ') or 'Date not set'
    zone = f" ({lesson['timezone']})" if lesson.get('timezone') else ''
    suffix = f" -- {lesson['reason']}" if not lesson['available'] else ''
    return f"{date}{zone} | {lesson['title']}{suffix}"


def selection_command(command, selected, eligible, count):
    """Apply a line-mode toggle atomically, so invalid input changes nothing."""
    command = command.strip().lower()
    if command == 'a':
        return set(eligible)
    if command == 'n':
        return set()
    changes = set()
    for token in command.replace(',', ' ').split():
        if not re.fullmatch(r'\d+(?:-\d+)?', token):
            raise ValueError('Enter lesson numbers, a range such as 2-5, a, n, Enter, or q.')
        bounds = [int(n) for n in token.split('-')]
        start, end = bounds[0], bounds[-1]
        if not 1 <= start <= end <= count:
            raise ValueError(f'Lesson numbers must be between 1 and {count}.')
        changes.update(range(start-1, end))
    if not changes <= eligible:
        raise ValueError('Rows marked [-] have no available recording and cannot be selected.')
    return selected.symmetric_difference(changes)


def choose_by_line(lessons):
    eligible = {i for i, row in enumerate(lessons) if row['available']}
    selected = set()
    while True:
        print('\nSelect lessons: [X] selected, [ ] available, [-] unavailable')
        for i, row in enumerate(lessons):
            marker = 'X' if i in selected else ' ' if i in eligible else '-'
            print(f"  [{marker}] {i+1:3}. {lesson_label(row)}")
        print(f'{len(selected)} selected. Toggle: 1,3,5-7 | a: all available | n: none | Enter: start | q: cancel')
        answer = input('Selection: ').strip().lower()
        if answer == 'q':
            return []
        if not answer:
            if selected:
                return [lessons[i] for i in sorted(selected)]
            print('Select at least one lesson, or q to cancel.')
            continue
        try:
            selected = selection_command(answer, selected, eligible, len(lessons))
        except ValueError as error:
            print(f'> [WARNING] {error}')


def choose_by_keys(lessons, read_key, render, page_size):
    eligible = {i for i, row in enumerate(lessons) if row['available']}
    selected = set()
    cursor = 0
    while True:
        render(cursor, selected)
        step = page_size() if callable(page_size) else page_size
        key = read_key()
        if key in ('q', 'escape'):
            return []
        if key == 'interrupt':
            raise KeyboardInterrupt
        if key == 'enter' and selected:
            return [lessons[i] for i in sorted(selected)]
        if key in ('space', 'x') and cursor in eligible:
            selected.symmetric_difference_update({cursor})
        elif key == 'a':
            selected = set(eligible)
        elif key == 'n':
            selected.clear()
        elif key == 'up':
            cursor = max(0, cursor-1)
        elif key == 'down':
            cursor = min(len(lessons)-1, cursor+1)
        elif key == 'pageup':
            cursor = max(0, cursor-step)
        elif key == 'pagedown':
            cursor = min(len(lessons)-1, cursor+step)
        elif key == 'home':
            cursor = 0
        elif key == 'end':
            cursor = len(lessons)-1


def windows_terminal():
    if os.name != 'nt' or not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    handle = kernel.GetStdHandle(-11)
    mode = wintypes.DWORD()
    return bool(kernel.GetConsoleMode(handle, ctypes.byref(mode)) and kernel.SetConsoleMode(handle, mode.value | 4))


def read_windows_key():
    import msvcrt
    key = msvcrt.getwch()
    if key in ('\x00', '\xe0'):
        return {'H': 'up', 'P': 'down', 'K': 'left', 'M': 'right', 'I': 'pageup', 'Q': 'pagedown', 'G': 'home', 'O': 'end'}.get(msvcrt.getwch(), '')
    return {' ': 'space', '\r': 'enter', '\x08': 'backspace', '\x1b': 'escape', '\x03': 'interrupt'}.get(key, key.lower())


def wrap_controls(controls, width):
    rows = []
    for control in controls:
        if rows and len(rows[-1]) + 3 + len(control) <= width:
            rows[-1] += ' | ' + control
        else:
            rows.extend(textwrap.wrap(control, width=max(1, width)))
    return rows


def color_controls(line):
    if 'NO_COLOR' in os.environ:
        return line
    return re.sub(r'(^| \| )([^:]+)(?=:)',
                  lambda match: f'{match[1]}\033[94m{match[2]}\033[0m', line)


def choose_lessons(lessons):
    if not any(row['available'] for row in lessons):
        print('> No recorded videos are available to select in this course.')
        return []
    if not windows_terminal():
        return choose_by_line(lessons)
    page_size = 1

    def render(cursor, selected):
        nonlocal page_size
        columns, lines = shutil.get_terminal_size((100, 25))
        width = max(1, columns-1)
        controls = wrap_controls(['Up/Down: move', 'Space/X: mark', 'A: all', 'N: none',
                                  'Enter: continue', 'Q/Esc: cancel', 'PgUp/PgDn: page',
                                  'Home/End: first/last'], width)
        footer_size = 2 + len(controls)
        page_size = max(1, lines - 6 - footer_size)
        first = cursor // page_size * page_size
        rows = ['ECHO360 RIPPER - Select course lessons', '-' * width,
                'Dates and times use the course local timezone.', '',
                '[X] selected   [ ] available   [-] unavailable', '']
        for i in range(first, min(first+page_size, len(lessons))):
            row = lessons[i]
            marker = 'X' if i in selected else ' ' if row['available'] else '-'
            label = f"{'>' if i == cursor else ' '} [{marker}] {i+1:3}. {lesson_label(row)}"
            rows.append(label)
        rows.extend([''] * max(0, lines - footer_size - len(rows)))
        rows.extend(['-' * width,
                     f'{len(selected)} selected | Rows {first+1}-{min(first+page_size, len(lessons))} of {len(lessons)}',
                     *controls])
        rows = [re.sub(r'[\x00-\x1f\x7f]', '', row)[:width] for row in rows]
        if 'NO_COLOR' not in os.environ:
            rows[0] = f'\033[1;36m{rows[0]}\033[0m'
            for i in range(first, min(first+page_size, len(lessons))):
                index = 6 + i - first
                if i == cursor:
                    rows[index] = f'\033[92m{rows[index]}\033[0m'
                elif i in selected:
                    rows[index] = f'\033[32m{rows[index]}\033[0m'
        for index in range(len(rows) - len(controls), len(rows)):
            rows[index] = color_controls(rows[index])
        # Clear and redraw only the alternate screen; restore original output on exit.
        print('\033[H\033[2J' + '\n'.join(rows), end='', flush=True)

    print('\033[?1049h\033[?25l', end='', flush=True)
    try:
        return choose_by_keys(lessons, read_windows_key, render, lambda: page_size)
    finally:
        print('\033[?25h\033[?1049l', end='', flush=True)
