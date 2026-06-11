---
title: "scikit-video: Video I/O and Quality Metrics in Python — Guide, Examples, and Alternatives"
date: 2026-01-21T09:00:00+00:00
last_modified_at: 2026-06-11T09:00:00+00:00
topic_kind: "package"
topic_id: "scikit-video"
topic_version: 2
categories:
  - Engineering
  - AI
tags:
  - python
  - package
  - pypi
  - video-processing
  - ffmpeg
  - computer-vision
  - numpy
excerpt: "What scikit-video still does well — NumPy-first video I/O and quality metrics like PSNR and SSIM — where it shows its age, and when to reach for PyAV, imageio, decord, or torchvision instead."
header:
  overlay_image: /assets/images/2026-01-21-package-scikit-video/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-01-21-package-scikit-video/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Why scikit-video matters

Most Python video libraries make you think about codecs, containers, pixel formats, and stream timestamps before you get a single frame. scikit-video (import name `skvideo`) made a different bet: hide FFmpeg entirely and hand you the video as a plain NumPy array with shape `(frames, height, width, channels)`. One function call in, one function call out. If you live in NumPy — and almost everyone doing scientific computing or ML preprocessing does — that ergonomic choice is still the best part of the library.

That design decision is why skvideo keeps showing up in research code a decade after its heyday. A video that is "just an array" composes with everything: slicing gives you temporal cropping, fancy indexing gives you frame sampling, and any NumPy-compatible operation becomes a video filter for free. The library also ships something most I/O wrappers do not: a `skvideo.measure` module with full-reference quality metrics like PSNR and SSIM, which turns it into a small but genuinely useful video-QA toolkit.

The honest caveat, which I will spend real time on below, is that the project is dormant. It still works in the right environment, but you have to know exactly where the cracks are — particularly around modern NumPy — before you put it anywhere near production.

## Quick start

Installation is one line, but there is a hard system requirement: FFmpeg must be installed and on your `PATH`, because skvideo shells out to the `ffmpeg` and `ffprobe` binaries for every decode and encode.

```bash
pip install scikit-video
# Debian/Ubuntu
sudo apt-get install ffmpeg
# macOS
brew install ffmpeg
```

Here is the complete read–process–write loop. Any local clip works; I use `input.mp4` as the placeholder.

```python
import numpy as np
import skvideo.io

# Read the entire clip into a single NumPy array
video = skvideo.io.vread("input.mp4")  # any local video file works here
print(video.shape, video.dtype)
# e.g. (240, 720, 1280, 3) uint8 -> 240 frames of 1280x720 RGB

# "Process" it: temporal subsample to every 2nd frame and darken by 30%
processed = (video[::2].astype(np.float64) * 0.7).astype(np.uint8)

# Write the result, requesting H.264 with a widely compatible pixel format
skvideo.io.vwrite(
    "output.mp4",
    processed,
    outputdict={"-vcodec": "libx264", "-pix_fmt": "yuv420p"},
)
```

That is the whole API surface most people ever need. Note the `outputdict` argument on `vwrite`: it passes flags straight through to FFmpeg, so you get the full encoder option space (`-crf`, `-preset`, `-r`, and so on) without skvideo inventing its own abstraction. I consider that pass-through design one of the library's smarter calls — it ages well precisely because it does not try to wrap FFmpeg's option space.

## Reading large videos without exhausting RAM

`vread` is a trap on long videos. A ten-minute 1080p clip at 30 fps is 18,000 frames; as uint8 RGB that is roughly 112 GB decompressed. The fix is streaming, and skvideo offers two equivalent entry points: the `skvideo.io.vreader` generator and the lower-level `skvideo.io.FFmpegReader` class.

```python
import skvideo.io

# Generator style: yields one (H, W, C) frame at a time
for i, frame in enumerate(skvideo.io.vreader("input.mp4")):
    if i % 30 == 0:
        print(i, frame.mean())  # per-frame work here, constant memory

# Class style: exposes stream geometry before you iterate
reader = skvideo.io.FFmpegReader("input.mp4")
num_frames, height, width, channels = reader.getShape()
print(f"{num_frames} frames at {width}x{height}")
for frame in reader.nextFrame():
    pass  # process each frame
reader.close()
```

`FFmpegReader.getShape()` is the detail worth remembering: it gives you frame count and dimensions up front, so you can pre-allocate output buffers or decide on a sampling stride before decoding anything. Pair it with `skvideo.io.FFmpegWriter` and you can transcode arbitrarily long videos frame by frame with a memory footprint of one frame.

## Quality metrics for video pipelines

