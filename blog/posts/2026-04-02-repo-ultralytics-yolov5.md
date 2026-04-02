---
title: "ultralytics/Yolov5 - Real-Time Object Detection Guide"
date: 2026-04-02T09:00:00+00:00
last_modified_at: 2026-04-02T09:00:00+00:00
topic_kind: "repo"
topic_id: "ultralytics/yolov5"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - YOLOv5
  - object detection
  - real-time processing
  - installation
  - advanced configurations
excerpt: "Learn how to set up and use YOLOv5 for real-time object detection, including installation, basic usage, and advanced configurations. Explore practical applications in security, autonomous vehicles, and retail analytics."
header:
  overlay_image: /assets/images/2026-04-02-repo-ultralytics-yolov5/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-04-02-repo-ultralytics-yolov5/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Guide to Implementing Real-Time Object Detection with YOLOv5

### Introduction to YOLOv5

YOLO (You Only Look Once) is a popular object detection model that can run in real-time. This guide will walk you through the process of setting up and using YOLOv5 for real-time object detection, including installation, basic usage, and advanced configurations.

### Objectives
- Understand the functionalities of YOLOv5.
- Learn how to install YOLOv5 and set it up in your environment.
- Explore practical applications of YOLOv5 through various code examples.
- Provide resources for further learning and contributing to the project.

### Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Basic Usage](#basic-usage)
4. [Advanced Configurations](#advanced-configurations)
5. [Practical Applications](#practical-applications)
6. [Conclusion](#conclusion)

---

### 1. Introduction

YOLOv5 is a state-of-the-art object detection model that is optimized for speed and accuracy. It has been widely used in various applications, from security to autonomous driving.

This guide will cover the following topics:
- Setting up YOLOv5.
- Running basic image and video processing with YOLOv5.
- Advanced configurations including custom training and deployment.

---

### 2. Installation

Before you can use YOLOv5, you need to install it in your environment. The installation process is straightforward and involves setting up the required dependencies. Here’s how:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/ultralytics/yolov5.git
   ```

2. **Install Dependencies:**
   Navigate to the cloned repository and install the necessary Python packages.
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Installation:**
   Run a simple test to ensure everything is set up correctly.
   ```python
   python detect.py --source 0  # Open webcam for testing
   ```

---

### 3. Basic Usage

Let’s start by using YOLOv5 to perform basic object detection on images and videos.

#### Image Detection

1. **Load a Pre-trained Model:**
   You can use the pre-trained model provided in the repository.
   ```python
   from yolov5.models.common import DetectMultiBackend
   from yolov5.utils.general import check_img_size, non_max_suppression, scale_coords
   from yolov5.utils.plots import Annotator, colors

   # Load a pre-trained model and set evaluation mode
   model = DetectMultiBackend('yolov5s.pt', device='0', dnn=False)
   model.eval()

   # Initialize the dataset loader (can be images or videos)
   images = LoadImages('data/images/zidane.jpg', img_size=640, auto=True)

   # Process each image in the dataset
   for path, im, im0s, vid_cap, s in images:
       # Run inference on the current image
       pred = model(im)  # forward pass
       pred = non_max_suppression(pred, conf_thres=0.25, iou_thres=0.45)  # apply NMS

       # Process detections for each image
       for i, det in enumerate(pred):  # detections per image
           annotator = Annotator(im0s)
           
           # Scale bounding boxes and labels
           det[:, :4] = scale_coords(im.shape[2:], det[:, :4], im0s.shape).round()

           # Draw bounding boxes and labels on the image
           for *xyxy, conf, cls in reversed(det):
               c = int(cls)
               label = f'{model.names[c]} {conf:.2f}'
               annotator.box_label(xyxy, label, color=colors(c))

       # Save or display processed images
       im0s = annotator.result()
       cv2.imwrite('output.jpg', im0s)
   ```

#### Video Detection

1. **Load Videos and Perform Real-Time Object Detection:**
   ```python
   import torch
   from yolov5.models.common import DetectMultiBackend
   from yolov5.utils.datasets import LoadImages, LoadStreams
   from yolov5.utils.general import (check_img_size, non_max_suppression, scale_coords)
   from yolov5.utils.plots import Annotator, colors

   # Load a pre-trained model and set evaluation mode
   model = DetectMultiBackend('yolov5s.pt', device='0', dnn=False)
   model.eval()

   # Initialize the dataset loader (can be images or videos)
   images = LoadImages('data/images/bus.jpg', img_size=640, auto=True)

   # Process each image in the dataset
   for path, im, im0s, vid_cap, s in images:
       # Run inference on the current image
       pred = model(im)  # forward pass
       pred = non_max_suppression(pred, conf_thres=0.25, iou_thres=0.45)  # apply NMS

       # Process detections for each image
       for i, det in enumerate(pred):  # detections per image
           annotator = Annotator(im0s)
           
           # Scale bounding boxes and labels
           det[:, :4] = scale_coords(im.shape[2:], det[:, :4], im0s.shape).round()

           # Draw bounding boxes and labels on the image
           for *xyxy, conf, cls in reversed(det):
               c = int(cls)
               label = f'{model.names[c]} {conf:.2f}'
               annotator.box_label(xyxy, label, color=colors(c))

       # Save or display processed images
       im0s = annotator.result()
       cv2.imwrite('output.jpg', im0s)

   # Optional: If using video streaming
   for path, im, im0s, vid_cap, s in images:
       ...
   ```

---

### 4. Advanced Configurations

YOLOv5 offers a wide range of advanced features that can be configured to suit specific needs. Some key configurations include:

- **Custom Training:** Train YOLOv5 on custom datasets.
- **Deployment:** Deploy the model for real-time applications using different frameworks like TensorFlow or ONNX.

#### Custom Training
1. **Prepare Your Dataset:**
   - Collect and annotate images with bounding boxes.
   - Organize your dataset into a structured format (YOLOv5 supports COCO, VOC, etc.).

2. **Train YOLOv5:**
   ```bash
   python train.py --img 640 --batch 16 --epochs 30 --data custom_dataset.yaml --weights yolov5s.pt
   ```

#### Deployment

- **Export Model for TensorFlow:**
  ```python
  from yolov5.export.torchscript import export_model

  model = DetectMultiBackend('yolov5s.pt', device='cpu')
  export_model(model, imgsz=(640, 640), device='cpu', half=False)
  ```

- **Deploy to Edge Devices:**
  Use ONNX Runtime for efficient deployment on edge devices.
  ```python
  import torch.onnx

  model = DetectMultiBackend('yolov5s.pt', device='cpu')
  model.export(format='onnx')
  ```

---

### 5. Practical Applications

YOLOv5 can be applied in various real-world scenarios, such as:
- **Security Systems:** Real-time monitoring and alerting based on detected objects.
- **Autonomous Vehicles:** Object detection for navigation and collision avoidance.
- **Retail Analytics:** Counting people in stores or tracking inventory.

---

### 6. Conclusion

This guide provided an in-depth look at YOLOv5's functionalities, installation process, and practical applications. By following the steps outlined here, readers are now equipped with the knowledge needed to implement real-time object detection in their projects. For further details, explore the official documentation and contribute to the community by sharing your findings and improvements.

### Next Steps

- Dive deeper into advanced configurations and custom training using YOLOv5.
- Contribute to the project's GitHub repository to support ongoing development and enhance its capabilities.
## Resources:
- [YOLOv5 - Home](https://github.com/ultralytics/yolov5)
- [YoloV5 Documentation - Getting Started](https://docs.ultralytics.com/modes/webapp/)
- [PyImageSearch: YOLOv5 Object Detection with PyTorch](https://www.pyimagesearch.com/2021/09/27/yolov5-object-detection-with-pytorch/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
