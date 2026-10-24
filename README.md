# echo360-downloader

Download a specific public Echo360 lecture, identify its video streams, choose which one should be large, and combine them into one offline MP4. Everything runs on your own computer.

This project was fully created with Codex GPT-6 Astra.

## Quick start on this computer

1. Open this toolkit folder and double-click **`START.cmd`**.
2. Choose **1 — Download a lesson, review streams, then combine**.
3. Paste the URL of the **specific lesson**. In Echo360, open the recording and copy the full classroom URL from the address bar.
4. Paste the course's **public section URL** when prompted. This establishes the public viewing session that some recordings require.
5. Enter an optional folder name, such as `Week 05 - Cloud Architecture`. Press Enter for the automatic name. Choose a download parent folder or press Enter for this toolkit's `downloads` folder.
6. The script downloads every available video stream at its highest listed resolution and adds the lecture's shared audio to each MP4. Leave this console open during downloading.
7. `STREAM_PREVIEW.jpg` opens automatically on Windows. Each row is one source, with frames near the beginning, middle, and end. You can also play the individual `source_1.mp4`, `source_2.mp4`, etc.
8. Enter the source ID that should be **large on the left**, then the distinct source ID that should be **small on the right**.
9. Press Enter for the `auto` encoder. The script starts a detached background process and prints its status/log paths. You can now close the console.

The result is named, for example, `combined_large-2_small-1.mp4` and is saved beside the downloaded source files. The originals remain available.

**Choose by looking at the images.** A source ID is not a role: source 1 may be the screen in one lecture and the camera in another. The toolkit uses Echo360's `sourceIndex` IDs, which do not necessarily match a player's visible ordering.

If a recording has only one video stream, it is downloaded normally. The wizard then stops without manufacturing a second stream.

## Installation on another Windows computer

Requirements:

- Windows 10 or 11 and Python **3.10 or newer**. A 64-bit Python installation is recommended.
- Internet for initial setup and downloading recordings.
- Enough free disk space for both source streams, the combined MP4, and temporary files.
- An NVIDIA GPU is optional. CPU encoding is supported.

Copy the toolkit's scripts, `examples`, `tests`, and documentation to the new computer. Do not copy the `.venv` folder: Python virtual environments are specific to their installation path. Double-click **`SETUP.cmd`** once, then use **`START.cmd`**.

Setup creates a private `.venv` environment and installs the exact package versions in `requirements.txt`. `imageio-ffmpeg` supplies FFmpeg; a separate FFmpeg installation is not required. Pillow creates preview contact sheets. Setup needs no administrator privileges and does not change the system's permanent PowerShell execution policy.

The scripts also work from Python's command line. The double-click launchers and OneDrive pinning are Windows-specific.

## Which Echo360 links and recordings are supported?

Two links may be needed:

| Link | Purpose | Shape |
|---|---|---|
| Specific lesson | Selects one recording | `https://echo360.org.uk/lesson/…/classroom` |
| Public course/section | Establishes public viewing access | `https://echo360.org.uk/section/…/public` |

Copy the complete lesson URL from the browser. Some lesson IDs contain long date/time strings; keep the entire URL, including any query string. Do not invent a lesson ID from a date.

The downloader opens the public course and lesson in the **same HTTP session**, then reads the player metadata and resolves the highest-resolution playlist. It supports the unencrypted, single-MP4 byte-range HLS format verified on the supplied Echo360 UK courses, plus directly exposed MP4 tracks. It downloads the referenced MP4 rather than recording your screen.

This is a purpose-built downloader, not a universal Echo360 client. Login-only institutional pages, DRM/encrypted streams, unrelated player formats, and HLS with separate media files are not implemented. The script reports these cases explicitly. It does not import browser cookies or store your account password. Echo360 changes to its player format may require a script update.

## Output layout and synchronization

| Element | Output |
|---|---|
| Large video | Left, fitted inside 1280 × 720 |
| Small video | Right, fitted inside 480 × 270 and vertically centered |
| Complete frame | 1760 × 720, 30 fps |
| Video format | MP4 with H.264 and `yuv420p` |
| Audio | One track; AAC is copied, other audio is converted to AAC |

