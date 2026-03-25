---
title: "MMDetection: OpenMMLab's Object Detection Toolbox"
date: 2026-01-11T09:00:00+00:00
last_modified_at: 2026-01-11T09:00:00+00:00
topic_kind: "package"
topic_id: "mmdet"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - object-detection
  - computer-vision
  - deep-learning
  - instance-segmentation
  - openmmlab
excerpt: "MMDetection is OpenMMLab's comprehensive object detection toolbox built on PyTorch, supporting hundreds of detection and segmentation models with a modular, config-driven architecture."
header:
  overlay_image: /assets/images/2026-01-11-package-mmdet/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-01-11-package-mmdet/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

MMDetection is an open-source object detection toolbox developed by [OpenMMLab](https://openmmlab.com/), built on top of PyTorch and the MMEngine framework. It provides a rich collection of detection and instance segmentation algorithms, including Faster R-CNN, YOLO, DETR, Mask R-CNN, and many more. MMDetection uses a config-driven approach where models, datasets, and training pipelines are specified through Python configuration files rather than hardcoded parameters.

MMDetection is widely used in both academic research and production systems. Its modular design allows researchers to swap components such as backbones, necks, and detection heads with minimal code changes, making it an excellent platform for experimenting with new architectures.

In this guide, you will learn how to install MMDetection, run inference with pretrained models, and understand the config-based workflow.

## Overview

Key features of MMDetection:

- **Extensive model zoo**: Hundreds of pretrained models for object detection, instance segmentation, and panoptic segmentation
- **Config-driven design**: All experiment settings live in Python config files that are easy to read, modify, and version control
- **Modular architecture**: Backbones, necks, heads, and losses are interchangeable components
- **Training and evaluation tools**: Built-in support for distributed training, learning rate scheduling, logging, and evaluation metrics
- **Strong ecosystem**: Part of the OpenMMLab family alongside MMSegmentation, MMPose, and other toolboxes

Use cases:

- Object detection in images and video
- Instance and panoptic segmentation
- Benchmarking new detection architectures
- Transfer learning for domain-specific detection tasks

## Getting Started

Install MMDetection and its dependencies:

```bash
pip install -U openmim
mim install mmengine
mim install mmcv
mim install mmdet
```

Download a pretrained model checkpoint and run inference:

```python
from mmdet.apis import init_detector, inference_detector

# Specify the config file and checkpoint
config_file = 'rtmdet_tiny_8xb32-300e_coco.py'
checkpoint_file = 'rtmdet_tiny_8xb32-300e_coco_20220902_112414-78e30dcc.pth'

# Initialize the detector
model = init_detector(config_file, checkpoint_file, device='cuda:0')

# Run inference on an image
result = inference_detector(model, 'demo/demo.jpg')

# The result contains predicted bounding boxes, labels, and scores
print(result.pred_instances.bboxes)
print(result.pred_instances.labels)
print(result.pred_instances.scores)
```

## Core Concepts

### Config Files

MMDetection uses Python config files to define every aspect of an experiment. A typical config inherits from base configs and overrides specific fields:

```python
# my_faster_rcnn_config.py
_base_ = [
    '../_base_/models/faster-rcnn_r50_fpn.py',
    '../_base_/datasets/coco_detection.py',
    '../_base_/schedules/schedule_1x.py',
    '../_base_/default_runtime.py'
]

# Override training settings
train_cfg = dict(max_epochs=24)
optim_wrapper = dict(optimizer=dict(lr=0.01))
```

### The `init_detector` and `inference_detector` APIs

These are the primary functions for loading a model and running predictions:

```python
from mmdet.apis import init_detector, inference_detector

# init_detector loads the model architecture from the config
# and the trained weights from the checkpoint
model = init_detector(
    config='configs/faster_rcnn/faster-rcnn_r50_fpn_1x_coco.py',
    checkpoint='checkpoints/faster_rcnn_r50_fpn_1x_coco.pth',
    device='cuda:0'  # Use 'cpu' if no GPU is available
)

# inference_detector accepts a single image path or a list of paths
result = inference_detector(model, 'test_image.jpg')
```

### Understanding Detection Results

In MMDetection 3.x, results are returned as `DetDataSample` objects:

```python
result = inference_detector(model, 'test_image.jpg')

# Access predictions
pred = result.pred_instances
bboxes = pred.bboxes    # Tensor of shape (N, 4) in xyxy format
scores = pred.scores    # Tensor of shape (N,)
labels = pred.labels    # Tensor of shape (N,) with class indices

# Filter by confidence threshold
mask = scores > 0.5
filtered_bboxes = bboxes[mask]
filtered_labels = labels[mask]
print(f"Found {len(filtered_bboxes)} objects with confidence > 0.5")
```

## Practical Examples

### Example 1: Inference with a Pretrained RTMDet Model

```python
from mmdet.apis import init_detector, inference_detector
from mmdet.utils import register_all_modules

# Register all modules to ensure model components are available
register_all_modules()

config_file = 'configs/rtmdet/rtmdet_l_8xb32-300e_coco.py'
checkpoint_file = 'checkpoints/rtmdet_l_8xb32-300e_coco.pth'

model = init_detector(config_file, checkpoint_file, device='cuda:0')
result = inference_detector(model, 'street_scene.jpg')

# Print detected objects
pred = result.pred_instances
for bbox, label, score in zip(pred.bboxes, pred.labels, pred.scores):
    if score > 0.3:
        x1, y1, x2, y2 = bbox.tolist()
        print(f"Class {label.item()}: score={score.item():.3f}, "
              f"bbox=({x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f})")
```

### Example 2: Training a Detector on a Custom Dataset

Use the MMDetection CLI tools to launch training:

```bash
# Train with a single GPU
python tools/train.py configs/faster_rcnn/faster-rcnn_r50_fpn_1x_coco.py

# Train with multiple GPUs using distributed training
bash tools/dist_train.sh configs/faster_rcnn/faster-rcnn_r50_fpn_1x_coco.py 4
```

To train on a custom COCO-format dataset, create a config that overrides the data paths:

```python
# custom_dataset_config.py
_base_ = 'configs/faster_rcnn/faster-rcnn_r50_fpn_1x_coco.py'

data_root = 'data/my_dataset/'

train_dataloader = dict(
    dataset=dict(
        ann_file='annotations/train.json',
        data_prefix=dict(img='train/'),
        data_root=data_root,
    )
)

val_dataloader = dict(
    dataset=dict(
        ann_file='annotations/val.json',
        data_prefix=dict(img='val/'),
        data_root=data_root,
    )
)

# Adjust number of classes for your dataset
model = dict(
    roi_head=dict(
        bbox_head=dict(num_classes=5)
    )
)
```

## Best Practices

- **Use `mim` for installation**: The `openmim` tool manages MMDetection and its dependencies (mmcv, mmengine) to ensure compatible versions.
- **Start with pretrained models**: Fine-tune from COCO-pretrained checkpoints rather than training from scratch, especially for small datasets.
- **Leverage config inheritance**: Build your custom configs by inheriting from base configs and overriding only what you need, rather than writing configs from scratch.
- **Use the model zoo**: Check the [MMDetection model zoo](https://mmdetection.readthedocs.io/en/latest/model_zoo.html) for pretrained checkpoints and their performance metrics before choosing an architecture.
- **Register modules**: Call `register_all_modules()` when using MMDetection in scripts outside the standard tools to ensure all components are properly registered.

Common pitfalls:

- Version mismatches between mmcv, mmengine, and mmdet cause import errors. Always use `mim install` to manage versions.
- The `mmcv.MMDataProcessor` class does not exist. Use `init_detector` and `inference_detector` from `mmdet.apis`.
- Config paths are relative to the MMDetection repository root. When working from a different directory, use absolute paths.

## Conclusion

MMDetection provides a mature, well-documented platform for object detection research and deployment. Its config-driven architecture and extensive model zoo make it straightforward to experiment with state-of-the-art detection methods, fine-tune models on custom datasets, and benchmark new approaches against established baselines.

Resources:
- [GitHub - open-mmlab/mmdetection](https://github.com/open-mmlab/mmdetection)
- [MMDetection Documentation](https://mmdetection.readthedocs.io/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