`skvideo.measure` is the part of the library I still reach for. It implements full-reference metrics — PSNR, SSIM, MSE, and several research-grade ones — operating directly on frame arrays:

```python
import numpy as np
import skvideo.io
import skvideo.measure

# Any two local clips of the same dimensions work here,
# e.g. a source and its re-encoded copy
original = skvideo.io.vread("input.mp4", as_grey=True)
compressed = skvideo.io.vread("input_crf35.mp4", as_grey=True)

n = min(len(original), len(compressed))
psnr_per_frame = skvideo.measure.psnr(original[:n], compressed[:n])
ssim_per_frame = skvideo.measure.ssim(original[:n], compressed[:n])

print(f"PSNR: mean {np.mean(psnr_per_frame):.2f} dB, "
      f"worst frame {np.min(psnr_per_frame):.2f} dB")
print(f"SSIM: mean {np.mean(ssim_per_frame):.4f}")
```

Why does this matter? Because every video pipeline silently re-encodes. Your dataset preparation script, your annotation tool, your cloud upload path — each step can introduce compression loss, and downstream models will happily train on the degraded result without complaining. A full-reference metric gives you a regression test for visual fidelity: run PSNR/SSIM between source and processed output in CI, alert when the worst-frame score drops below a threshold, and you catch a misconfigured `-crf` flag before it poisons a training run. Per-frame scores (rather than a single average) are key — encoder failures are usually localized to scene cuts or high-motion segments, and the minimum tells you what the mean hides.

## When to use it

- **Research scripts and notebooks** where the video-as-array model makes exploration fast and the clips are short enough for `vread`.
- **Quality measurement.** PSNR/SSIM over NumPy arrays with per-frame granularity, no extra dependencies beyond SciPy.
- **Quick transcoding glue** where `outputdict`/`inputdict` pass-through to FFmpeg flags beats learning a new API.
- **Pinned, frozen environments** — a Docker image with an older NumPy where the known issues simply cannot bite you.

## When not to use it

- **New production systems.** A dormant dependency in a hot path is technical debt on day one.
- **Modern NumPy environments** (more on this next — older skvideo releases break outright).
- **High-throughput ML data loading.** Piping raw frames through a subprocess is slow compared to decord or PyAV with hardware-aware decoding.
- **Anything needing audio, subtitles, or precise seeking.** skvideo's pipe-based model only sees the video stream, front to back.

## Project health: an honest assessment

This is the section that should drive your decision, so let me be direct: scikit-video is effectively unmaintained. The last release on PyPI, 1.1.11, dates back to 2019. The GitHub repository has seen only sporadic activity since, issues accumulate without triage, and there is no sign of a release pipeline producing new versions. This is not a criticism of the authors — it is a finished research library that did its job — but it has a concrete, well-documented consequence.

The breakage is NumPy. NumPy 1.20 deprecated the old scalar aliases `np.float`, `np.int`, and `np.bool`, and NumPy 1.24 removed them entirely. skvideo 1.1.11 uses these aliases internally (notably in `skvideo.io` and `skvideo.measure`), so on any current NumPy you get `AttributeError: module 'numpy' has no attribute 'float'` the moment you call into affected code paths. This is one of the most frequently reported issues against the project, and because there is no new PyPI release, `pip install scikit-video` hands every new user a package that is broken out of the box on a modern stack.

Your practical options, in descending order of my preference:

1. **Use something else.** For new code, the alternatives below are maintained and faster.
2. **Install from the GitHub master branch**, which contains fixes that never shipped to PyPI: `pip install git+https://github.com/scikit-video/scikit-video.git`. Workable for research code; awkward for reproducible builds.
3. **Pin NumPy below 1.24** (e.g. `numpy<1.24`). I do not recommend this — you are now holding back your entire scientific stack for one I/O library.
4. **Monkey-patch the aliases** (`np.float = np.float64` before importing skvideo). It works, it is ugly, and it will eventually break something else. Last resort only.

The deeper point: a library whose known, crashing incompatibility with its single most important dependency goes unfixed on PyPI for years is telling you its maintenance status more clearly than any commit graph. Plan accordingly.

## Integration with IBM watsonx.ai

In multimodal AI workflows on watsonx.ai, the model layer typically expects images or frame batches, not container files — so something has to handle decode and frame extraction first. A small preprocessing service using skvideo's `vreader` (or, for new builds, PyAV) can sample frames at a fixed stride, normalize them as NumPy arrays, and pass them to a vision or multimodal foundation model for captioning, classification, or embedding via the watsonx.ai APIs. The same pattern works for building training corpora: decode, run quality checks with `skvideo.measure`, filter degraded clips, then push the surviving frames into Prompt Lab experiments or fine-tuning datasets. The library's role here is narrow but real — it is the deterministic, scriptable front end that turns video files into the arrays the AI layer actually consumes.