Both pictures preserve their aspect ratio. Black padding fills unused space. The small video sits beside the large one, so it does not cover the slides.

The video timelines start together. Downloaded Echo360 streams use the lecture's shared timeline and audio; the toolkit does not listen to the sound or automatically detect an offset between unrelated recordings. By default, input durations must match within two seconds. Existing black frames, missing-camera signals, or incorrect source content are preserved.

To reverse the layout, swap the large/small selections and choose a new output filename. There is no need to download again. Making the computer screen small naturally makes small text harder to read; keep the full-size source MP4 if you may need to inspect it later.

## Combine files you already have

Double-click `START.cmd`, choose **2**, then paste:

1. The absolute path of the video to show large on the left.
2. The absolute path of the video to show small on the right.
3. A **new** output path ending in `.mp4`.

Paths copied with quotes from File Explorer are accepted. The toolkit will not overwrite an input or an existing final output. If you want to review two local inputs first, use the `preview` command below.

## Command-line reference

Open PowerShell in the toolkit folder. These commands use its private Python environment directly, so activation is unnecessary. Replace the example URLs and filenames with real ones. Keep quotes around paths containing spaces.

### Inspect a lesson without downloading full videos

```powershell
.\.venv\Scripts\python.exe .\echo360_tool.py inspect `
  --lesson "https://echo360.org.uk/lesson/REAL_LESSON_ID/classroom" `
  --course "https://echo360.org.uk/section/REAL_SECTION_ID/public"
```

This prints the duration, available source IDs, and whether shared audio exists. It does not identify camera/screen roles; use visual previews for that.

### Download all streams of one lecture

```powershell
.\.venv\Scripts\python.exe .\echo360_tool.py download `
  --lesson "https://echo360.org.uk/lesson/REAL_LESSON_ID/classroom" `
  --course "https://echo360.org.uk/section/REAL_SECTION_ID/public" `
  --name "Lecture 05" `
  --output-root "C:\Videos\Echo360"
```

This creates `C:\Videos\Echo360\Lecture 05`. Omit `--name` for a date/URL-based name. Omit `--output-root` to use the toolkit's `downloads` directory.

Running the same download again reuses completed streams only when their saved size and SHA-256 match. An interrupted transfer is retried from the beginning; completed streams are retained. Choose a distinct lecture folder for each recording, and do not run concurrent downloads into the same folder.

### Create a visual comparison of local files

```powershell
.\.venv\Scripts\python.exe .\echo360_tool.py preview `
  "C:\Videos\Echo360\Lecture 05\source_1.mp4" `
  "C:\Videos\Echo360\Lecture 05\source_2.mp4" `
  --output "C:\Videos\Echo360\Lecture 05\comparison.jpg"
```

### Teacher large, computer small

After visually confirming that source 2 is the teacher and source 1 is the computer:

```powershell
.\.venv\Scripts\python.exe .\echo360_tool.py combine `
  --large "C:\Videos\Echo360\Lecture 05\source_2.mp4" `
  --small "C:\Videos\Echo360\Lecture 05\source_1.mp4" `
  --output "C:\Videos\Echo360\Lecture 05\teacher-large.mp4" `
  --encoder auto --background
```

For slides large, swap the two input paths and use another output name. Without `--background`, the same job runs in the current console and prints progress there.

### Make a short trial before encoding a long lecture

```powershell
.\.venv\Scripts\python.exe .\echo360_tool.py combine `
  --large "C:\Videos\Echo360\Lecture 05\source_2.mp4" `
  --small "C:\Videos\Echo360\Lecture 05\source_1.mp4" `
  --output "C:\Videos\Echo360\Lecture 05\preview-20s.mp4" `
  --seconds 20 --encoder cpu
