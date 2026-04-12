---
title: "tencentarc/gfpgan: state-of-the-art-face-restoration-model"
date: 2026-04-12T09:00:00+00:00
last_modified_at: 2026-04-12T09:00:00+00:00
topic_kind: "repo"
topic_id: "TencentARC/GFPGAN"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - gfpgan
  - face-restoration
  - perceptual-gans
  - image-enhancement
excerpt: "Discover how to use GFPGAN for high-resolution face restoration, enhancing photos and videos. Learn setup, usage, and best practices directly from the source."
header:
  overlay_image: /assets/images/2026-04-12-repo-tencentarc-gfpgan/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-04-12-repo-tencentarc-gfpgan/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

GFPGAN, an abbreviation for Face Restoration using Perceptual GANs, is a state-of-the-art face restoration model developed by Tencent. It addresses the challenge of face degradation in images and videos, enhancing facial features to restore natural appearances. This blog will guide you through setting up, using, and optimizing GFPGAN for your projects.

## Overview

GFPGAN offers several key features:
- **High-resolution face restoration**: The model ensures that restored faces maintain high resolution.
- **Realistic and perceptually lossless results**: Restored images and videos look natural without any artifacts or distortions.
- **Compatibility with various input formats**: GFPGAN supports both image and video inputs, making it versatile for different use cases.

Current version: `3.0.0`

## Getting Started

To get started with GFPGAN, you need to install the library using pip:
```bash
pip install git+https://github.com/TencentARC/GFPGAN.git
```

```python
from GFPGAN import GFPGANer

# Initialize the model with a specified model version
restorer = GFPGANer(model='GFPGANCleanv1-NoCE-C2')

# Enhance an image by specifying the input path and desired upsampling factor
output = restorer.enhance(image_path='input.jpg', upscale=2)
```

## Core Concepts

### Main Functionality

GFPGAN performs face restoration through two main steps:
- **Face detection and alignment**: The model detects faces in the input images or videos and aligns them to ensure accurate restoration.
- **Perceptual loss minimization during restoration**: By minimizing perceptual losses, GFPGAN ensures that the restored faces look natural and maintain high visual quality.

### API Overview

Here is an example of how to use the `GFPGANer` class:
```python
from GFPGAN import GFPGANer

# Initialize the model with a specified model version
restorer = GFPGANer(model='GFPGANCleanv1-NoCE-C2')

# Enhance an image by specifying the input path and desired upsampling factor
output = restorer.enhance(image_path='input.jpg', upscale=2)
```

### Example Usage

```python
from GFPGAN import GFPGANer

# Initialize the model with a specified model version
restorer = GFPGANer(model='GFPGANCleanv1-NoCE-C2')

# Enhance an image by specifying the input path and desired upsampling factor
output = restorer.enhance(image_path='input.jpg', upscale=2)
```

## Practical Examples

### Example 1: Face Restoration for Photo Editing

```python
from GFPGAN import GFPGANer

# Initialize the model with a specified model version
restorer = GFPGANer(model='GFPGANCleanv1-NoCE-C2')

# Enhance an image by specifying the input path and desired upsampling factor
output = restorer.enhance(image_path='input.jpg', upscale=2)
```

### Example 2: Video Enhancement for Face Restoration

```python
from GFPGAN import GFPGANer

# Initialize the model with a specified model version
restorer = GFPGANer(model='GFPGANCleanv1-NoCE-C2')

# Enhance a video by specifying the input and output paths, and desired upsampling factor
output_video_path = 'enhanced_output.mp4'
restorer.enhance(video_path='input.mp4', output_video_path=output_video_path, upscale=2)
```

## Best Practices

### Tips and Recommendations

- **Always check for the latest updates and patches** to ensure you are using the most recent improvements.
- **Use high-resolution input images** to maximize restoration quality.

### Common Pitfalls

- **Over-optimizing settings**: While customization can enhance results, overly aggressive settings may introduce artifacts in the output. Balancing between detail and clarity is key.

## Conclusion

GFPGAN is a robust tool for face restoration, offering high-quality results with minimal effort. It supports various input formats and provides versatile functionality for both images and videos. Regular updates and active maintenance by the community ensure compatibility with modern Python environments and ongoing support.

For more detailed instructions on how to use GFPGAN effectively, refer to the official documentation:
- [Getting Started with GFPGAN](https://github.com/TencentARC/GFPGAN#how-to-use-gfpgan)
- [Detailed Installation and Usage Guide](https://github.com/TencentARC/GFPGAN/wiki/How-to-Use-GFPGAN)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