## Integration with IBM Watson Orchestrate

Watson Orchestrate automates multi-step business workflows by chaining skills and tools, and media handling is a natural fit for that pattern. A custom skill wrapping a short skvideo script can act as an automated media-QA gate: when a new asset lands — a marketing render, a training video, a compliance recording — the workflow extracts frames, computes PSNR/SSIM against the approved master, and routes the asset forward or back to a human reviewer based on the scores. The value is not the metric itself but removing a manual eyeball check from a repeatable process; Orchestrate handles the routing, notifications, and audit trail while the Python step stays a few dozen lines.

## Alternatives compared

| Library | API style | Maintenance | Speed | Best for |
|---|---|---|---|---|
| scikit-video | NumPy arrays via FFmpeg subprocess | Dormant (last PyPI release 2019) | Moderate (pipe overhead) | Quick scripts, quality metrics, legacy code |
| OpenCV (`cv2.VideoCapture`) | Imperative frame loop, BGR arrays | Active | Fast | CV pipelines already using OpenCV |
| PyAV | Pythonic bindings to FFmpeg's C libraries | Active | Fast, fine-grained | Production decode/encode, precise stream control |
| imageio / imageio-ffmpeg | Simple `imread`-style reader/writer | Active | Moderate | Drop-in skvideo replacement for simple I/O |
| decord | Random-access reader, NumPy/torch bridges | Low activity | Very fast random access | ML training data loading with frame sampling |
| torchvision.io | Tensor-native read/write | Active (API evolving) | Good, GPU-adjacent | PyTorch-only pipelines |

My take: for the exact niche skvideo occupied — "give me frames as arrays without ceremony" — **imageio with the imageio-ffmpeg plugin** is the closest maintained substitute, and migrating is usually an afternoon. For production systems where you care about seeking, timestamps, audio, or throughput, **PyAV** is the serious choice; it binds FFmpeg's libraries directly instead of spawning a subprocess, which buys you both speed and control at the cost of a steeper API. If you already depend on OpenCV, `cv2.VideoCapture` is fine — just remember it hands you BGR, not RGB, and its FFmpeg build flags vary across wheels.

For ML data loading specifically, **decord** earned its reputation: random frame access without sequential decoding makes it dramatically faster for the sample-k-frames-per-clip pattern that video models use, though its own maintenance has slowed, so weigh that. **torchvision.io** is reasonable if you are all-in on PyTorch and want tensors directly, but its video API has been through several deprecation cycles — pin your versions. Nothing on this list replicates `skvideo.measure`, which is why my own pipelines sometimes pair a modern reader with skvideo (from GitHub master) used purely as a metrics library.

## Limitations

- **Frozen at release 1.1.11 (2019)**; modern-NumPy fixes exist only on GitHub master.
- **Crashes on NumPy >= 1.24** out of the box due to removed `np.float`/`np.int` aliases.
- **Subprocess architecture**: every read/write spawns FFmpeg and pipes raw frames, adding latency and limiting throughput.
- **No random access** — streaming is strictly sequential, so frame sampling means decoding everything before the frames you want.
- **Video stream only**: no audio, subtitle, or container-metadata handling beyond `ffprobe` output.
- **`vread` memory blow-up** on long clips; you must know to switch to `vreader`.
- **Sparse documentation** that has not tracked ecosystem changes (Python versions, FFmpeg CLI changes).

## Final recommendation

Use scikit-video knowingly or not at all. If you have existing code built on it, or you want its genuinely good `skvideo.measure` metrics, install from GitHub master, pin everything, and it will keep serving you fine — the core design is sound and FFmpeg underneath has not stopped working. But for new projects in 2026, the default should be imageio for simple array-style I/O, PyAV when you need real control or performance, and decord or torchvision.io inside ML training loops. skvideo's NumPy-first ergonomics were ahead of their time; the ecosystem has since caught up while the project stood still. Respect it as the library that showed everyone how pleasant video I/O could be — then, for production, pick a maintained descendant of that idea.

## References

- [scikit-video on GitHub](https://github.com/scikit-video/scikit-video)
- [scikit-video documentation](http://www.scikit-video.org/)
- [scikit-video on PyPI](https://pypi.org/project/scikit-video/)
- [FFmpeg](https://ffmpeg.org/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
