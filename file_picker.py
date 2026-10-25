"""Console file browser for selecting local merge inputs."""
from pathlib import Path
import os
import re
import shutil
import sys

from course_picker import windows_terminal, read_windows_key

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.m4v', '.ts', '.mts', '.m2ts', '.wmv'}


def video_entries(folder, excluded=None):
    directories, videos = [], []
    for path in folder.iterdir():
        if path.is_dir():
            directories.append(path)
        elif path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS:
            if excluded is None or path.resolve() != excluded:
                videos.append(path)
    key = lambda path: path.name.casefold()
    return ([folder.parent] if folder.parent != folder else []) + sorted(directories, key=key) + sorted(videos, key=key)


def choose_video(title, start, excluded=None):
    """Return a video path, or None when cancelled. Never modify browsed files."""
    if not windows_terminal():
        return str(Path(input(f'{title} video path: ').strip().strip('"')).expanduser().resolve())
    folder = Path(start).resolve()
    while not folder.is_dir() and folder.parent != folder:
        folder = folder.parent
    excluded = Path(excluded).resolve() if excluded else None
    entries, cursor, message = [], 0, ''

    def visit(path):
        nonlocal folder, entries, cursor, message
        target = path.resolve()
        listing = video_entries(target, excluded)
        folder, entries, cursor, message = target, listing, 0, ''

    def select(path):
        if path.is_dir():
            visit(path)
            return None
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError('Choose an existing video file or folder.')
        resolved = path.resolve()
        if resolved == excluded:
            raise ValueError('Choose a different video from the large input.')
        return str(resolved)

    print('\033[?1049h\033[?25l', end='', flush=True)
    try:
        try:
            visit(folder)
        except OSError as error:
            message = str(error)
        while True:
            columns, lines = shutil.get_terminal_size((100, 25))
            width, page_size = max(1, columns - 1), max(1, lines - 8)
            first = cursor // page_size * page_size
            rows = [f'ECHO360 RIPPER - Choose {title} video', '-' * width, str(folder), '',
                    'Up/Down: move | Enter: open/select | Backspace: parent | P: paste folder/file path (any drive) | Q/Esc: cancel | PgUp/PgDn: page', '',
                    message or 'Folders and video files only. Enter chooses the highlighted video.', '']
            selected_row = len(rows) + cursor - first if entries else None
            for index in range(first, min(first + page_size, len(entries))):
                path = entries[index]
                label = '[..] Parent folder' if path == folder.parent else f'[folder] {path.name}' if path.is_dir() else path.name
                rows.append(f'{">" if index == cursor else " "} {label}')
            if not entries:
                rows.append('(No video files or folders here)')
            clean = lambda text: re.sub(r'[\x00-\x1f\x7f]', '', text)[:width]
            rows = [clean(row) for row in rows]
            if 'NO_COLOR' not in os.environ:
                rows[0] = f'\033[1;36m{rows[0]}\033[0m'
                rows[4] = re.sub(r'(^| \| )([^:]+)(?=:)',
                                 lambda match: f'{match[1]}\033[94m{match[2]}\033[0m', rows[4])
                if selected_row is not None:
                    rows[selected_row] = f'\033[92m{rows[selected_row]}\033[0m'
            print('\033[H\033[2J' + '\n'.join(rows), end='', flush=True)
            key = read_windows_key()
            if key in ('q', 'escape'):
                return None
            if key == 'interrupt':
                raise KeyboardInterrupt
            if key in ('up', 'down', 'pageup', 'pagedown', 'home', 'end'):
                delta = {'up': -1, 'down': 1, 'pageup': -page_size, 'pagedown': page_size,
                         'home': -len(entries), 'end': len(entries)}[key]
                cursor = max(0, min(max(0, len(entries) - 1), cursor + delta))
                continue
            try:
                if key == 'backspace':
                    visit(folder.parent)
                elif key == 'enter' and entries:
                    result = select(entries[cursor])
                    if result:
                        return result
                elif key == 'p':
                    print('\033[?25h\n', end='', flush=True)
                    try:
                        value = input('Folder or video path (Enter to return): ').strip().strip('"')
                    finally:
                        print('\033[?25l', end='', flush=True)
                    if value:
                        path = Path(value).expanduser()
                        result = select(path if path.is_absolute() else folder / path)
                        if result:
                            return result
            except (OSError, ValueError) as error:
                message = str(error)
    finally:
        print('\033[?25h\033[?1049l', end='', flush=True)
