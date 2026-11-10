---
title: "sahi: simplifying object detection and instance segmentation post-processing"
date: 2026-11-10T09:00:00+00:00
last_modified_at: 2026-11-10T09:00:00+00:00
topic_kind: "tutorial"
topic_id: "sahi"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - sahi
  - object-detection
  - instance-segmentation
  - post-processing
  - python-library
  - api
  - customization
  - model-integration
excerpt: "SAHI is a Python library that streamlines post-processing for object detection and instance segmentation models, offering a user-friendly API and customizable features for developers."
header:
  overlay_image: /assets/images/2026-11-10-tutorial-sahi/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-11-10-tutorial-sahi/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

SAHI is a Python library designed for post-processing the outputs of object detection and instance segmentation models. It simplifies the integration and usage of these models in real-world applications by providing a user-friendly API and various post-processing techniques. This article will introduce SAHI, its key features, and practical examples to help you effectively use the library in your projects.

## Overview

SAHI supports various post-processing techniques, works with popular models, offers a simple and customizable API, and includes evaluation utilities. It is ideal for developers working with object detection and instance segmentation models, providing tools to handle model outputs efficiently. The current version of SAHI is 0.9.1, and it requires Python 3.7 or higher.

## Getting Started

### Installation

To install SAHI, use the following pip command:

```bash
pip install sahi
```

### Quick Example

```python
from sahi import ObjectDetectionPostProcessor
from sahi.predict import get_sliced_prediction

# Load model and image
model = load_your_model()
image = load_your_image()

# Create post-processor
post_processor = ObjectDetectionPostProcessor(
    score_threshold=0.5,
    nms_threshold=0.6,
    output_dir="/path/to/output",
    mode="union",
)

# Perform post-processing
predictions = get_sliced_prediction(image, model, postprocessor=post_processor)

# Save predictions
predictions.save()
```

## Core Concepts

### Main Functionality

SAHI provides tools for post-processing, including score thresholds, non-maximum suppression (NMS), and output directory management. The main functionality can be customized to fit specific needs, ensuring accurate and efficient post-processing.

### API Overview

The API is straightforward, allowing users to customize post-processing steps according to their specific needs. Here is an example of how to define and apply a post-processor:

```python
from sahi import ObjectDetectionPostProcessor

# Define post-processor
post_processor = ObjectDetectionPostProcessor(
    score_threshold=0.7,
    nms_threshold=0.3,
    output_dir="/path/to/output",
    mode="fast_nms",
)

# Apply post-processing
predictions = post_processor.post_process(predictions)

# Print predictions
for pred in predictions:
    print(pred)
```

## Practical Examples

### Example 1: Custom Score Threshold

This example demonstrates how to use a custom score threshold to filter predictions:

```python
from sahi import ObjectDetectionPostProcessor

# Define post-processor with custom score threshold
post_processor = ObjectDetectionPostProcessor(
    score_threshold=0.9,
    nms_threshold=0.4,
    output_dir="/path/to/output",
    mode="fast_nms",
)

# Apply post-processing
predictions = post_processor.post_process(predictions)

# Print predictions
for pred in predictions:
    print(pred)
```

### Example 2: Union Mode

This example shows how to use the union mode for post-processing:

```python
from sahi import ObjectDetectionPostProcessor

# Define post-processor with union mode
post_processor = ObjectDetectionPostProcessor(
    score_threshold=0.6,
    nms_threshold=0.7,
    output_dir="/path/to/output",
    mode="union",
)

# Apply post-processing
predictions = post_processor.post_process(predictions)

# Print predictions
for pred in predictions:
    print(pred)
```

## Best Practices

### Tips and Recommendations

To use SAHI effectively, it is recommended to:
- Use SAHI's built-in utilities for evaluation and customization.
- Ensure accurate and efficient post-processing by avoiding overly aggressive score thresholds and proper output directory management.

### Common Pitfalls

Avoid setting overly aggressive score thresholds, which can lead to false negatives. Proper output directory management is crucial to avoid overwriting or misplacing predictions.

## Conclusion

SAHI simplifies object detection and instance segmentation post-processing, offering a flexible and easy-to-use API. It is actively maintained, with recent updates and a good commit history. The official documentation and GitHub repository provide comprehensive information, and there are additional blog posts that offer real-world examples and usage tips. Explore these resources to enhance your understanding and use of SAHI in your projects.

- [Official Documentation](https://sahipkg.readthedocs.io/en/latest/index.html)
- [GitHub Repository](https://github.com/obss/sahi)
- [Blog Post](https://towardsdev.com/sahi-post-processing-library-for-object-detection-and-instance-segmentation-in-python-537d3b9e11d5)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
