"""Standalone Windows-first Echo360 downloader and two-stream video combiner."""
import argparse
from contextlib import contextmanager
import ctypes
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback
import urllib.parse
import urllib.request
import urllib.error
import uuid

import imageio_ffmpeg

HOME = Path(__file__).resolve().parent
FF = imageio_ffmpeg.get_ffmpeg_exe()
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
BANNER = r'''
   _____ ____ _   _  ___  _____   __    ___
  | ____/ ___| | | |/ _ \|___ /  / /_  / _ \
  |  _|| |   | |_| | | | | |_ \ | '_ \| | | |
  | |__| |___|  _  | |_| |___) || (_) | |_| |
  |_____\____|_| |_|\___/|____/  \___/ \___/

                 R I P P E R
       Download. Preview. Choose. Combine.
'''
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='replace')


def supports_color(stream):
    if 'NO_COLOR' in os.environ or not getattr(stream, 'isatty', lambda: False)():
        return False
    if os.name != 'nt':
        return True
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    handle = kernel.GetStdHandle(-12 if stream is sys.stderr else -11)
    mode = wintypes.DWORD()
    return bool(kernel.GetConsoleMode(handle, ctypes.byref(mode)) and
                kernel.SetConsoleMode(handle, mode.value | 0x0004))


def colored(text, color, stream):
    return f'\033[{color}m{text}\033[0m' if supports_color(stream) else text


def status_line(message, tag=None, stream=None):
    stream = stream or sys.stdout
    color = {'READY': '32', 'COMPLETE': '32', 'WARNING': '33', 'ERROR': '31',
             'PROGRESS': '94'}.get(tag, '36')
    marker = colored(f'> [{tag}]' if tag else '>', color, stream)
    for line in str(message).splitlines():
        print(f'{marker} {line}', file=stream, flush=True)


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


