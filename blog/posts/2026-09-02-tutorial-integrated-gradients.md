---
title: "integrated-gradients: method for attributing model predictions to input features"
date: 2026-09-02T09:00:00+00:00
last_modified_at: 2026-09-02T09:00:00+00:00
topic_kind: "tutorial"
topic_id: "integrated-gradients"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - integrated-gradients
  - machine-learning
  - deep-neural-networks
  - attributions
  - prediction-explanation
excerpt: "Learn how to use integrated gradients for explaining predictions in machine learning models, especially in deep neural networks. Get started with the integrated_gradients library and understand key concepts and practical examples."
header:
  overlay_image: /assets/images/2026-09-02-tutorial-integrated-gradients/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-09-02-tutorial-integrated-gradients/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Integrated gradients is a method for attributing the prediction of a machine learning model to its input features. It offers a way to understand which features contribute most to the model's prediction by integrating the model's output along the path from a baseline input to the original input. This method is particularly useful in deep neural networks where model predictions can be complex and difficult to interpret. Readers of this article will learn how to use the `integrated_gradients` library to understand model predictions in a detailed and interpretable manner.

## Overview

Integrated gradients provide a method for attributing the prediction of a model to its input features by integrating the model's output along the path from a baseline to the input. This method is primarily used in machine learning for explaining predictions, especially in deep neural networks. The current version of the `integrated_gradients` library is **0.3.1**, which aligns with the validation report and ensures optimal compatibility and features.

## Getting Started

To get started with the `integrated_gradients` library, you can install it using pip:

```bash
pip install integrated_gradients
```

```python
import numpy as np
import tensorflow as tf
from integrated_gradients import IntegratedGradients

# Load a pre-trained model
model = tf.keras.models.load_model('path/to/model')

# Initialize the IntegratedGradients object
ig = IntegratedGradients(model)

# Prepare a random input data
input_data = np.random.random((1, 28, 28, 1))  # Example input for MNIST

# Compute the attributions
attributions = ig.attribute(input_data, target=0, baselines=np.zeros((1, 28, 28, 1)))

# The attributions will give you the contribution of each pixel to the model's prediction
```

This example demonstrates how to initialize the `IntegratedGradients` class and compute the attributions for a given input and target class.

## Core Concepts

The main functionality of the `IntegratedGradients` class is to calculate the contribution of each input feature to the model's prediction by computing the average gradient of the output with respect to each input feature. This process involves the following steps:

1. **Baseline and Input Preparation**: Define a baseline input and the actual input. For image classification, the baseline can be a black image (all pixels set to 0).

2. **Model Prediction**: Use the model to predict the output for the input and baseline.

3. **Gradient Calculation**: Compute the gradient of the output with respect to the input features.

4. **Integration**: Integrate the gradients along the path from the baseline to the input.

5. **Attribution**: The contribution of each feature is the integral of the gradient over this path.

The API overview for the `IntegratedGradients` class is as follows:

```python
class IntegratedGradients:
    def __init__(self, model):
        # Initialize the model
        self.model = model

    def attribute(self, input_data, target=0, baselines=None, steps=50):
        # Compute the attributions
        pass
```

The `attribute` method takes the input data, target class, baselines, and number of steps for integration. It returns the attributions for each feature.

## Practical Examples

### Example 1: Image Classification

In this example, we will use the `IntegratedGradients` class to understand the contribution of each pixel in an input image to the model's prediction for a given class.

```python
import numpy as np
import tensorflow as tf
from integrated_gradients import IntegratedGradients

# Load a pre-trained model
model = tf.keras.models.load_model('path/to/model')

# Initialize the IntegratedGradients object
ig = IntegratedGradients(model)

# Prepare a random input data for MNIST
input_data = np.random.random((1, 28, 28, 1))

# Compute the attributions
attributions = ig.attribute(input_data, target=0, baselines=np.zeros((1, 28, 28, 1)))

# Output the attributions
print(attributions)
```

### Example 2: Text Classification

In this example, we will use the `IntegratedGradients` class to understand the contribution of each word in a text input to the model's prediction for a given class.

```python
import numpy as np
import tensorflow as tf
from integrated_gradients import IntegratedGradients

# Load a pre-trained model
model = tf.keras.models.load_model('path/to/model')

# Initialize the IntegratedGradients object
ig = IntegratedGradients(model)

# Prepare a random input data for text classification
input_data = np.random.random((1, 300))  # Example input, 300 features for a word embedding

# Compute the attributions
attributions = ig.attribute(input_data, target=0, baselines=np.zeros((1, 300)))

# Output the attributions
print(attributions)
```

These examples demonstrate how to use the `IntegratedGradients` class for different types of input data, providing insights into the model's decision-making process.

## Best Practices

- **Use the Latest Version**: Always use the latest version of the `integrated_gradients` library for optimal performance and features.
- **Regular Updates**: Regularly check the official GitHub repository for updates and bug fixes.
- **Proper Input Data**: Ensure that the input data is properly formatted to avoid common pitfalls.

## Conclusion

Integrated gradients is a powerful tool for explaining predictions in deep learning models, providing insights into which features are most important. By following the best practices and using the provided examples, you can effectively interpret the predictions of your models. For more in-depth learning, refer to the official documentation and explore the provided web tutorials.

- **Resources**:
  - [Integrated Gradients for Deep Learning](https://christophm.github.io/interpretable-ml-book/integrated-gradients.html)
  - [Integrated Gradients Example](https://towardsdatascience.com/integrated-gradients-explained-with-python-code-7fda63d95721)
  - [Official TensorFlow Forums](https://github.com/interpretable-ml/integrated-gradients)

Stay updated with the latest repository commits and community discussions for ongoing support and improvements.

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
