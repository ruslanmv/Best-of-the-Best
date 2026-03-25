---
title: "ComfyUI - A Node-Based Interface for Stable Diffusion Image Generation"
date: 2026-02-25T09:00:00+00:00
last_modified_at: 2026-02-25T09:00:00+00:00
topic_kind: "repo"
topic_id: "comfyanonymous/ComfyUI"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - comfyui
  - stable-diffusion
  - image-generation
  - node-based-workflow
  - diffusion-models
  - python
excerpt: "An in-depth look at ComfyUI, a powerful node-based graphical interface for designing and executing Stable Diffusion image generation workflows."
header:
  overlay_image: /assets/images/2026-02-25-repo-comfyui/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-02-25-repo-comfyui/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

[ComfyUI](https://github.com/comfyanonymous/ComfyUI) is a powerful, modular node-based graphical interface for Stable Diffusion and other diffusion-model image generation. Unlike traditional single-button UIs, ComfyUI exposes the entire image generation pipeline as a visual graph of connected nodes, giving users precise control over every step from model loading and prompt conditioning to sampling, upscaling, and post-processing.

## Overview

The `comfyanonymous/ComfyUI` repository provides:

- A **node-based workflow editor** that runs in the browser, backed by a Python server
- Support for **Stable Diffusion 1.x, 2.x, SDXL, SD3, and Flux** models
- **ControlNet, LoRA, IP-Adapter**, and other conditioning techniques as first-class nodes
- A **queue system** for batching multiple generations
- **Workflow saving and sharing** as portable JSON files
- Efficient **VRAM management** with automatic offloading, supporting GPUs with as little as 3 GB of memory
- An extensible **custom node ecosystem** maintained by the community

## Getting Started

### Installation

Clone the repository and install the Python dependencies:

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt
```

For NVIDIA GPUs, ensure you have a compatible version of PyTorch with CUDA support. ComfyUI also supports AMD GPUs via ROCm and Apple Silicon via MPS.

### Downloading Models

Place your Stable Diffusion checkpoint files in the `models/checkpoints/` directory. For example:

```bash
# Download a model (e.g., SDXL)
wget -P models/checkpoints/ https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
```

LoRA weights go in `models/loras/`, VAE files in `models/vae/`, and ControlNet models in `models/controlnet/`.

### Starting the Server

```bash
python main.py
```

By default, ComfyUI launches a web server at `http://127.0.0.1:8188`. Open this URL in your browser to access the node editor.

## Core Concepts

### Node-Based Workflows

Every image generation pipeline in ComfyUI is built by connecting nodes in a visual graph. A basic text-to-image workflow consists of:

1. **Load Checkpoint** - Loads a Stable Diffusion model from disk
2. **CLIP Text Encode** - Converts positive and negative text prompts into conditioning tensors
3. **KSampler** - Runs the diffusion sampling process using a scheduler and sampler algorithm
4. **VAE Decode** - Decodes the latent output into a visible image
5. **Save Image** / **Preview Image** - Writes the result to disk or displays it in the UI

Nodes are connected by dragging wires between compatible input and output ports. This visual approach makes it easy to understand and modify the generation pipeline.

### Workflow JSON Files

ComfyUI workflows can be saved as JSON files and shared with others. Loading a workflow JSON restores the complete node graph, including all parameter settings. You can also drag a ComfyUI-generated PNG image into the editor, as workflow metadata is embedded in the image file by default.

### The KSampler Node

The KSampler is central to image generation. Key parameters include:

- **seed** - Controls reproducibility; the same seed with the same settings produces the same image
- **steps** - Number of denoising steps (typically 20-50)
- **cfg** (Classifier-Free Guidance scale) - Controls how closely the output follows the prompt (typically 5-12)
- **sampler_name** - The sampling algorithm (euler, euler_ancestral, dpmpp_2m, dpmpp_sde, etc.)
- **scheduler** - The noise schedule (normal, karras, exponential, sgm_uniform, etc.)
- **denoise** - The denoising strength (1.0 for full generation, lower values for img2img)

### LoRA and ControlNet

ComfyUI has dedicated nodes for applying LoRA weights and ControlNet conditioning:

- **Load LoRA** takes a model and CLIP input and applies LoRA adjustments with a configurable strength
- **Apply ControlNet** takes a conditioning input and a control image (such as a depth map, edge detection, or pose) to guide generation spatially

## Practical Examples

### Example 1: Basic Text-to-Image Workflow

The default workflow included with ComfyUI demonstrates a standard text-to-image pipeline:

1. Add a **Load Checkpoint** node and select your model (e.g., `sd_xl_base_1.0.safetensors`)
2. Add two **CLIP Text Encode** nodes - one for the positive prompt and one for the negative prompt
3. Connect both to a **KSampler** node, set steps to 30, cfg to 7.5, and choose the `dpmpp_2m` sampler with the `karras` scheduler
4. Connect a **Empty Latent Image** node to the KSampler's latent input, setting the resolution to 1024x1024 for SDXL
5. Connect the KSampler output to a **VAE Decode** node, then to a **Save Image** node

Click **Queue Prompt** to generate the image.

### Example 2: Image-to-Image with ControlNet

To perform guided image-to-image generation:

1. Start with the basic text-to-image workflow above
2. Add a **Load Image** node pointing to your reference image
3. Add a **ControlNet Loader** node and select a ControlNet model (e.g., a depth or canny edge model)
4. Add an **Apply ControlNet** node, connecting the ControlNet model and the loaded reference image
5. Wire the Apply ControlNet output into the KSampler's positive conditioning input

This steers the generated image to follow the spatial structure of your reference image while applying the style described in your text prompt.

### Example 3: Using the API Programmatically

ComfyUI exposes a REST API that accepts workflow JSON. You can submit workflows from Python:

```python
import json
import requests

# Load a saved workflow
with open("workflow.json", "r") as f:
    workflow = json.load(f)

# Submit to the ComfyUI server
response = requests.post(
    "http://127.0.0.1:8188/prompt",
    json={"prompt": workflow}
)
print(response.json())
```

## Best Practices

- **Save your workflows frequently.** Complex node graphs represent significant effort. Export them as JSON files or rely on the embedded metadata in generated images.
- **Use the manager for custom nodes.** The [ComfyUI Manager](https://github.com/ltdrdata/ComfyUI-Manager) simplifies installing and updating community-contributed custom nodes.
- **Match resolution to model training.** SD 1.5 works best at 512x512, SDXL at 1024x1024. Using incorrect resolutions leads to artifacts.
- **Start with fewer steps** (15-20) during experimentation, then increase for final renders.

## Conclusion

ComfyUI has established itself as one of the most flexible tools for AI image generation. Its node-based approach provides transparency and control that single-button interfaces cannot match, while the active community contributes a growing library of custom nodes for new models, techniques, and post-processing steps. The `comfyanonymous/ComfyUI` repository continues to evolve rapidly, adding support for new model architectures and performance improvements.

For more details, visit the [ComfyUI GitHub repository](https://github.com/comfyanonymous/ComfyUI).

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