@contextmanager
def exclusive(path):
    """Reject duplicate jobs writing the same destination; OS releases locks on exit."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as handle:
        handle.seek(0)
        handle.write(b'0')
        handle.flush()
        handle.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise RuntimeError(f'Another job is already using this destination: {path.parent}') from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def slug(value):
    result = re.sub(r'[^\w .-]', '_', value).strip(' .')[:100]
    if not result or result.upper() in {'CON', 'PRN', 'AUX', 'NUL', *[f'COM{i}' for i in range(1, 10)], *[f'LPT{i}' for i in range(1, 10)]}:
        result = 'lecture_' + result
    return result


def duration_seconds(value):
    if isinstance(value, (float, int)):
        return float(value)
    m = re.fullmatch(r'PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?', str(value))
    if not m or not any(m.groups()):
        raise ValueError(f'Unsupported duration: {value!r}')
    return sum(float(v or 0) * factor for v, factor in zip(m.groups(), (3600, 60, 1)))


def request_text(opener, url):
    with opener.open(url, timeout=90) as response:
        return response.read().decode('utf-8')


class PublicAccessRequired(RuntimeError):
    """The lesson may need a public course session before it can be opened."""


def player(lesson_url, course_url=None):
    parsed = urllib.parse.urlparse(lesson_url)
    if parsed.scheme != 'https' or '/lesson/' not in parsed.path:
        raise ValueError('Paste a specific HTTPS lesson/classroom URL, not a section/course URL.')
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    opener.addheaders = [('User-Agent', 'Echo360OfflineToolkit/1.0')]
    if course_url:
        if urllib.parse.urlparse(course_url).scheme != 'https':
            raise ValueError('The public course URL must use HTTPS.')
        request_text(opener, course_url)
    try:
        html = request_text(opener, lesson_url)
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise PublicAccessRequired('The lesson requires a viewing session. Supply its public course/section URL.') from exc
        raise
    match = re.search(r'Echo\["echoPlayerV2FullApp"\]\(("(?:\\.|[^"\\])*")', html)
    if not match:
        raise PublicAccessRequired('Public player configuration not found. Open the lesson in your browser, copy its full classroom URL, and supply its public course/section URL. Login-only pages and changed player formats are not supported.')
    data = json.loads(json.loads(match[1]))
    if not data.get('video', {}).get('playableMedias'):
        raise RuntimeError('This page has no downloadable playable video metadata.')
    return opener, data['video']


def select_tracks(video):
    tracks = {}
    audios = []
    for item in video['playableMedias']:
        if item.get('trackType') == ['Video']:
            index = int(item['sourceIndex'])
            if index not in tracks or item.get('isHls'):
                tracks[index] = item
        elif item.get('trackType') == ['Audio']:
            audios.append(item)
    if not tracks:
        raise RuntimeError('No separate video streams found; this player format is unsupported.')
    audio = next((x for x in audios if x.get('isHls')), audios[0] if audios else None)
    return dict(sorted(tracks.items())), audio


def media_url(opener, media):
    """Resolve the public single-MP4 byte-range HLS format verified on Echo360."""
    url = media['uri']
    if not media.get('isHls') and urllib.parse.urlparse(url).path.lower().endswith('.mp4'):
        return url
    for _ in range(4):
        text = request_text(opener, url)
        if not text.lstrip().startswith('#EXTM3U'):
            raise RuntimeError('Expected an HLS playlist, received another response.')
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        if any(x.startswith('#EXT-X-KEY:') and 'METHOD=NONE' not in x for x in lines):
            raise RuntimeError('Encrypted/protected media is not supported.')
        variants = []
        for i, line in enumerate(lines):
            if line.startswith('#EXT-X-STREAM-INF:'):
                resolution = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
                bandwidth = re.search(r'(?:^|,)BANDWIDTH=(\d+)', line.split(':', 1)[1])
                following = next((x for x in lines[i+1:] if not x.startswith('#')), None)
                if following:
                    area = int(resolution[1])*int(resolution[2]) if resolution else 0
                    variants.append((area, int(bandwidth[1]) if bandwidth else 0, following))
        if variants:
            url = urllib.parse.urljoin(url, max(variants)[2])
            continue
        init = re.search(r'#EXT-X-MAP:.*?URI="([^"]+)"', text)
        segments = [x for x in lines if not x.startswith('#')]
        if not init or not segments:
            raise RuntimeError('Unsupported HLS layout: expected one MP4 with byte-range segments.')
        target = urllib.parse.urljoin(url, init[1])
        if not urllib.parse.urlparse(target).path.lower().endswith('.mp4') or any(urllib.parse.urljoin(url, x) != target for x in segments):
            raise RuntimeError('This playlist uses separate media segments; this toolkit supports the verified single-MP4 layout only.')
        return target
    raise RuntimeError('Too many nested playlists.')


def fetch_file(opener, url, path):
    for attempt in range(3):
        try:
            with opener.open(url, timeout=120) as response, Path(path).open('wb') as output:
                total = int(response.headers.get('Content-Length', 0))
                received = 0
                last = time.monotonic()
                while block := response.read(1024*1024):
                    output.write(block)
                    received += len(block)
                    if time.monotonic() - last > 10:
                        status_line(f'Downloaded {received/1024**2:.1f} MiB' + (f' / {total/1024**2:.1f} MiB' if total else ''), 'PROGRESS')
                        last = time.monotonic()
            if not received or (total and received != total):
                raise OSError('Incomplete HTTP download')
            return
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            status_line('Download interrupted; retrying from the beginning.', 'WARNING')
            time.sleep(2)


def ff_run(arguments):
    result = subprocess.run([FF, '-hide_banner', *arguments], capture_output=True, text=True,
                            encoding='utf-8', errors='replace', creationflags=NO_WINDOW)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:] or 'FFmpeg failed.')
    return result


def inspect(path):
    result = subprocess.run([FF, '-hide_banner', '-i', str(path)], capture_output=True,
                            text=True, encoding='utf-8', errors='replace', creationflags=NO_WINDOW)
    text = result.stderr
    duration = re.search(r'Duration: (\d+):(\d+):([\d.]+)', text)
    resolution = re.search(r'Video:.*?\b(\d{2,5})x(\d{2,5})\b', text)
    if not duration:
        raise RuntimeError(f'Cannot read media duration: {path}')
    return dict(seconds=int(duration[1])*3600+int(duration[2])*60+float(duration[3]),
                resolution=f'{resolution[1]}x{resolution[2]}' if resolution else None,
                audio='Audio:' in text, aac='Audio: aac' in text)


def verify(path, expected=None, require_audio=True):
    info = inspect(path)
    if not info['resolution'] or (require_audio and not info['audio']):
        raise RuntimeError(f'Missing video or audio: {path}')
    if expected is not None and abs(info['seconds']-expected) > 2:
        raise RuntimeError(f'Duration mismatch: {path}: {info["seconds"]} vs {expected}')
    commands = [['-v', 'error', '-i', str(path), '-map', '0', '-c', 'copy', '-f', 'null', '-']]
    for position in (0, info['seconds']/2, max(0, info['seconds']-2)):
        commands.append(['-v', 'error', '-threads', '2', '-ss', str(position), '-i', str(path), '-t', '1', '-f', 'null', '-'])
    for command in commands:
        result = ff_run(command)
        if result.stderr.strip():
            raise RuntimeError(f'Playback check reported errors: {result.stderr[:1500]}')
    return info


def pin(path):
    if os.name == 'nt':
        result = subprocess.run(['attrib', '+P', '-U', str(path)], capture_output=True, creationflags=NO_WINDOW)
        if result.returncode:
            status_line(f'Could not set Always keep on this device for {path}', 'WARNING')


def default_name(url):
    date = re.search(r'(\d{4}-\d\d-\d\d)T(\d\d):(\d\d)', urllib.parse.unquote(url))
    prefix = f'{date[1]}_{date[2]}-{date[3]}' if date else 'lecture'
    return prefix + '_' + hashlib.sha256(url.encode()).hexdigest()[:8]


def download(lesson_url, course_url=None, name=None, output_root=None, announce_preview=True):
    folder = Path(output_root or HOME / 'downloads').expanduser().resolve() / slug(name or default_name(lesson_url))
    with exclusive(folder / '.download.lock'):
        return _download(lesson_url, course_url, name, output_root, announce_preview)


def _download(lesson_url, course_url=None, name=None, output_root=None, announce_preview=True):
    opener, video = player(lesson_url, course_url)
    tracks, audio = select_tracks(video)
    expected = duration_seconds(video['duration'])
    folder = Path(output_root or HOME / 'downloads').expanduser().resolve() / slug(name or default_name(lesson_url))
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / 'manifest.json'
    manifest = read_json(manifest_path) if manifest_path.exists() else {'lesson_url': lesson_url, 'public_course_url': course_url, 'streams': []}
    if manifest['lesson_url'] != lesson_url:
        raise RuntimeError('This output name belongs to another lesson. Choose a different name.')
    status_line(f'Lesson: {expected/60:.1f} minutes; source IDs: {list(tracks)}\nFolder: {folder}')
    cache = folder / '_temporary'
    cache.mkdir(exist_ok=True)
    audio_path = cache / 'audio.mp4'
    known = {r['source_id']: r for r in manifest['streams']}
    for index, media in tracks.items():
        target = folder / f'source_{index}.mp4'
        old = known.get(index)
        if old and target.is_file() and target.stat().st_size == old['bytes'] and digest(target) == old['sha256']:
            status_line(f'Source {index}: already downloaded and checksum matches.', 'READY')
            continue
        if target.exists():
            raise RuntimeError(f'Existing file is unverified or changed: {target}. Move it aside before retrying.')
        if audio and not audio_path.exists():
            status_line('Shared audio...', 'DOWNLOAD')
            audio_partial = cache / 'audio.download'
            fetch_file(opener, media_url(opener, audio), audio_partial)
            audio_partial.replace(audio_path)
        raw = cache / f'source_{index}.raw.mp4'
        partial = cache / f'source_{index}.partial.mp4'
        status_line(f'Source {index} at its highest available resolution...', 'DOWNLOAD')
        fetch_file(opener, media_url(opener, media), raw)
        args = ['-v', 'error', '-i', str(raw)]
        if audio:
            args += ['-i', str(audio_path), '-map', '0:v:0', '-map', '1:a:0']
        else:
            args += ['-map', '0:v:0', '-map', '0:a:0?']
        args += ['-c', 'copy', '-movflags', '+faststart', '-y', str(partial)]
        ff_run(args)
        info = verify(partial, expected)
        partial.replace(target)
        row = dict(source_id=index, file=target.name, bytes=target.stat().st_size, sha256=digest(target), **info)
        known[index] = row
        manifest['streams'] = [known[k] for k in sorted(known)]
        manifest['expected_seconds'] = expected
        write_json(manifest_path, manifest)
        pin(target)
        raw.unlink(missing_ok=True)
        status_line(f'Source {index}: {info["resolution"]}', 'READY')
    audio_path.unlink(missing_ok=True)
    preview_files([(f'Source {r["source_id"]}', folder / r['file']) for r in manifest['streams']],
                  folder / 'SOURCE_PREVIEWS.jpg', title='SOURCE STREAM PREVIEWS - separate inputs, not the merged output', announce=announce_preview)
    return folder, manifest


def preview_files(items, output, title='INPUT VIDEO PREVIEWS - separate inputs, not the merged output', announce=True):
    from PIL import Image, ImageDraw, ImageFont
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    header = 42
    sheet = Image.new('RGB', (1440, header+300*len(items)), '#202020')
    draw = ImageDraw.Draw(sheet)
    draw.text((10, 10), title, fill='white', font=ImageFont.load_default(size=18))
    for row, (label, path) in enumerate(items):
        seconds = inspect(path)['seconds']
        positions = [min(120, seconds*.1), seconds*.5, seconds*.9]
        for col, position in enumerate(positions):
            frame = output.parent / f'.preview-{uuid.uuid4().hex}.jpg'
            ff_run(['-v', 'error', '-threads', '2', '-ss', str(position), '-i', str(path), '-frames:v', '1',
                    '-vf', 'scale=480:270:force_original_aspect_ratio=decrease,pad=480:270:(ow-iw)/2:(oh-ih)/2', '-y', str(frame)])
            with Image.open(frame) as image:
                sheet.paste(image.convert('RGB'), (col*480, header+row*300+30))
            frame.unlink()
            draw.text((col*480+8, header+row*300+8), f'{label} | {position:.0f} seconds', fill='white')
    sheet.save(output, quality=90)
    if announce:
        status_line(f'Input source previews (not the merged output): {output}', 'PREVIEW')
    return output


def update_status(job_dir, **values):
    if not job_dir:
        return
    path = Path(job_dir) / 'status.json'
    state = read_json(path) if path.exists() else {}
    state.update(values, updated=time.strftime('%Y-%m-%d %H:%M:%S'))
    write_json(path, state)
    (Path(job_dir) / 'STATUS.txt').write_text('\n'.join(f'{k}: {v}' for k, v in state.items())+'\n', encoding='utf-8')


def encoder_name(choice):
    if choice == 'cpu':
        return 'cpu'
    probe = subprocess.run([FF, '-v', 'error', '-f', 'lavfi', '-i', 'color=s=128x72:r=30',
                            '-frames:v', '1', '-c:v', 'h264_nvenc', '-f', 'null', '-'],
                           capture_output=True, creationflags=NO_WINDOW)
    if probe.returncode == 0:
        return 'nvenc'
    if choice == 'nvenc':
        raise RuntimeError('NVIDIA NVENC is unavailable or busy. Retry later or choose --encoder cpu.')
    return 'cpu'


def combine(large, small, output, encoder='auto', seconds=None, allow_different_duration=False, job_dir=None):
    paths = [Path(x).expanduser().resolve() for x in (large, small, output)]
    if len(set(paths)) != 3:
        raise ValueError('Large input, small input, and output must be three different files.')
    with exclusive(paths[2].with_suffix('.mp4.lock')):
        return _combine(*paths, encoder, seconds, allow_different_duration, job_dir)


def _combine(large, small, output, encoder='auto', seconds=None, allow_different_duration=False, job_dir=None):
    large, small, output = (Path(x).expanduser().resolve() for x in (large, small, output))
    if large == small or output in (large, small):
        raise ValueError('Large input, small input, and output must be three different files.')
    if output.suffix.lower() != '.mp4':
        raise ValueError('The output filename must end in .mp4.')
    if output.exists():
        raise FileExistsError(f'Output already exists; choose another name: {output}')
    a, b = inspect(large), inspect(small)
    if not a['resolution'] or not b['resolution']:
        raise ValueError('Both inputs must contain video.')
    if abs(a['seconds']-b['seconds']) > 2 and not allow_different_duration:
        raise ValueError('Input durations differ by more than 2 seconds. Use matching streams, or --allow-different-duration to stop at the shorter input.')
    expected = min(a['seconds'], b['seconds'])
    if seconds is not None:
        if seconds <= 0:
            raise ValueError('--seconds must be greater than zero.')
        expected = min(expected, seconds)
    audio_input = 0 if a['audio'] else 1 if b['audio'] else None
    if audio_input is None:
        raise ValueError('Neither input contains audio.')
    chosen = encoder_name(encoder)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.stem + '.partial.mp4')
    layout = ('[0:v]setpts=PTS-STARTPTS,scale=1280:720:force_original_aspect_ratio=decrease:force_divisible_by=2,'
              'pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[large];'
              '[1:v]setpts=PTS-STARTPTS,scale=480:270:force_original_aspect_ratio=decrease:force_divisible_by=2,'
              'pad=480:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[small];'
              '[large][small]hstack=inputs=2:shortest=1[out]')
    args = [FF, '-hide_banner', '-v', 'error', '-nostats', '-threads', '2', '-i', str(large),
            '-threads', '2', '-i', str(small), '-filter_complex_threads', '2', '-filter_complex', layout,
            '-map', '[out]', '-map', f'{audio_input}:a:0']
    args += (['-c:v', 'h264_nvenc', '-preset', 'p4', '-cq', '21', '-b:v', '0'] if chosen == 'nvenc'
             else ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21', '-threads', '2'])
    args += ['-pix_fmt', 'yuv420p']
    args += ['-c:a', 'copy'] if (a, b)[audio_input]['aac'] else ['-c:a', 'aac', '-b:a', '128k']
    args += ['-t', str(expected), '-shortest', '-movflags', '+faststart', '-progress', 'pipe:1', '-y', str(partial)]
    log_path = output.with_suffix('.ffmpeg.log')
    status_line(f'Encoding with {chosen}: {output}', 'ENCODE')
    update_status(job_dir, phase='encoding', output=str(output), encoder=chosen, percent=0)
    with log_path.open('w', encoding='utf-8') as log:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=log, text=True, creationflags=NO_WINDOW)
        last = 0
        for line in proc.stdout:
            key, _, value = line.strip().partition('=')
            if key == 'out_time_us' and time.monotonic()-last > 5:
                try:
                    percent = min(100, max(0, int(value)/1e6/expected*100))
                except ValueError:
                    continue
                update_status(job_dir, percent=round(percent, 1), ffmpeg_pid=proc.pid)
                status_line(f'{percent:.1f}%', 'PROGRESS')
                last = time.monotonic()
        if proc.wait():
            raise RuntimeError(f'Encoding failed. See {log_path}')
    update_status(job_dir, phase='verifying', percent=100)
    info = verify(partial, expected)
    partial.replace(output)
    pin(output)
    report = dict(file=str(output), large=str(large), small=str(small), encoder=chosen,
                  bytes=output.stat().st_size, sha256=digest(output), checks=['duration', 'video_and_audio', 'all_packets', 'start_middle_end_decode'], **info)
    write_json(output.with_suffix('.verification.json'), report)
    status_line(str(output), 'COMPLETE')
    return report


def start_background(job):
    directory = HOME / 'jobs' / (time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
    directory.mkdir(parents=True)
    write_json(directory / 'job.json', job)
    update_status(directory, state='starting')
    with (directory / 'run.log').open('wb') as log:
        kwargs = dict(stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, cwd=HOME)
        if os.name == 'nt':
            kwargs['creationflags'] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs['start_new_session'] = True
        proc = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()), '_worker', str(directory)], **kwargs)
    print()
    status_line(f'Job started. PID: {proc.pid}', 'BACKGROUND')
    status_line(f'Status: {directory / "STATUS.txt"}\nLog: {directory / "run.log"}')
    return directory


def run_batch(jobs, job_dir=None):
    results = []
    failures = []
    for number, job in enumerate(jobs, 1):
        update_status(job_dir, phase='downloading', item=number, total=len(jobs))
        try:
            folder, manifest = download(job['lesson_url'], job.get('public_course_url'), job.get('name'), job.get('output_root'))
            mapping = {r['source_id']: folder / r['file'] for r in manifest['streams']}
            big, small = int(job['large_source']), int(job['small_source'])
            if big not in mapping or small not in mapping or big == small:
                raise ValueError(f'Choose two distinct source IDs from {list(mapping)}.')
            output = folder / f'combined_large-{big}_small-{small}.mp4'
            verification = output.with_suffix('.verification.json')
            if output.exists() and verification.exists() and digest(output) == read_json(verification)['sha256']:
                results.append(read_json(verification))
                status_line(f'Already complete: {output}', 'COMPLETE')
                continue
            results.append(combine(mapping[big], mapping[small], output, encoder=job.get('encoder', 'auto'), job_dir=job_dir))
        except Exception as exc:
            failures.append(dict(item=number, lesson=job.get('lesson_url'), error=str(exc)))
            status_line(f'Item {number} failed: {exc}', 'ERROR')
    report = dict(files=results, failures=failures)
    if job_dir:
        write_json(Path(job_dir) / 'batch-report.json', report)
    if failures:
        raise RuntimeError(f'{len(failures)} batch item(s) failed. See run.log / batch-report.json; successful items were retained.')
    return report


def worker(directory):
    directory = Path(directory)
    if os.name == 'nt':
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    update_status(directory, state='running', pid=os.getpid())
    try:
        job = read_json(directory / 'job.json')
        if job['type'] == 'combine':
            report = combine(**job['options'], job_dir=directory)
        elif job['type'] == 'batch':
            report = run_batch(job['jobs'], directory)
        else:
            raise ValueError('Unknown job type.')
        write_json(directory / 'result.json', report)
        update_status(directory, state='complete', phase='complete', percent=100)
    except BaseException as exc:
        update_status(directory, state='failed', phase='failed', error=str(exc))
        traceback.print_exc()
        raise
    finally:
        if os.name == 'nt':
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


def prompt_path(label):
    return str(Path(input(label).strip().strip('"')).expanduser().resolve())


def choose_source(label, mapping):
    choices = ', '.join(str(index) for index in sorted(mapping))
    while True:
        answer = input(f'{label} ({choices}): ').strip()
        if answer.isdigit() and int(answer) in mapping:
            return int(answer)
        status_line(f'Enter one of: {list(mapping)}', 'WARNING')


def confirm_merge():
    while True:
        answer = input('Combine the downloaded streams into one video? [y/N]: ').strip().lower()
        if answer in ('y', 'yes'):
            return True
        if answer in ('', 'n', 'no'):
            return False
        status_line('Enter y or n.', 'WARNING')


def wizard_download(lesson, name, output_root):
    try:
        return download(lesson, name=name, output_root=output_root, announce_preview=False)
    except (PublicAccessRequired, urllib.error.HTTPError) as exc:
        if isinstance(exc, urllib.error.HTTPError) and exc.code not in (401, 403):
            raise
        status_line('The lesson could not be accessed directly. Its public course link may establish the required viewing session.', 'WARNING')
        status_line('URL format: https://echo360.org.uk/section/<course-id>/public')
        status_line('Copy your course page link; replace <course-id> with its actual ID.')
        course = input('Public course/section URL: ').strip()
        if not course:
            raise PublicAccessRequired('No course URL supplied. Open the public course in your browser and copy its URL.') from exc
        return download(lesson, course_url=course, name=name, output_root=output_root, announce_preview=False)


def wizard():
    print(colored(BANNER, '36', sys.stdout))
    print('1. Download a lesson (optional merge)\n2. Combine two existing local video files\n3. Run a batch JSON file in the background\n')
    mode = input('Choose 1, 2, or 3 [1]: ').strip() or '1'
    if mode == '3':
        config = read_json(prompt_path('Batch JSON path: '))
        start_background({'type': 'batch', 'jobs': config['jobs']})
        return
    if mode == '1':
        lesson = input('Specific lesson/classroom URL: ').strip()
        course_name = slug(input('Course folder name [Echo360]: ').strip() or 'Echo360')
        name = input('Video subfolder name (Enter for automatic date + ID): ').strip() or None
        parent = input(f'Download root folder [Enter: {HOME / "downloads"}]: ').strip().strip('"')
        output_root = (Path(parent).expanduser().resolve() if parent else HOME / 'downloads') / course_name
        folder, manifest = wizard_download(lesson, name, output_root)
        mapping = {r['source_id']: str(folder / r['file']) for r in manifest['streams']}
        if len(mapping) < 2:
            status_line('Only one stream is available. Download is complete; there is no second stream to combine.', 'COMPLETE')
            return
        if not confirm_merge():
            status_line(f'Download complete. Source videos are saved in: {folder}', 'COMPLETE')
            return
        preview = folder / 'SOURCE_PREVIEWS.jpg'
        print()
        status_line('SOURCE_PREVIEWS.jpg shows the separate source streams, not the final merged layout.', 'PREVIEW')
        status_line(f'File: {preview}')
        status_line('Use these input previews or the source MP4s to identify the lecturer and screen. Source IDs are not role labels.')
        if os.name == 'nt':
            try: os.startfile(preview)
            except OSError: pass
        big = choose_source('Source ID for the LARGE video on the LEFT', mapping)
        remaining = {k:v for k,v in mapping.items() if k != big}
        small = next(iter(remaining)) if len(remaining) == 1 else choose_source('Source ID for the SMALL video on the RIGHT', remaining)
        status_line(f'Layout: source {big} large / left; source {small} small / right.')
        large_path, small_path = mapping[big], mapping[small]
        output = str(folder / f'combined_large-{big}_small-{small}.mp4')
    elif mode == '2':
        large_path = prompt_path('LARGE / LEFT video path: ')
        small_path = prompt_path('SMALL / RIGHT video path: ')
        output = prompt_path('New output MP4 path: ')
    else:
        raise ValueError('Choose 1, 2, or 3.')
    encoder = input('Encoder: auto, nvenc, or cpu [auto]: ').strip() or 'auto'
    if encoder not in ('auto', 'nvenc', 'cpu'):
        raise ValueError('Encoder must be auto, nvenc, or cpu.')
    start_background({'type': 'combine', 'options': dict(large=large_path, small=small_path, output=output, encoder=encoder)})
    status_line('You can close this console. Leave the computer on while the background job runs.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('wizard')
    for name in ('inspect', 'download'):
        p = sub.add_parser(name)
        p.add_argument('--lesson', required=True)
        p.add_argument('--course')
        if name == 'download':
            p.add_argument('--name')
            p.add_argument('--output-root')
    p = sub.add_parser('preview')
    p.add_argument('files', nargs='+')
    p.add_argument('--output', required=True)
    p = sub.add_parser('combine')
    p.add_argument('--large', required=True)
    p.add_argument('--small', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--encoder', choices=['auto', 'nvenc', 'cpu'], default='auto')
    p.add_argument('--seconds', type=float, help='Encode only a short sample from the start.')
    p.add_argument('--allow-different-duration', action='store_true')
    p.add_argument('--background', action='store_true')
    p = sub.add_parser('batch')
    p.add_argument('config')
    p.add_argument('--background', action='store_true')
    p = sub.add_parser('_worker', help=argparse.SUPPRESS)
    p.add_argument('directory')
    args = vars(parser.parse_args())
    command = args.pop('command')
    if command == 'wizard':
        wizard()
    elif command == 'inspect':
        _, video = player(args['lesson'], args['course'])
        tracks, audio = select_tracks(video)
        print(json.dumps(dict(seconds=duration_seconds(video['duration']), source_ids=list(tracks), shared_audio=bool(audio)), indent=2))
    elif command == 'download':
        download(args['lesson'], args['course'], args['name'], args['output_root'])
    elif command == 'preview':
        preview_files([(f'Input {i+1}', Path(f)) for i,f in enumerate(args['files'])], args['output'])
    elif command == 'combine':
        background = args.pop('background')
        for key in ('large', 'small', 'output'):
            args[key] = str(Path(args[key]).expanduser().resolve())
        if background: start_background({'type': 'combine', 'options': args})
        else: combine(**args)
    elif command == 'batch':
        jobs = read_json(args['config'])['jobs']
        if not isinstance(jobs, list) or not jobs:
            raise ValueError('The batch file must contain a non-empty jobs array.')
        # Resolve user-provided relative folders before detaching the worker.
        for job in jobs:
            if job.get('output_root'):
                job['output_root'] = str(Path(job['output_root']).expanduser().resolve())
        if args['background']: start_background({'type': 'batch', 'jobs': jobs})
        else: run_batch(jobs)
    elif command == '_worker':
        worker(args['directory'])


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        status_line('Stopped. Completed files were retained.', 'WARNING', stream=sys.stderr)
        sys.exit(130)
    except Exception as error:
        status_line(str(error), 'ERROR', stream=sys.stderr)
        sys.exit(1)
