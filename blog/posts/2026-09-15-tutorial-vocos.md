---
title: "Vocos - Python Library for Audio Reconstruction"
date: 2026-09-15T09:00:00+00:00
last_modified_at: 2026-09-15T09:00:00+00:00
topic_kind: "tutorial"
topic_id: "vocos"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - vocos
  - python
  - audio-reconstruction
  - speech-synthesis
  - noise-reduction
  - encodec
excerpt: "Learn how to use Vocos, a Python library for generating high-quality audio from mel-spectrograms or EnCodec tokens. Explore speech synthesis, noise reduction, and more with this powerful tool."
header:
  overlay_image: /assets/images/2026-09-15-tutorial-vocos/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-09-15-tutorial-vocos/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

### What is Vocos?
Vocos is a Python library designed for audio reconstruction from mel-spectrograms or EnCodec tokens, enabling users to generate high-quality audio from spectral representations. It is particularly useful for researchers, developers, and audio engineers who need to work with audio data.

### Why it matters
Vocos is crucial for applications such as speech synthesis, noise reduction, and audio enhancement, providing a powerful toolset for manipulating and reconstructing audio signals. Its robustness and compatibility with Python 3.7 or later ensure seamless integration into existing projects and workflows.

### What readers will learn
Readers will learn how to install and use Vocos, understand its key features, and explore practical use cases through detailed examples.

## Overview

### Key Features
- High-quality audio reconstruction from mel-spectrograms and EnCodec tokens.
- Pre-trained models and training functionalities for custom datasets.
- Compatibility with Python 3.7 or later.

### Use Cases
- Speech synthesis.
- Noise reduction.
- Audio enhancement.

### Current Version: 1.2.3
The current version 1.2.3 of Vocos includes improvements in accuracy and robustness, as well as additional features for better user experience. Note that version 1.1.0 is deprecated and should be avoided.

## Getting Started

### Installation
To install Vocos, follow the instructions in the README. Ensure compatibility with Python 3.7 or later.

```python
pip install vocos
```

### Quick Example (Complete Code)

```python
import vocos

# Load the pre-trained model
model = vocos.load_pretrained_model()

# Define input mel-spectrogram or EnCodec tokens
input_data = ...

# Generate audio
audio = model.reconstruct(input_data)

# Save the generated audio
audio.save("output_audio.wav")
```

## Core Concepts

### Main Functionality
Vocos offers functionalities for audio reconstruction, including the ability to load pre-trained models, reconstruct audio from mel-spectrograms or EnCodec tokens, and generate high-quality audio outputs.

### API Overview
The API provides methods for loading models, reconstructing audio, and handling various audio data types. Refer to the API documentation for detailed method descriptions and usage examples.

### Example Usage
```python
import vocos

# Load a pre-trained model
model = vocos.load_pretrained_model()

# Define input mel-spectrogram
mel_spectrogram = ...

# Reconstruct audio from the mel-spectrogram
audio = model.reconstruct(mel_spectrogram)

# Save the generated audio
audio.save("output_audio.wav")
```

## Practical Examples

### Example 1: Speech Synthesis
```python
import vocos

# Load a pre-trained model for speech synthesis
speech_synthesis_model = vocos.load_pretrained_model("speech_synthesis")

# Generate mel-spectrogram from text
from vocos.text_to_spectrogram import text_to_spectrogram
mel_spectrogram = text_to_spectrogram("Hello, how are you?")

# Reconstruct audio from the mel-spectrogram
audio = speech_synthesis_model.reconstruct(mel_spectrogram)

# Save the generated audio
audio.save("speech_synthesis_output.wav")
```

### Example 2: Noise Reduction
```python
import vocos

# Load a pre-trained model for noise reduction
noise_reduction_model = vocos.load_pretrained_model("noise_reduction")

# Define input audio with noise
noisy_audio = ...

# Generate mel-spectrogram from the noisy audio
mel_spectrogram = noisy_audio.to_spectrogram()

# Reconstruct clean audio from the mel-spectrogram
clean_audio = noise_reduction_model.reconstruct(mel_spectrogram)

# Save the clean audio
clean_audio.save("noise_reduction_output.wav")
```

## Best Practices

### Tips and Recommendations
- Ensure compatibility with Python 3.7 or later for smooth installation and usage.
- Utilize the provided code examples as a starting point and customize them for your specific needs.
- Explore the pre-trained models and training functionalities for custom datasets.

### Common Pitfalls
- Avoid using deprecated version 1.1.0, as it is no longer supported.
- Pay attention to input data formats and ensure they match the expected types for the chosen model.

## Conclusion

In summary, Vocos is a powerful tool for audio reconstruction, offering pre-trained models and training functionalities. By following the installation instructions and exploring the provided examples, readers can effectively utilize Vocos for various audio manipulation tasks.

## Next Steps

- Contribute additional examples to the README to enhance user-friendliness and community engagement.
- Explore the pre-trained models and training functionalities available in the package for custom datasets.

## Resources
- [Package Health Report](https://example.com/package-health-report)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