```

`--seconds` encodes only the specified number of seconds from the beginning. Omit it for the full lecture.

### Encoder choices

- `auto`: tests NVIDIA NVENC; uses it when available, otherwise uses the CPU.
- `nvenc`: requires working NVIDIA hardware encoding. A busy/unsupported GPU produces an error instead of falling back.
- `cpu`: uses H.264/libx264, `veryfast`, CRF 21. This is slower, but needs no NVIDIA GPU.

NVENC uses preset `p4` and CQ 21. Hardware performance varies. Run a short trial if estimating a long job. Avoid starting extra encoders while another course queue is already using the GPU.

`--allow-different-duration` is an explicit override for unequal local files: the output stops at the shorter input. It does not correct synchronization offsets.

## Batch download and combine without interaction

1. Copy `examples/batch.example.json` to a new file, such as `my-lectures.json`.
2. Replace the placeholder links and names.
3. Set `large_source` and `small_source` separately for every lecture. Use the interactive/download workflow first if you have not inspected the streams.
4. Optionally add `"output_root": "C:/Videos/Echo360"` to each job. JSON accepts forward slashes; with backslashes, write them as `\\`.
5. Drag your JSON file onto **`RUN_BATCH.cmd`**, or choose **3** in `START.cmd`.

Equivalent command:

```powershell
.\.venv\Scripts\python.exe .\echo360_tool.py batch .\my-lectures.json --background
```

The batch processes items sequentially: download, verify, combine, verify, then the next item. A failed item is recorded and the batch continues to the next one. The final `batch-report.json` lists successes and failures. Rerunning the same batch reuses checksum-matching downloads and completed combined files. Do not edit a batch's source roles while reusing the same output name; choose a new output when changing settings.

A batch needs an explicit list of lesson URLs. It does not enumerate course pages, filter by start time, or infer which source contains slides.

## Background status, stopping, and recovery

Each detached job gets a folder under `jobs`, such as `jobs/20261025-120000-a1b2c3/`:

| File | Meaning |
|---|---|
| `job.json` | Exact inputs and selected layout |
| `STATUS.txt` | Readable current state and progress |
| `status.json` | The same state in JSON, including process IDs |
| `run.log` | Download/encoding messages and errors |
| `result.json` | Successful final result |
| `batch-report.json` | Per-item batch successes and failures |

`state: complete` means all required checks succeeded. `state: failed` contains an error; inspect the log. A `.partial.mp4` is an unfinished file and should not be treated as the final result.

The background worker runs independently of the launcher. It temporarily prevents automatic Windows sleep while running, without changing your permanent power settings. **Do not shut down, restart, manually sleep the computer, or close a laptop lid while it is working.** Keep it powered. Internet is required for downloads, but not for combining local files.

To stop a job, use Task Manager's Details view and the worker/FFmpeg PIDs recorded in `status.json`. Stop the worker and its active FFmpeg process. Stopping only the launcher window will not stop a detached worker. After a forced stop, the last status can remain `running`; check the PIDs before assuming it is active. There is no automatic restart after reboot.

After stopping, rerun the download or batch command. Finished verified files remain. Interrupted encoding starts again from the beginning of that lecture; the toolkit does not resume halfway through an MP4. Do not start two jobs targeting the same output file.

## Offline availability and verification

Downloaded streams are checked for video/audio, expected duration, reading every media packet, and decoding samples at the start, middle, and end. The script records file sizes and SHA-256 hashes in `manifest.json`. Combined files get their own `.verification.json` and `.ffmpeg.log`.

These checks detect many transfer and playback errors; they are not a frame-by-frame content review. The three preview positions may miss a temporary camera switch or recording outage. Play additional sections if the role is uncertain.

On Windows, the toolkit requests **Always keep on this device** using `attrib +P -U` for final MP4s. If the operation fails, it prints a note. Before a flight, confirm the OneDrive files show the local availability checkmark and try playing them with networking disabled. A normal compatible MP4 player is sufficient.

## Troubleshooting

| Message or symptom | What to do |
|---|---|
| Public player configuration not found | Use the exact lesson/classroom URL and its public course URL. Confirm the recording is publicly viewable. Login-only pages are outside this toolkit's scope. |
| HTTP 403 / access denied | Start again with the public course link so a fresh viewing session is established. Do not reuse a copied, expired CDN URL. |
| Encrypted/protected or unsupported HLS layout | This format is not implemented. Use the platform's official download option if offered. |
| Existing file is unverified or changed | Move that file aside and rerun; it is not silently replaced. Keep completed files and `manifest.json` together. |
| Output already exists | Choose a new MP4 filename. For a batch, keep the matching verification report so it can recognize completed output. |
| Durations differ | Check that both files belong to the same lesson. Use the explicit shorter-input override only when appropriate. |
| No signal / black picture | Inspect the original source MP4 and another time point. The source recording itself may lack a camera or screen signal. |
| NVENC unavailable or busy | Wait for other GPU jobs, select `cpu`, or use `auto`. A GPU failure during an encode is logged; it is not silently restarted on CPU. |
| Installation failed | Check internet access and Python 3.10+, then rerun `SETUP.cmd`. |
| Toolkit folder moved | Recreate `.venv` with `SETUP.cmd` in the new location. Old job files contain absolute input paths and may need updating. |
| Disk full | Free space, preserve completed outputs, and rerun the affected task. Temporary media is under each lecture's `_temporary` folder. |

## Included files

- `echo360_tool.py`: downloader, preview generator, combiner, wizard, batch processor, and background worker.
- `START.cmd`: interactive workflow.
- `SETUP.cmd`, `setup.ps1`, `requirements.txt`: private Python environment and dependencies.
- `RUN_BATCH.cmd`, `examples/batch.example.json`: unattended batch workflow.
- `tests/test_toolkit.py`: offline regression tests for playlist handling, source IDs, and overwrite guards.
- `tests/test_download_integration.py`: local HTTP download, audio muxing, verification, and cache reuse tests.

Run the offline tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

For help on any command, append `--help`, for example `echo360_tool.py combine --help`.

## Validation

Validated on 25 October 2026, Windows, Python 3.13, with the private environment created by `setup.ps1`.

- Setup succeeded from a folder whose path includes spaces and Estonian characters. Dependencies: imageio-ffmpeg 0.6.0 and Pillow 12.2.0; bundled FFmpeg 7.1.
- Seven automated tests passed. They cover duration parsing, highest-resolution playlist selection, relative URLs, rejecting encrypted/unsupported layouts, source IDs independent of array order, protecting input files, and an HTTP download integration test.
- The integration test generated two short video-only files and separate AAC audio, served them over local HTTP, downloaded and muxed both streams, verified playback, generated a contact sheet, and confirmed checksum-based reuse without another full transfer. Test media was temporary.
- A real public Echo360 lesson was inspected using a fresh public course session. Both video playlists and the audio playlist resolved successfully. Small HTTP range requests returned valid MP4 headers for all three tracks. Evidence: `validation/public-session-check.json`. This check did not redownload the full lecture.
- Two detached background jobs successfully combined existing real lecture files into three-second samples, one with the teacher large and one with the computer large. Both jobs reached `complete`, including packet reads and sample decoding. Both outputs contain H.264 video at 1760 × 720 and AAC audio.
- The second background job used the toolkit's private Python environment. The launcher returned before encoding completed. CPU encoding was used for these tests so the pre-existing course encoding queue could continue using the GPU.
- The generated `validation/layout-comparison.jpg` was visually reviewed: the selected large video is on the left, the small video is centered on the right, and neither overlaps the other.

The toolkit's new batch orchestration was reviewed but a full multi-hour batch was not repeated. NVIDIA encoding uses the same established FFmpeg settings as the existing lecture queue; these toolkit sample tests specifically exercised the CPU path. No claim is made that every Echo360 deployment or player format is supported.

Samples and their verification reports are kept locally under `validation`. Completed test job logs remain locally under `jobs`. These directories, lecture media, and machine-specific paths are excluded from the Git repository. They are examples, not ongoing tasks; a fresh clone contains the source code and reproducible offline tests instead.
