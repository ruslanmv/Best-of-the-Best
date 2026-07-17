---
title: "image-classification-tensorflow"
date: 2026-07-17T09:00:00+00:00
last_modified_at: 2026-07-17T09:00:00+00:00
topic_kind: "tutorial"
topic_id: "image-classification"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - image-classification
  - tensorflow
  - machine-learning
  - mnist-dataset
excerpt: "Learn how to implement image classification with TensorFlow 3.x. Explore key concepts, practical examples, and best practices for building robust models."
header:
  overlay_image: /assets/images/2026-07-17-tutorial-image-classification/header-data-science.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-07-17-tutorial-image-classification/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Image classification is a machine learning technique used to identify objects, people, places, etc., within digital images and videos. This technology is essential for various applications such as autonomous driving, medical imaging, security systems, and more. In this article, we will explore how to implement image classification using TensorFlow 3.x, covering key concepts, practical examples, best practices, and more.

## Overview

TensorFlow is a robust framework for building, training, and deploying machine learning models. It offers a comprehensive API that includes layers, optimizers, and metrics specifically designed for image classification tasks. The current version of TensorFlow is 3.x, which introduces significant improvements over previous versions, enhancing both performance and ease of use.

## Getting Started

To get started with TensorFlow, you need to install it using pip:

```sh
pip install tensorflow==3.x
```

```python
import tensorflow as tf

# Load the dataset
(train_images, train_labels), (_, _) = tf.keras.datasets.mnist.load_data()

# Preprocess the data
train_images = train_images / 255.0

# Create a model
model = tf.keras.models.Sequential([
    tf.keras.layers.Flatten(input_shape=(28, 28)),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(10)
])

# Compile the model
loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
model.compile(optimizer='adam', loss=loss_fn, metrics=['accuracy'])

# Train the model
model.fit(train_images, train_labels, epochs=5)

# Evaluate the model
_, accuracy = model.evaluate(train_images,  train_labels, verbose=2)
print('\nAccuracy: {:5.2f}%'.format(100 * accuracy))
```

## Core Concepts

### Main Functionality

The core functionality of image classification involves building and training models to classify images. TensorFlow provides a robust API for this purpose, including layers like `Flatten`, activation functions such as ReLU, and optimizers like Adam.

### API Overview

TensorFlow's API for image classification includes several key components:

- **`tf.keras.layers.Flatten`:** Flattens the input to a 1D array.
- **`tf.keras.layers.Dense`:** Fully connected layer with ReLU activation by default.
- **`tf.keras.layers.Dropout`:** Regularizes the model to prevent overfitting.
- **`tf.keras.losses.SparseCategoricalCrossentropy`:** Loss function for multi-class classification.

### Example Usage

Here’s an example of using a pre-trained MobileNetV2 model to classify images:

```python
import tensorflow as tf

# Load a pre-trained model
model = tf.keras.applications.MobileNetV2(weights='imagenet', include_top=True)

# Preprocess an image
img_path = 'path/to/image.jpg'
img = tf.keras.preprocessing.image.load_img(img_path, target_size=(224, 224))
x = tf.keras.preprocessing.image.img_to_array(img)
x = tf.keras.applications.mobilenet_v2.preprocess_input(x[tf.newaxis,...])

# Predict the class
preds = model.predict(x)
print('Predicted:', tf.keras.applications.mobilenet_v2.decode_predictions(preds, top=3)[0])
```

## Practical Examples

### Example 1: Classifying Handwritten Digits

We can use TensorFlow to classify handwritten digits from the MNIST dataset. This example demonstrates building a simple neural network and training it on the data.

```python
import tensorflow as tf

# Load the dataset
(train_images, train_labels), (_, _) = tf.keras.datasets.mnist.load_data()

# Preprocess the data
train_images = train_images / 255.0

# Create a model
model = tf.keras.models.Sequential([
    tf.keras.layers.Flatten(input_shape=(28, 28)),
    tf.keras.layers.Dense(128, activation='relu'),
    tf.keras.layers.Dropout(0.2),
    tf.keras.layers.Dense(10)
])

# Compile the model
loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
model.compile(optimizer='adam', loss=loss_fn, metrics=['accuracy'])

# Train the model
model.fit(train_images, train_labels, epochs=5)

# Evaluate the model
_, accuracy = model.evaluate(train_images,  train_labels, verbose=2)
print('\nAccuracy: {:5.2f}%'.format(100 * accuracy))
```

### Example 2: Classifying Nature Images

We can also use a pre-trained MobileNetV2 model to classify nature images:

```python
import tensorflow as tf

# Load a pre-trained model and preprocess an image
model = tf.keras.applications.MobileNetV2(weights='imagenet', include_top=True)
img_path = 'path/to/nature_image.jpg'
img = tf.keras.preprocessing.image.load_img(img_path, target_size=(224, 224))
x = tf.keras.preprocessing.image.img_to_array(img)
x = tf.keras.applications.mobilenet_v2.preprocess_input(x[tf.newaxis,...])

# Predict the class
preds = model.predict(x)
print('Predicted:', tf.keras.applications.mobilenet_v2.decode_predictions(preds, top=3)[0])
```

## Resources

- [Official TensorFlow Guide](https://www.tensorflow.org/tutorials/images/classification)
- [TensorFlow Tutorial](https://www.tensorflow.org/tutorials/images/cnn)

By following these guidelines, you can effectively implement image classification using TensorFlow.

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
