# Local validation

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
