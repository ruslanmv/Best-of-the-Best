---
title: "MMSegmentation: OpenMMLab's Semantic Segmentation Toolbox"
date: 2026-01-24T09:00:00+00:00
last_modified_at: 2026-01-24T09:00:00+00:00
topic_kind: "package"
topic_id: "mmsegmentation"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - python
  - package
  - pypi
  - semantic-segmentation
  - deep-learning
  - computer-vision
  - pytorch
  - openmmlab
excerpt: "MMSegmentation is OpenMMLab's open-source semantic segmentation toolbox built on PyTorch, supporting 50+ architectures and a unified config-driven workflow for training and inference."
header:
  overlay_image: /assets/images/2026-01-24-package-mmsegmentation/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-01-24-package-mmsegmentation/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

MMSegmentation is an open-source semantic segmentation toolbox from the [OpenMMLab](https://openmmlab.com/) ecosystem. Built on PyTorch and the MMEngine framework, it provides a unified, config-driven workflow for training, evaluating, and deploying semantic segmentation models. It ships with implementations of over 50 segmentation architectures and supports a wide range of benchmark datasets out of the box.

In this guide you will learn how to install MMSegmentation, run inference with a pretrained model, and understand the config system that ties models, datasets, and training schedules together.

## Overview

Key features:

* 50+ segmentation architectures (DeepLabV3, DeepLabV3+, PSPNet, UNet, SegFormer, Mask2Former, and more)
* Config-driven design -- models, datasets, schedules, and runtime settings are all defined in Python config files
* Pretrained model zoo with hundreds of checkpoints on ADE20K, Cityscapes, PASCAL VOC, and other datasets
* Built on MMEngine and MMCV for a consistent training and evaluation pipeline
* Support for distributed training, mixed precision, and TensorRT/ONNX export

Use cases:

* Autonomous driving scene parsing (Cityscapes, BDD100K)
* Indoor scene understanding (ADE20K, ScanNet)
* Medical image segmentation
* Remote sensing and satellite imagery analysis
* Research benchmarking of new segmentation architectures

Current version: **mmsegmentation 1.2.2** (requires mmengine and mmcv >= 2.0)

## Getting Started

MMSegmentation depends on PyTorch, MMEngine, and MMCV. Install them in order:

```
pip install torch torchvision
pip install -U openmim
mim install mmengine mmcv
pip install mmsegmentation
```

Alternatively, install MMSegmentation and its dependencies together using MIM:

```
mim install mmsegmentation
```

Verify the installation:

```python
import mmseg
print(mmseg.__version__)
```

## Core Concepts

### Config System

MMSegmentation uses Python config files to define every aspect of an experiment. A config file typically inherits from base configs and specifies the model architecture, dataset pipeline, training schedule, and runtime options. For example, `pspnet_r50-d8_4xb2-40k_cityscapes-512x1024.py` describes a PSPNet with a ResNet-50 backbone trained on Cityscapes.

### Model Architecture

Models are built from a config dictionary with three main components:

* **backbone** -- the feature extractor (e.g., ResNet, Swin Transformer)
* **decode_head** -- the segmentation head that produces per-pixel predictions (e.g., PSPHead, ASPPHead, SegformerHead)
* **auxiliary_head** (optional) -- an auxiliary loss head for deeper supervision

### Inference API

The high-level inference API consists of two functions from `mmseg.apis`:

* `init_model(config, checkpoint)` -- loads a model from a config file and checkpoint
* `inference_model(model, image)` -- runs inference and returns the segmentation result

## Practical Examples

### Example 1: Running Inference with a Pretrained Model

```python
from mmseg.apis import init_model, inference_model
import mmcv

# Paths to the config file and pretrained checkpoint
config_file = "configs/pspnet/pspnet_r50-d8_4xb2-40k_cityscapes-512x1024.py"
checkpoint_file = "pspnet_r50-d8_512x1024_40k_cityscapes_20200605_003338-2966598c.pth"

# Initialize the model
model = init_model(config_file, checkpoint_file, device="cuda:0")

# Run inference on a single image
result = inference_model(model, "demo/demo.png")

# The result contains predicted semantic labels per pixel
seg_map = result.pred_sem_seg.data.cpu().numpy()
print(f"Segmentation map shape: {seg_map.shape}")
```

### Example 2: Visualizing Segmentation Results

```python
from mmseg.apis import init_model, inference_model
from mmseg.visualization import SegLocalVisualizer
import mmcv

config_file = "configs/pspnet/pspnet_r50-d8_4xb2-40k_cityscapes-512x1024.py"
checkpoint_file = "pspnet_r50-d8_512x1024_40k_cityscapes_20200605_003338-2966598c.pth"

model = init_model(config_file, checkpoint_file, device="cuda:0")
image = mmcv.imread("demo/demo.png")
result = inference_model(model, image)

# Visualize the result
visualizer = SegLocalVisualizer()
visualizer.dataset_meta = model.dataset_meta
visualizer.add_datasample(
    name="result",
    image=image,
    data_sample=result,
    draw_gt=False,
    show=False,
    out_file="result.png",
)
print("Saved visualization to result.png")
```

### Example 3: Listing Available Pretrained Models

You can use MIM to search the model zoo for available checkpoints:

```
mim search mmsegmentation --model "deeplabv3plus"
```

Or programmatically in Python:

```python
from mmseg.utils import register_all_modules
from mmengine import Config

# Register all modules so configs can be loaded
register_all_modules()

# Load a config to inspect the model definition
cfg = Config.fromfile("configs/deeplabv3plus/deeplabv3plus_r101-d8_4xb2-40k_cityscapes-512x1024.py")
print(f"Backbone: {cfg.model.backbone.type}")
print(f"Decode head: {cfg.model.decode_head.type}")
```

### Example 4: Training on a Custom Dataset

To train on your own dataset, create a config that inherits from a base and overrides the dataset paths:

```python
# my_config.py
_base_ = "configs/pspnet/pspnet_r50-d8_4xb2-40k_cityscapes-512x1024.py"

# Override dataset settings
train_dataloader = dict(
    dataset=dict(
        type="CustomDataset",
        data_root="data/my_dataset",
        img_dir="images/train",
        seg_map_dir="annotations/train",
    ),
)

val_dataloader = dict(
    dataset=dict(
        type="CustomDataset",
        data_root="data/my_dataset",
        img_dir="images/val",
        seg_map_dir="annotations/val",
    ),
)
```

Then launch training from the command line:

```
python tools/train.py my_config.py
```

## Best Practices

* Use MIM (`openmim`) to manage dependencies and download pretrained checkpoints. It resolves version compatibility automatically.
* Start from an existing config in the `configs/` directory and customize it rather than writing a config from scratch.
* Use `register_all_modules()` when loading configs or models outside the standard training scripts.
* For custom datasets, ensure your annotation masks use contiguous integer class IDs starting from 0, and define the `classes` and `palette` fields in your dataset config.
* Enable mixed-precision training with `--amp` for faster training on modern GPUs.

## Conclusion

MMSegmentation provides a comprehensive, well-maintained toolkit for semantic segmentation research and production. Its config-driven design, extensive model zoo, and tight integration with the OpenMMLab ecosystem make it straightforward to reproduce published results, benchmark new ideas, and deploy models to production.

Resources:

* [MMSegmentation Documentation](https://mmsegmentation.readthedocs.io/)
* [MMSegmentation GitHub](https://github.com/open-mmlab/mmsegmentation)
* [MMSegmentation Model Zoo](https://mmsegmentation.readthedocs.io/en/latest/model_zoo.html)
* [OpenMMLab](https://openmmlab.com/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
