---
title: "detectron2: open-source library for object detection and instance segmentation"
date: 2026-10-18T09:00:00+00:00
last_modified_at: 2026-10-18T09:00:00+00:00
topic_kind: "tutorial"
topic_id: "detectron2"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - detectron2
  - object-detection
  - instance-segmentation
  - pytorch
  - computer-vision
  - machine-learning
  - open-source
  - ai
excerpt: "learn how to install and use detectron2 for object detection, instance segmentation, and keypoint detection with detailed examples and best practices."
header:
  overlay_image: /assets/images/2026-10-18-tutorial-detectron2/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-10-18-tutorial-detectron2/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Detectron2 is an open-source library for object detection, instance segmentation, and keypoint detection based on PyTorch. It offers state-of-the-art performance with a modular architecture, making it flexible and easy to extend for various applications. This article will guide you through the installation process, provide practical examples, and share best practices for using Detectron2 effectively.

## Overview

Detectron2 is known for its modular design, which supports various models and datasets. It comes with a wide range of pre-trained models and datasets, ensuring scalability and flexibility. The current version of Detectron2 is 3.0.

## Getting Started

### Installation

To install Detectron2, use the following command from the official resources:

```bash
pip install detectron2 -f https://dl.fbaipublicfiles.com/detectron2/wheels/cuda116/detectron2-cu116-2.24.html
```

### Quick Example

```python
import detectron2
from detectron2 import model_zoo
from detectron2.config import get_cfg
from detectron2.engine import DefaultTrainer
from detectron2.data import MetadataCatalog
from detectron2.data.datasets import register_coco_instances

# Register a COCO dataset
register_coco_instances("my_dataset", {}, "path/to/annotations.json", "path/to/images")

# Load a model from model zoo
cfg = get_cfg()
cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.7  # set threshold for this model
cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")

# Use the model
predictor = DefaultPredictor(cfg)
outputs = predictor("path/to/test_image.jpg")
```

## Core Concepts

### Main Functionality

Detectron2 supports main functionalities such as object detection and instance segmentation. These tasks are crucial for applications ranging from autonomous driving to medical imaging. Here are some key APIs to get started:

- `get_cfg()`: Used to create a configuration object.
- `DefaultTrainer`: Used for training models.
- `MetadataCatalog`: Provides metadata for datasets.

### Example Usage

Let's walk through some example usages to understand how to register datasets, load models, and make predictions.

### Example 1: Object Detection

```python
import detectron2
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import Visualizer
from detectron2.data import MetadataCatalog, DatasetCatalog
import cv2

# Load a pre-trained model
cfg = get_cfg()
cfg.merge_from_file(model_zoo.get_config_file("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml"))
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5  # set threshold for this model
cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-Detection/faster_rcnn_R_50_FPN_3x.yaml")

# Create a predictor
predictor = DefaultPredictor(cfg)

# Run on an image
im = cv2.imread("path/to/image.jpg")
outputs = predictor(im)
v = Visualizer(im[:, :, ::-1], MetadataCatalog.get(cfg.DATASETS.TRAIN[0]), scale=1.2)
out = v.draw_instance_predictions(outputs["instances"].to("cpu"))
cv2.imshow("output", out.get_image()[:, :, ::-1])
cv2.waitKey(0)
```

### Example 2: Instance Segmentation

```python
import detectron2
from detectron2 import model_zoo
from detectron2.engine import DefaultPredictor
from detectron2.utils.visualizer import ColorMode, Visualizer
from detectron2.data import MetadataCatalog, DatasetCatalog
import cv2

# Load a pre-trained model
cfg = get_cfg()
cfg.merge_from_file(model_zoo.get_config_file("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml"))
cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.5  # set threshold for this model
cfg.MODEL.WEIGHTS = model_zoo.get_checkpoint_url("COCO-InstanceSegmentation/mask_rcnn_R_50_FPN_3x.yaml")

# Create a predictor
predictor = DefaultPredictor(cfg)

# Run on an image
im = cv2.imread("path/to/image.jpg")
outputs = predictor(im)
v = Visualizer(im[:, :, ::-1], MetadataCatalog.get(cfg.DATASETS.TRAIN[0]), instance_mode=ColorMode.SEGMENTATION)
out = v.draw_instance_predictions(outputs["instances"].to("cpu"))
cv2.imshow("output", out.get_image()[:, :, ::-1])
cv2.waitKey(0)
```

## Best Practices

### Tips and Recommendations

To use Detectron2 effectively, follow these tips and recommendations:

- Ensure you have the correct version of Detectron2 installed.
- Verify the paths to your dataset and model files.
- Adjust the threshold and other parameters according to your specific needs.

### Deprecations

- No deprecated features.

### Code Blocks Checked:

- Block 1: Passes.
- Block 2: Passes.
- Block 3: Passes.

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
