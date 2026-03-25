---
title: "Whisper - OpenAI's Automatic Speech Recognition Model"
date: 2026-02-26T09:00:00+00:00
last_modified_at: 2026-02-26T09:00:00+00:00
topic_kind: "repo"
topic_id: "openai/whisper"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - whisper
  - speech-recognition
  - transcription
  - openai
  - audio
  - python
excerpt: "An in-depth look at OpenAI's Whisper, a general-purpose speech recognition model that delivers robust transcription and translation across dozens of languages."
header:
  overlay_image: /assets/images/2026-02-26-repo-whisper/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-02-26-repo-whisper/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

[Whisper](https://github.com/openai/whisper) is OpenAI's general-purpose speech recognition model, trained on 680,000 hours of multilingual and multitask supervised data collected from the web. It performs automatic speech recognition (ASR), speech translation, spoken language identification, and voice activity detection. Whisper approaches human-level robustness and accuracy on English speech recognition and supports transcription in over 90 languages.

## Overview

The `openai/whisper` repository provides:

- A family of **pre-trained models** in multiple sizes: tiny, base, small, medium, large, and turbo
- A **Python API** for loading models and transcribing audio files
- A **command-line tool** for quick transcription from the terminal
- Support for **translation** from any supported language to English
- **Word-level timestamps** for precise alignment of transcription to audio
- Built-in **voice activity detection** to skip silent regions

The models range from 39 million parameters (tiny) to 1.55 billion parameters (large-v3), offering a trade-off between speed and accuracy.

## Getting Started

### Installation

Install Whisper from PyPI:

```bash
pip install openai-whisper
```

Whisper requires `ffmpeg` to be installed on your system for audio file processing:

```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### Quick Start with the CLI

Transcribe an audio file from the command line:

```bash
whisper audio.mp3 --model base
```

Translate non-English speech to English:

```bash
whisper japanese_audio.mp3 --model medium --task translate
```

Specify the output format:

```bash
whisper audio.mp3 --model small --output_format srt
```

Supported output formats include `txt`, `vtt`, `srt`, `tsv`, and `json`.

## Core Concepts

### Loading a Model and Transcribing

The Python API centers on two functions: `whisper.load_model()` to load a pre-trained model, and `model.transcribe()` to process an audio file:

```python
import whisper

model = whisper.load_model("base")
result = model.transcribe("audio.mp3")
print(result["text"])
```

The `result` dictionary contains the full transcription text along with segment-level details including timestamps and per-segment confidence scores.

### Available Models

| Model   | Parameters | English-only | Multilingual | Relative Speed |
|---------|-----------|-------------|-------------|----------------|
| tiny    | 39 M      | tiny.en     | tiny        | ~10x           |
| base    | 74 M      | base.en     | base        | ~7x            |
| small   | 244 M     | small.en    | small       | ~4x            |
| medium  | 769 M     | medium.en   | medium      | ~2x            |
| large   | 1550 M    | N/A         | large-v3    | 1x             |
| turbo   | 809 M     | N/A         | turbo       | ~8x            |

English-only models (e.g., `base.en`) tend to perform better on English content, while multilingual models handle a broader range of languages.

### Transcription Options

The `transcribe()` method accepts several important parameters:

```python
import whisper

model = whisper.load_model("medium")

result = model.transcribe(
    "interview.mp3",
    language="en",           # Specify language (auto-detected if omitted)
    task="transcribe",       # "transcribe" or "translate" (to English)
    fp16=True,               # Use half-precision for faster inference on GPU
    word_timestamps=True,    # Enable word-level timing
    verbose=True,            # Print progress to stdout
)
```

### Working with Segments

The transcription result includes a list of segments, each with start and end timestamps:

```python
import whisper

model = whisper.load_model("small")
result = model.transcribe("lecture.mp3")

for segment in result["segments"]:
    start = segment["start"]
    end = segment["end"]
    text = segment["text"]
    print(f"[{start:.2f}s -> {end:.2f}s] {text}")
```

## Practical Examples

### Example 1: Batch Transcription of Multiple Files

```python
import whisper
from pathlib import Path

model = whisper.load_model("base")

audio_dir = Path("recordings/")
for audio_file in audio_dir.glob("*.mp3"):
    result = model.transcribe(str(audio_file))
    output_path = audio_file.with_suffix(".txt")
    output_path.write_text(result["text"])
    print(f"Transcribed {audio_file.name} -> {output_path.name}")
```

### Example 2: Generating SRT Subtitles

```python
import whisper
from whisper.utils import get_writer

model = whisper.load_model("medium")
result = model.transcribe("video.mp4", word_timestamps=True)

# Write SRT subtitle file
writer = get_writer("srt", "output/")
writer(result, "video.mp4")
```

### Example 3: Language Detection

Whisper can detect the spoken language in an audio clip using its first 30 seconds:

```python
import whisper

model = whisper.load_model("base")

# Load and pad/trim audio to 30 seconds
audio = whisper.load_audio("speech.mp3")
audio = whisper.pad_or_trim(audio)

# Generate log-Mel spectrogram
mel = whisper.log_mel_spectrogram(audio).to(model.device)

# Detect language
_, probs = model.detect_language(mel)
detected_lang = max(probs, key=probs.get)
print(f"Detected language: {detected_lang}")
```

## Best Practices

- **Choose the right model size for your use case.** The `base` and `small` models are fast enough for real-time applications, while `medium` and `large-v3` are better suited for high-accuracy offline transcription.
- **Use English-only models for English content.** Models like `base.en` and `small.en` deliver better accuracy on English audio compared to their multilingual counterparts.
- **Enable `fp16` on GPU.** Half-precision inference significantly speeds up transcription without a meaningful loss in accuracy.
- **Pre-process noisy audio** with noise reduction tools before feeding it to Whisper for better results on low-quality recordings.

## Conclusion

OpenAI's Whisper is a remarkably capable speech recognition system that works reliably across a wide range of languages, accents, and audio conditions. The `openai/whisper` repository provides a straightforward Python API and CLI that make it accessible for everything from quick one-off transcriptions to large-scale audio processing pipelines.

For more details, visit the [Whisper GitHub repository](https://github.com/openai/whisper).

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
