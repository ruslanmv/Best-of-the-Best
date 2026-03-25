---
title: "scikit-video: Video Processing in Python with FFmpeg"
date: 2026-01-21T09:00:00+00:00
last_modified_at: 2026-01-21T09:00:00+00:00
topic_kind: "package"
topic_id: "scikit-video"
topic_version: 1
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
excerpt: "scikit-video (skvideo) is a Python library for video reading, writing, and processing built on top of FFmpeg and NumPy."
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

## Introduction

scikit-video is a Python library that provides convenient functions for reading, writing, and processing video data. It wraps FFmpeg (or LibAV) behind a clean NumPy-based API, so you can load an entire video as a NumPy array, manipulate frames, and write the result back to disk -- all in a few lines of code.

The Python import name is `skvideo`, and the main I/O module is `skvideo.io`.

## Overview

Key features:

* Read video files into NumPy arrays with `skvideo.io.vread()`
* Write NumPy arrays to video files with `skvideo.io.vwrite()`
* Stream large videos frame-by-frame with `skvideo.io.FFmpegReader` and `skvideo.io.FFmpegWriter`
* Video quality metrics (SSIM, MSE, PSNR) in `skvideo.measure`
* Video utility functions in `skvideo.utils`

Use cases:

* Loading video datasets for machine learning pipelines
* Batch video transcoding and format conversion
* Computing video quality metrics
* Frame-level preprocessing for computer vision

Current version: **scikit-video 1.1.11**

Requirements: Python 3, NumPy >= 1.9.2, SciPy >= 0.16.0, and FFmpeg installed on the system.

## Getting Started

Installation:

```
pip install scikit-video
```

Make sure FFmpeg is installed and available on your PATH. On Ubuntu:

```
sudo apt-get install ffmpeg
```

Quick example -- read a video, print its shape, and write it back:

```python
import skvideo.io

# Read the entire video as a NumPy array (T, H, W, C)
video_data = skvideo.io.vread("input.mp4")
print(f"Video shape: {video_data.shape}")
# e.g. (150, 720, 1280, 3) -> 150 frames, 720x1280, 3 color channels

# Write the video back to a new file
skvideo.io.vwrite("output.mp4", video_data)
```

## Core Concepts

### Reading Video

`skvideo.io.vread(filename)` reads the entire video into memory as a 4D NumPy array with shape `(num_frames, height, width, channels)`. This is convenient for short clips but can use significant memory for long videos.

### Streaming with FFmpegReader

For large videos, use `skvideo.io.FFmpegReader` to iterate frame by frame:

```python
import skvideo.io

reader = skvideo.io.FFmpegReader("large_video.mp4")

for frame in reader.nextFrame():
    # frame is a NumPy array of shape (H, W, C)
    print(frame.shape)

reader.close()
```

### Writing Video

`skvideo.io.vwrite(filename, video_array)` writes a NumPy array to a video file. You can pass FFmpeg output parameters via the `outputdict` argument:

```python
import skvideo.io
import numpy as np

# Create a synthetic video: 60 frames of 480x640 random noise
video_data = np.random.randint(0, 255, (60, 480, 640, 3), dtype=np.uint8)

skvideo.io.vwrite(
    "synthetic.mp4",
    video_data,
    outputdict={"-vcodec": "libx264", "-pix_fmt": "yuv420p"},
)
```

### Streaming with FFmpegWriter

For frame-by-frame writing:

```python
import skvideo.io
import numpy as np

writer = skvideo.io.FFmpegWriter(
    "streamed_output.mp4",
    outputdict={"-vcodec": "libx264", "-pix_fmt": "yuv420p"},
)

for i in range(60):
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    writer.writeFrame(frame)

writer.close()
```

## Practical Examples

### Example 1: Extract and Save a Single Frame

```python
import skvideo.io
from PIL import Image

# Read the video
video_data = skvideo.io.vread("input.mp4")

# Extract the 10th frame (0-indexed)
frame = video_data[9]

# Save the frame as a PNG image
img = Image.fromarray(frame)
img.save("frame_10.png")
print(f"Saved frame with shape {frame.shape}")
```

### Example 2: Compute Video Quality Metrics

```python
import skvideo.io
import skvideo.measure
import numpy as np

# Read the original and distorted videos
original = skvideo.io.vread("original.mp4")
distorted = skvideo.io.vread("distorted.mp4")

# Compute PSNR between the two videos
psnr_scores = skvideo.measure.psnr(original, distorted)
print(f"Mean PSNR: {np.mean(psnr_scores):.2f} dB")
```

### Example 3: Probe Video Metadata

```python
import skvideo.io

# Get video metadata without reading the full file
metadata = skvideo.io.ffprobe("input.mp4")
video_info = metadata["video"]
print(f"Resolution: {video_info['@width']}x{video_info['@height']}")
print(f"Codec: {video_info['@codec_name']}")
```

## Best Practices

* Use `skvideo.io.FFmpegReader` and `skvideo.io.FFmpegWriter` for large videos to avoid loading the entire file into memory.
* Always specify `outputdict` with an appropriate codec (e.g., `libx264`) when writing videos for broad compatibility.
* Use `skvideo.io.ffprobe()` to inspect video metadata before reading to know the resolution and frame count ahead of time.
* Ensure FFmpeg is installed on your system -- scikit-video depends on it for all encoding and decoding operations.

## Conclusion

scikit-video provides a straightforward, NumPy-centric interface for video I/O and processing in Python. By wrapping FFmpeg, it gives you access to a wide range of codecs and formats while keeping the API simple and Pythonic.

Resources:

* [scikit-video Documentation](http://www.scikit-video.org/stable/)
* [scikit-video on PyPI](https://pypi.org/project/scikit-video/)
* [scikit-video GitHub](https://github.com/scikit-video/scikit-video)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
