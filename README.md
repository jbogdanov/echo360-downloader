# echo360-downloader

```text
   _____ ____ _   _  ___  _____   __    ___
  | ____/ ___| | | |/ _ \|___ /  / /_  / _ \
  |  _|| |   | |_| | | | | |_ \ | '_ \| | | |
  | |__| |___|  _  | |_| |___) || (_) | |_| |
  |_____\____|_| |_|\___/|____/  \___/ \___/

                 R I P P E R
       Download. Preview. Choose. Combine.
```

Download public Echo360 lectures for offline viewing. Choose a single lesson or select several lessons from a course, then optionally combine two video streams into one MP4 with a large video on the left and a smaller video on the right.

Each downloaded source MP4 includes audio and can be watched independently. Merging is optional; it puts both pictures into one video with a single audio track.

This project was fully created with Codex GPT-6 Astra.

## 1. Set up the toolkit

You need Windows 10 or 11, Python **3.10 or newer**, an internet connection for setup and downloads, and enough disk space for the source videos and merged output. An NVIDIA GPU is optional; CPU encoding is supported.

1. Download or clone this repository into a folder where you want to keep the toolkit.
2. Keep the repository files together, including `echo360_tool.py`, `course_picker.py`, `file_picker.py`, the `.cmd` launchers, `setup.ps1`, and `requirements.txt`.
3. Double-click **`SETUP.cmd`** and wait for **Setup complete**. This creates a private `.venv` and installs the dependencies, including FFmpeg. You do not need a separate FFmpeg installation or administrator privileges.
4. Double-click **`START.cmd`** to open Echo360 Ripper. If setup has already been completed on this computer, start here.

`START.cmd` also runs setup automatically if the private Python environment is missing. When copying the toolkit to another computer, leave `.venv` behind and run setup again there.

## 2. Choose your workflow

Use **Up / Down** to move the `>` marker, then press **Enter** to open the selected workflow. The current choice is also highlighted in color when supported:

```text
Up/Down: move | Enter: choose | Q/Esc: quit

> Download a lesson (optional merge)
  Combine two existing local video files
  Select lessons from a public course and batch download (optional merge)
  Run a saved batch JSON file
```

