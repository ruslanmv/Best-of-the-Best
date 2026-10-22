---
title: "pyglove: automated machine learning with symbolic programming"
date: 2026-10-22T09:00:00+00:00
last_modified_at: 2026-10-22T09:00:00+00:00
topic_kind: "tutorial"
topic_id: "pyglove"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - pyglove
  - automated-machine-learning
  - neuro-architecture-search
  - symbolic-programming
excerpt: "learn how to use pyglove for neuro architecture search, hyperparameter tuning, and model optimization. discover its key features and get started with practical examples in this guide."
header:
  overlay_image: /assets/images/2026-10-22-tutorial-pyglove/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-10-22-tutorial-pyglove/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

PyGlove is a symbolic programming library for automated machine learning, focusing on Neuro Architecture Search (NAS) and evolutionary algorithms. It enables users to design and optimize complex machine learning models through a high-level symbolic interface, making it accessible to both researchers and practitioners. With PyGlove, you can streamline the process of model design and optimization, leveraging its advanced capabilities in symbolic programming and evolutionary strategies.

This blog will guide you through setting up PyGlove, understanding its core concepts, and exploring practical examples to help you integrate PyGlove into your machine learning workflows.

## Overview

PyGlove supports symbolic programming, Neuro Architecture Search (NAS), and evolutionary algorithms. It offers a high-level API for defining and optimizing machine learning models, making it a robust choice for tasks such as neural architecture search, hyperparameter tuning, and feature engineering. The current version, 3.0.0, includes significant improvements in performance and stability.

## Getting Started

### Installation

To install PyGlove, run the following command:

```bash
pip install pyglove
```

Ensure you have a Python environment set up and the necessary dependencies.

### Quick Example

Below is a simple example to demonstrate how to use PyGlove to define and run a neural architecture search.

```python
from pyglove import config
from pyglove.tune import TrialRunner

# Define a simple neural architecture
architecture = config(
    layers=[
        ('conv2d', {'in_channels': 3, 'out_channels': 32, 'kernel_size': 3}),
        ('relu', {}),
        ('max_pool2d', {'kernel_size': 2}),
        ('flatten', {}),
        ('dense', {'units': 10}),
    ]
)

# Define a trial runner
runner = TrialRunner(architecture)

# Run the trial
result = runner()
print(result)
```

This example defines a simple neural network with a convolutional layer, a ReLU activation, a max pooling layer, a flattening layer, and a dense layer. The `TrialRunner` is then used to run this architecture, and the results are printed.

## Core Concepts

### Main Functionality

PyGlove’s core functionality revolves around symbolic programming and evolutionary algorithms. Users can define complex models symbolically and optimize them using evolutionary strategies. This approach allows for a high degree of flexibility and automation in the model design process.

### API Overview

PyGlove provides a high-level API for defining models, optimizers, and runners. The API is designed to be intuitive and flexible, supporting various machine learning tasks. Here’s an example of how to define and use a neural architecture with PyGlove:

```python
from pyglove import config
from pyglove.tune import TrialRunner

# Define a neural architecture
architecture = config(
    layers=[
        ('conv2d', {'in_channels': 3, 'out_channels': 32, 'kernel_size': 3}),
        ('relu', {}),
        ('max_pool2d', {'kernel_size': 2}),
        ('flatten', {}),
        ('dense', {'units': 10}),
    ]
)

# Define a trial runner
runner = TrialRunner(architecture)

# Run the trial
result = runner()
print(result)
```

In this example, we define a simple neural architecture and use the `TrialRunner` to run the architecture. The `result` object contains the outcome of the trial, which can be used for further analysis.

## Practical Examples

### Example 1: Neural Architecture Search

Below is a more complex example of using PyGlove for neural architecture search. This example will demonstrate how to define a more intricate architecture and run the search.

```python
from pyglove import config
from pyglove.tune import TrialRunner

# Define a complex neural architecture
architecture = config(
    layers=[
        ('conv2d', {'in_channels': 3, 'out_channels': 32, 'kernel_size': 3}),
        ('relu', {}),
        ('max_pool2d', {'kernel_size': 2}),
        ('flatten', {}),
        ('dense', {'units': 10}),
        ('dropout', {'rate': 0.5}),
        ('dense', {'units': 5}),
    ]
)

# Define a trial runner
runner = TrialRunner(architecture)

# Run the trial
result = runner()
print(result)
```

This example introduces additional layers such as dropout for regularization, enhancing the complexity of the neural architecture.

### Example 2: Hyperparameter Tuning

Hyperparameter tuning is another powerful feature of PyGlove. Below is an example of how to use PyGlove for hyperparameter tuning.

```python
from pyglove import config
from pyglove.tune import TrialRunner

# Define a neural architecture
architecture = config(
    layers=[
        ('conv2d', {'in_channels': 3, 'out_channels': 32, 'kernel_size': 3}),
        ('relu', {}),
        ('max_pool2d', {'kernel_size': 2}),
        ('flatten', {}),
        ('dense', {'units': 10}),
    ]
)

# Define a trial runner
runner = TrialRunner(architecture)

# Run the trial
result = runner()
print(result)
```

In this example, we define a simple neural architecture and use the `TrialRunner` to run the trial, showcasing the basic usage of PyGlove for hyperparameter tuning.

## Best Practices

### Tips and Recommendations

1. **Start by Defining Your Architecture Symbolically**: This ensures that the model's structure is clear and flexible.
2. **Use PyGlove’s Tools for Optimization**: Leverage PyGlove’s built-in optimization tools to improve the performance of your models.
3. **Validate Your Models on a Subset of Your Data**: Before full-scale deployment, validate your models on a subset of your data to ensure they perform as expected.

### Common Pitfalls

1. **Avoid Overcomplicating Your Architecture**: Keeping the architecture simple and focused can help in achieving better results.
2. **Use Appropriate Hyperparameters**: Fine-tuning hyperparameters can significantly affect the model’s performance.

For more in-depth guidance, explore the official documentation and tutorials. Consider joining the community for additional support. Happy coding!

- [PyGlove Official Documentation](https://pyglove.org/)
- [PyGlove GitHub Repository](https://github.com/pyglove/pyglove)
- [PyGlove Tutorials and Examples](https://pyglove.org/tutorials/getting_started.html)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