| You want to… | Choose |
|---|---|
| Download one recording and optionally merge its streams | [Option 1](#option-1-download-one-lesson-and-optionally-merge) |
| Merge two videos already on your computer | [Option 2](#option-2-combine-two-local-videos) |
| Mark several lessons with `[X]`, download them, and optionally merge with one layout for all | [Option 3](#option-3-select-course-lessons-and-batch-download) |
| Rerun a saved selection or use a prepared download/merge batch | [Option 4](#option-4-run-a-saved-batch) |

The first workflow is selected initially, so pressing Enter opens option 1. The option numbers in this guide refer to the four rows above: move to that row and press Enter. **Home / End** jump to the first / last row; **Q / Esc** exits. Open `START.cmd` again whenever you want to begin another workflow. If the console cannot support keyboard navigation, the toolkit falls back to the numbered prompt.

### Get the correct Echo360 link

For **one lesson**, open the recording in Echo360 and copy its complete URL from the browser:

```text
https://echo360.org.uk/lesson/<lesson-id>/classroom
```

For **a course**, copy the public course page URL:

```text
https://echo360.org.uk/section/<course-id>/public
```

Example course URL with a placeholder ID:

```text
https://echo360.org.uk/section/12345678-1234-1234-1234-123456789abc/public
```

Use your actual URL, not the placeholder. Lesson and course IDs are different. Some lesson IDs contain long date/time strings; copy the entire link, including any query string.

Option 1 asks for a course link only if it needs one to access the lesson. Option 3 starts with the course link and discovers the lessons for you.

## Option 1: Download one lesson and optionally merge

Follow these prompts in order:

1. Open `START.cmd` and choose **1**.
2. At **Specific lesson/classroom URL**, paste the recording's full URL.
3. At **Course folder name [Echo360]**, enter a name such as `Course`, or press Enter for `Echo360`.
4. At **Video subfolder name**, enter a name such as `02`, or press Enter for an automatic date/ID name.
5. At **Download root folder**, press Enter for the toolkit's `downloads` folder, or enter an absolute path such as `C:\Videos\Echo360`. With the example names and default root, the destination is `downloads\Course\02`.
6. If **Public course/section URL** appears, paste that course's public link. Visiting it establishes the viewing session needed by some lessons.
7. Wait while every available source stream downloads at its highest listed resolution and receives the shared audio. **Keep this console open during this download stage.**
8. At **Combine the downloaded streams into one video?**, **Yes** is selected by default. Press **Enter** to merge, or use the arrow keys to select **No** and press Enter to finish with separate MP4s.
9. After you select **Yes** to accept merging, the toolkit creates and opens a temporary `SOURCE_PREVIEWS.jpg`. Inspect the rows to identify the camera and computer screen. These are **input source previews**, not a preview of the final merged layout. The image is removed after a successful merge.
10. At **Source ID for the LARGE video on the LEFT (1, 2)**, enter the ID you want large. The prompt lists the actual available IDs. With two streams, the other becomes small on the right automatically. With more than two, choose the small source from a second prompt.
11. At **Encoder**, press Enter for **Auto**, or use the arrow keys to choose **CPU** or **NVIDIA (NVENC)** and press Enter.
12. The merge starts in the background, and live status appears in the same console. Wait for **Job complete. All output checks passed.** The result is saved beside the source files, for example `combined_large-2_small-1.mp4`.

If the lesson contains only one video stream, downloading completes without a merge question. If you select **No** to decline merging, both source MP4s remain ready to play with audio, and no preview image is created.

**Source IDs are not role labels.** Source 1 might show slides in one lesson and the lecturer in another. Choose using the previews or play the source MP4s. The previews sample the beginning, middle, and end; inspect more of the recording if the content changes.

### Choose an encoder

Yes/No and encoder selectors use arrow keys and Enter, with the current choice highlighted in green and keyboard controls in a bottom footer. **Q / Esc** cancels before starting a job. In consoles without keyboard navigation, the text prompts remain available: `[yes] no` accepts Enter for yes, and the encoder prompt accepts `auto`, `cpu`, or `nvenc`.

| Choice | Behavior |
|---|---|
| `auto` — default | Tests NVIDIA NVENC and uses it if available; otherwise uses the CPU. |
| `nvenc` | Requires a working NVIDIA encoder. Reports an error if unavailable or busy. |
| `cpu` | Works without an NVIDIA GPU; encoding is usually slower. |

A failure after encoding starts is reported rather than automatically restarted with another encoder.

## Option 2: Combine two local videos

Use this after a course batch download, or whenever you already have both source files.

1. Open the lesson folder and play both source MP4s to decide which picture should be large. You can also create a comparison image using the advanced `preview` command below.
2. Open `START.cmd` and choose **2**.
3. The **LARGE / LEFT** file browser opens in the project's `downloads` folder. A header and divider identify which video you are choosing. Use **Up / Down** to move the green `>` selection and **Enter** to open a folder or select a video, such as `Course\02\source_2.mp4`. If `downloads` does not exist yet, the browser starts in the project folder.
4. The **SMALL / RIGHT** browser opens in the large video's folder. Choose the other source, such as `source_1.mp4`. The already selected large video is hidden from this list.
5. The output path is generated automatically and displayed. With these sources, it is `combined_large-2_small-1.mp4` in the same lesson folder, just like option 1.
6. Use the arrow keys to choose **Auto**, **CPU**, or **NVIDIA (NVENC)**, then press Enter. **Auto** is selected by default.
7. Watch the background merge's progress. When all checks pass, open the output MP4 in your video player.

Keyboard controls appear on one line above the file list, with blue key names and descriptions in the default color, separated from the current path by a blank line. The helper text has a blank line before and after it. Use **Backspace** or the **[..] Parent folder** row to go up, **Page Up / Page Down** to scroll, and **Home / End** to jump to the first / last entry. Press **P** to paste a folder or video path, including a path on another drive; quotes copied from File Explorer are accepted. **Q / Esc** cancels without starting a merge. The browser shows folders and common video formats, including MP4, MKV, MOV, and WebM.

The result is saved beside the large input. Downloaded `source_<ID>.mp4` files use their IDs in the output name; other filenames use their stems, such as `combined_large-teacher_small-slides.mp4`. Inputs and output must be different files; an existing final output is not overwritten. To reverse the layout, run option 2 again with the videos swapped; the output name follows that order.

If the console cannot support keyboard navigation, option 2 asks you to paste both video paths instead. It does not automatically open a preview. To generate a comparison image for local files, use the advanced `preview` command below.

## Option 3: Select course lessons and batch download

1. Open `START.cmd` and choose **3**.
2. At **Public course/section URL**, paste the public course link ending in `/public`.
3. Wait for the lesson list to load. It shows dates and times in the course's local timezone and indicates which recordings are available.
4. Move through the list and mark the lessons you want with **Space** or **X**. Selected lessons display `[X]`. Nothing is selected initially.
5. Press **Enter** when your selection is ready. The selected lessons are listed in the console.
6. At **Course folder name [Echo360]**, enter a name such as `Course`, or press Enter for `Echo360`.
7. At **Download root folder**, press Enter for `downloads`, or enter an absolute path. Each selected lesson gets its own automatic date/ID subfolder inside the course folder; there is no individual subfolder-name prompt in this workflow.
8. At **Combine the downloaded streams into one video?**, press Enter to accept the default **Yes**, or use the arrow keys to select **No** and press Enter to download only.
9. If merging, the toolkit reads the available source IDs from the first selected lesson. **No previews are created or opened.** At **Source ID for the LARGE video on the LEFT for all lessons (1, 2)**, choose the source you want large throughout the batch. With two streams, the other automatically becomes small; with more than two, choose the small source once too.
10. Use the arrow keys to choose **Auto**, **CPU**, or **NVIDIA (NVENC)**, then press Enter. **Auto** is selected by default. This encoder and the selected source layout apply to every lesson. Download-only batches skip the source and encoder questions.
11. The background batch downloads and, if requested, merges each lesson in sequence. Follow progress in the same window. Each lesson folder contains the source MP4s with audio and, when merged, a file such as `combined_large-2_small-1.mp4`.

```text
  [X]   1. 2026-09-01 14:00 (Europe/Tallinn) | Lecture 1
> [ ]   2. 2026-09-01 16:00 (Europe/Tallinn) | Practical session
  [X]   3. 2026-09-08 14:00 (Europe/Tallinn) | Lecture 2
  [-]   4. 2026-12-01 14:00 (Europe/Tallinn) | Lecture 3 -- Not recorded yet
```

| Key | Action |
|---|---|
| Up / Down | Move the `>` cursor |
| Space / X | Select or deselect the current lesson |
| A / N | Select all available recordings / clear the selection |
| Page Up / Page Down | Move through a long list |
| Home / End | Jump to the first / last row |
| Enter | Continue with the selected lessons |
| Q / Esc | Cancel without starting a batch |

`[ ]` means available, `[X]` means selected, and `[-]` means unavailable. Future, processing, live, and other unavailable recordings cannot be selected. An empty selection does not proceed.

If the terminal cannot display the Windows keyboard checklist, a numbered version appears instead. Type `1,3,5-7` and press Enter to toggle those rows; use `a` for all available, `n` for none, an empty Enter to continue, or `q` to cancel.

**This workflow downloads all source streams of each selected lesson, with audio in each MP4.** Optional merging uses the same source IDs for every selected lesson. IDs are not camera/screen role labels, so the visible content can differ between lessons even with the same layout. For individual layouts, use **option 2** afterward or prepare a per-lesson batch with **option 4**. Option 3 creates no preview images, and completed downloads remove their `_temporary` folder.

If the first selected lesson has fewer than two streams, merging cannot start; choose download-only or start the selection with a two-stream lesson. If a later lesson lacks a chosen source, its downloaded videos remain available, the error is recorded, and the batch continues with the remaining lessons.

While running, the selection is saved in `jobs\<job-id>\job.json`. After success, the temporary job folder is removed and the selection and results are kept in one file: `job-history\<job-id>.json`. If a lesson fails, the batch records the error and continues with the remaining lessons; failed-job folders are retained. Use option 4 with either saved batch file to rerun the selection. Completed downloads whose checksums still match are reused.

## Option 4: Run a saved batch

### Rerun a course selection

1. Find `job-history\<job-id>.json` for a successful batch, or `jobs\<job-id>\job.json` for a failed batch.
2. Open `START.cmd` and choose **4**.
3. At **Batch JSON path**, paste the full path to that JSON file.
4. Watch the background batch in the same console. It reuses verified source files and retries unfinished downloads.
5. Review `batch-report.json` in the new job folder if any items fail.

You can also drag the saved batch file onto **`RUN_BATCH.cmd`**. Wait for the previous batch to finish or stop it before rerunning the same destinations.

### Prepare a download-and-merge batch

1. Copy [examples/batch.example.json](examples/batch.example.json) to `batch.json`.
2. Replace each placeholder lesson URL and public course URL with your actual links.
3. Give each job a distinct `name` and set `output_root` to the desired **course folder**, for example `C:/Videos/Echo360/Course`. Unlike the wizard, JSON jobs do not prompt for a course folder.
4. Inspect each lesson's source previews or MP4s. Set `large_source` and `small_source` to two different IDs for that lesson, and choose an `encoder`. Roles can differ between lessons.
5. Save the JSON file. Use forward slashes in paths, or escape backslashes as `\\`.
6. Run it with option **4**, or drag it onto `RUN_BATCH.cmd`.
7. The batch downloads, verifies, merges, and verifies each lesson in sequence. Its merged file is named `combined_large-<ID>_small-<ID>.mp4` inside that lesson's folder.

For an item that should only download, set `"action": "download"` and omit `large_source`, `small_source`, and `encoder`. An omitted `action` means download and combine. The saved selection from option 3 contains either download-only items or merge items with your chosen source IDs and encoder.

The report lists download-only results under `downloads`, merged results under `files`, and errors under `failures`. A failed item does not prevent later items from running. Reruns reuse verified completed files. To reverse a completed layout, use option 2 with the input paths swapped. For a custom output filename, use the advanced `combine` command below.

## 3. Monitor a running job

Once **[BACKGROUND] Job started** appears, the worker runs independently of the console. Options 1 and 2 launch background merging; options 3 and 4 launch the whole batch in the background.

During encoding, progress updates about once per second:

```text
[########------------]  40.0% | 3.2x | ETA 00:17:15 | nvenc
```

`3.2x` means about 3.2 seconds of video processed per second. ETA estimates the remaining encoding time; verification follows afterward. Batch status also shows the current item, such as `Job 2/8`, and download messages include transferred MiB when available.

1. Leave the monitor open to follow progress, or close it / press **Ctrl+C** to stop watching. The background worker continues.
2. To reopen progress in a separate window, double-click **`WATCH.cmd`**. It shows the most recently started job.
3. To watch a particular job, drag its folder or `STATUS.txt` onto `WATCH.cmd`. For a completed job, drag its `job-history\<job-id>.json` record onto the launcher instead. `WATCH.cmd` also finds the latest job after its temporary folder has been removed.
4. Wait for the completion message before treating the output as ready. If the monitor reports an error, open `run.log` and, for batches, `batch-report.json` in that job's folder.

**Option 1's initial download is still in the foreground:** keep its console open until downloading finishes. Closing it before the background merge starts interrupts that download.

Keep the computer powered on while a job runs. The worker prevents automatic Windows sleep, but shutdown, restart, manual sleep, or a laptop lid action can interrupt it. Internet is needed for downloads, but not for merging local files.

To stop processing itself, use Task Manager's Details view and the worker / active FFmpeg PIDs in `status.json`. Stop the worker and its active FFmpeg process. Closing only the monitor does not stop them. Interrupted transfers and encoding restart from the beginning of the affected file; completed verified files remain. Jobs do not restart automatically after reboot.

Console output uses `>` markers and colored labels: cyan for information, green for completed steps, yellow for warnings, red for errors, and blue for progress. Logs remain plain text. Set `NO_COLOR` to disable colors.

## 4. Find the output and watch offline

For option 1 with course `Course` and video subfolder `02`, the files look like this:

```text
downloads/
  Course/
    02/
      source_1.mp4
      source_2.mp4
      manifest.json
      combined_large-2_small-1.mp4       (if merged)
      combined_large-2_small-1.verification.json
      combined_large-2_small-1.ffmpeg.log (only kept for errors/failed jobs)
```

Source counts vary. Option 3 uses automatic date/ID subfolders instead of `02`. Option 2 automatically names the output and saves it beside the large input.

1. Open `source_1.mp4` or `source_2.mp4` to watch that stream with the lecture audio, or open the combined MP4 to watch both pictures together. A separate audio file is not needed.
2. Confirm playback and audio, including a point near the end.
3. If the files are in OneDrive, confirm they are available locally. The toolkit requests **Always keep on this device** for final MP4s.
4. Before a flight, disconnect from the network and check that the files still play.

`SOURCE_PREVIEWS.jpg` is a temporary comparison of separate inputs, created when you accept merging in option 1 and removed after success. Option 3 does not create previews. The downloader also removes its `_temporary` folder after all source files are ready. Files from interrupted downloads are retained for retrying; unexpected files you place in `_temporary` are preserved. A `.partial.mp4` is unfinished; use the final MP4 after successful verification. Keep `manifest.json` and verification reports with their videos so later runs can recognize completed downloads and merges.

Temporary `.download.lock` and `*.mp4.lock` files protect active tasks from duplicate writers and are removed when the task releases them. After a merge and its verification succeed, an empty `*.ffmpeg.log` is deleted automatically. Logs containing errors, and logs from failed jobs, are retained for troubleshooting.

Successful background jobs also remove their temporary `jobs\<job-id>` folder after the worker exits. One JSON completion record remains in `job-history\<job-id>.json`, containing the inputs, final status, and results. This keeps monitoring and batch reruns available without retaining progress logs and temporary status files. Active, failed, and interrupted jobs are kept in `jobs/`. Cleanup preserves any unexpected files you add to a job folder.

### Combined layout and synchronization

| Element | Output |
|---|---|
| Large video | Left, fitted inside 1280 × 720 |
| Small video | Right, fitted inside 480 × 270 and vertically centered |
| Complete frame | 1760 × 720, 30 fps |
| Format | MP4, H.264 video, one AAC audio track |

Both images keep their aspect ratio, with black padding as needed. The smaller picture sits beside the larger one and does not cover it. The original source files remain available for viewing small text at full size.

The combined file uses one input's audio track, so the shared lecture audio is not played twice. For other local files, it uses the large input's audio when available, otherwise the small input's audio.

The two video timelines start together. Inputs must normally match in duration within two seconds. The toolkit does not detect or repair timing offsets between unrelated recordings. Existing black frames or missing-camera content remain in the output.

### Job files

These files exist while a job runs and are retained if it fails. After success, its folder is replaced by the single completion record in `job-history/`.

| File under `jobs/<job-id>/` | Purpose |
|---|---|
| `job.json` | Saved inputs; batch jobs can be rerun through option 4 |
| `STATUS.txt`, `status.json` | Current state, progress, and process IDs |
| `launcher.json` | Process ID used while the worker starts |
| `run.log` | Messages and errors |
| `result.json` | Successful job result |
| `batch-report.json` | Per-item successes and failures for a batch |

`state: complete` means required checks passed. A failed or forcibly stopped job may leave a partial output; inspect its log and process state before retrying. Do not run simultaneous jobs targeting the same files.

## Advanced command-line usage

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

This command creates a contact sheet of the separate input files. It does not preview the merged layout. To see the actual layout, encode a short trial with `combine --seconds 20` as shown below.

An explicitly requested preview stays available after this command. A later successful merge of two files in that same folder removes `SOURCE_PREVIEWS.jpg`; use a different image filename if you want to keep it.

```powershell
.\.venv\Scripts\python.exe .\echo360_tool.py preview `
  "C:\Videos\Echo360\Lecture 05\source_1.mp4" `
  "C:\Videos\Echo360\Lecture 05\source_2.mp4" `
  --output "C:\Videos\Echo360\Lecture 05\SOURCE_PREVIEWS.jpg"
```

### Teacher large, computer small

After visually confirming that source 2 is the teacher and source 1 is the computer:

```powershell
.\.venv\Scripts\python.exe .\echo360_tool.py combine `
  --large "C:\Videos\Echo360\Lecture 05\source_2.mp4" `
  --small "C:\Videos\Echo360\Lecture 05\source_1.mp4" `
  --output "C:\Videos\Echo360\Lecture 05\teacher-large.mp4" `
  --encoder auto --background --watch
```

For slides large, swap the two input paths and use another output name. Omit `--watch` to return immediately after launching the background job. Without `--background`, the job runs in the foreground and prints progress there; closing that console can interrupt it.

### Make a short trial before encoding a long lecture

```powershell
.\.venv\Scripts\python.exe .\echo360_tool.py combine `
  --large "C:\Videos\Echo360\Lecture 05\source_2.mp4" `
  --small "C:\Videos\Echo360\Lecture 05\source_1.mp4" `
  --output "C:\Videos\Echo360\Lecture 05\preview-20s.mp4" `
  --seconds 20 --encoder cpu
```

`--seconds` encodes only the specified number of seconds from the beginning. Omit it for the full lecture.

### Run or watch a batch

```powershell
.\.venv\Scripts\python.exe .\echo360_tool.py batch .\batch.json --background --watch

# Watch the most recently started job
.\.venv\Scripts\python.exe .\echo360_tool.py watch

# Watch a specific job; replace the folder with your actual job ID
.\.venv\Scripts\python.exe .\echo360_tool.py watch ".\jobs\20261025-120000-a1b2c3"
```

`--watch` requires `--background`. Omit `--watch` to launch a background job and return immediately. For command help, use `echo360_tool.py combine --help` or another command followed by `--help`.

NVENC uses preset `p4` with CQ 21. CPU encoding uses `libx264`, preset `veryfast`, and CRF 21. For local files of unequal duration, `combine --allow-different-duration` explicitly allows output to stop at the shorter input; it does not repair synchronization.

## Supported recordings

The downloader supports publicly viewable Echo360 lessons using the unencrypted, single-MP4 byte-range HLS format verified on the supplied Echo360 UK courses, plus directly exposed MP4 tracks. A public course URL establishes a viewing session when needed; its cookies stay in the downloader's session. The tool does not import browser cookies or store account passwords.

Login-only institutional pages, DRM/encrypted streams, and HLS with separate media files are not implemented. Course discovery depends on the current public course page and syllabus format. Platform changes may require an update.

## Troubleshooting

| Message or symptom | What to do |
|---|---|
| Public player or course configuration not found | Check the full URL and confirm the page is publicly viewable. Option 1 may also need the course's public link. |
| HTTP 403 / access denied | Retry with the public course link to establish a fresh viewing session. Do not reuse expired CDN links. |
| A lesson is marked `[-]` | It has no available video, is still processing, or is live. Reload the course later if availability changes. |
| Numbered selection appears instead of arrow-key controls | Use numbers/ranges, or open `START.cmd` in a supported Windows console. |
| Encrypted/protected or unsupported HLS layout | This recording format is not implemented. Use Echo360's official download option if available. |
| Existing file is unverified or changed | Move that file aside before retrying. Keep completed files together with their manifest or verification report. |
| Output already exists | Move or rename the existing result, or use the advanced `combine` command with a different output path. A batch can reuse a completed merge when its verification report and checksum match. |
| Durations differ | Confirm both files belong to the same lesson. Use the advanced shorter-input override only when appropriate. |
| No signal / black picture | Inspect the source MP4 at several points; the original recording may lack a camera or screen signal. |
| NVENC unavailable or busy | Wait for other GPU work to finish, choose `cpu`, or use `auto`. |
| Installation failed | Check Python 3.10+ and internet access, then rerun `SETUP.cmd`. |
| Toolkit folder moved / copied `.venv` no longer works | Close toolkit processes, move the old `.venv` out of the toolkit folder, and rerun `SETUP.cmd` to create a new one. Preserve downloads and jobs; saved jobs may contain old absolute paths. |
| Disk full | Free space and retry. Temporary download files are in each lesson's `_temporary` folder. |
| Batch finished with failures | Inspect `batch-report.json` and `run.log`, resolve the cause, then rerun the saved batch with option 4. |

## Project files

| File | Purpose |
|---|---|
| `START.cmd` | Interactive menu |
| `SETUP.cmd`, `setup.ps1`, `requirements.txt` | Private Python environment and dependencies |
| `WATCH.cmd` | Reopen live progress |
| `RUN_BATCH.cmd` | Run a saved batch dropped onto the launcher |
| `echo360_tool.py` | Downloader, previews, merging, wizard, and background worker |
| `course_picker.py` | Public course discovery and console checklist |
| `file_picker.py` | Console file browser for local merge inputs |
| `examples/batch.example.json` | Editable download-and-merge batch example |
| `tests/` | Offline tests for downloading, selection, merging guards, and monitoring |

## Validation

Validation recorded on **25 October 2026**, on Windows with Python 3.13, imageio-ffmpeg 0.6.0, Pillow 12.2.0, and bundled FFmpeg 7.1:

- **71 automated tests passed**, covering playlist parsing, source IDs, overwrite guards, main-menu, Yes/No, encoder, and file-browser navigation, terminal restoration, wizard prompts and automatic output naming, course discovery/selection and shared batch layouts without previews, batch failure handling, live monitoring, lock cleanup with concurrent processes, and completed-job cleanup.
- Local HTTP integration downloaded two streams plus shared audio, muxed and verified the outputs, created source previews, and checked checksum-based reuse. A two-lesson download batch also completed successfully.
- All eight source MP4s checked across four downloaded lessons contained AAC audio. Ten-second samples starting one minute into each file decoded with non-silent audio; this was a sample check, not a full listening review.
- Metadata discovery succeeded for all four supplied public courses. The Windows checklist was exercised in a real console using Space/X, arrows, Page Down, and Enter.
- Real lecture files were merged into short CPU-encoded samples in both layout orientations. Output checks passed, and the layout was visually reviewed.
- Background monitoring was verified with eight- and sixty-second samples. Closing one monitor left the worker running; another monitor observed successful completion.
- Setup worked from a path containing spaces and Estonian characters.
- Cleanup checks verified that completed downloads leave no `_temporary` folder, download-only jobs create no source preview, and successful merges remove their source preview and empty FFmpeg log. Completed downloads and merges leave no lock files, failed verification retains its log, and a competing process cannot remove an active owner's lock. Compatibility with locks held by older Windows workers was also checked.
- Job cleanup tests covered retained completion records and batch inputs, reopening the monitor after cleanup, active/failed-job preservation, cleanup retries, and preserving unexpected user files.
- A real three-second background merge completed, its temporary job folder was automatically removed, and the monitor reopened successfully from its completion record. Cleanup of read-only completed job files and folders was also tested on Windows.

Run the reproducible offline tests from the toolkit folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Verification checks duration, video/audio presence, reading all media packets, and decoding samples at the beginning, middle, and end. Manifests and output reports record SHA-256 hashes. These checks do not replace a full content review.

A full multi-hour batch was not repeated during these toolkit checks. The sample merge tests used the CPU; NVIDIA encoding uses the established FFmpeg settings from the earlier lecture queue. Support for every Echo360 deployment is not claimed.

Downloaded media, local job logs, completion history, and validation samples are excluded from Git. A fresh clone contains the scripts, documentation, example configuration, and reproducible tests.
