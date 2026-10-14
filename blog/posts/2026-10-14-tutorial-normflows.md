---
title: "normflows: Probabilistic Modeling with Normalizing Flows"
date: 2026-10-14T09:00:00+00:00
last_modified_at: 2026-10-14T09:00:00+00:00
topic_kind: "tutorial"
topic_id: "normflows"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - normflows
  - normalizing-flows
  - machine-learning
  - python-package
excerpt: "Learn about normflows, a Python package for advanced probabilistic modeling using normalizing flows. Discover installation, core concepts, and practical examples."
header:
  overlay_image: /assets/images/2026-10-14-tutorial-normflows/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-10-14-tutorial-normflows/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Normflows is a powerful Python package for probabilistic modeling and density estimation using normalizing flows. Normalizing flows are a method for transforming a simple probability distribution into a more complex one, making them ideal for tasks such as generative modeling, density estimation, and conditional flows. This package is essential for advanced machine learning practitioners and researchers, offering a flexible and efficient architecture.

In this article, we will cover the installation process, core concepts, practical examples, and best practices for using normflows. By the end, you will be able to create and utilize normalizing flows for your own projects.

## Overview

Normflows is a mature and actively maintained package, currently at version 3.x. It offers a wide range of features, including a flexible architecture that supports various flow types and efficient sampling techniques. The package is widely used for generative modeling, density estimation, and conditional flows. 

For detailed information, you can refer to the official documentation and GitHub repository. The official documentation provides comprehensive guides and examples, while the GitHub repository contains the latest updates, issues, and pull requests.

## Getting Started

To get started with normflows, you can install it via pip:

```sh
pip install normflows
```

```python
import normflows

# Create a simple flow
model = normflows.NormalizingFlow()

# Sample from the flow
samples = model.sample(1000)
```

This code snippet demonstrates the basic setup and sampling process. For more detailed usage, refer to the official documentation.

## Core Concepts

Normflows allows you to build probabilistic models using normalizing flows. A normalizing flow is a bijective function that transforms a simple probability distribution into a more complex one. The package supports various types of flow architectures, such as affine couplings, inverse autoregressive flows (IAFs), and more.

### API Overview

The key functions and classes in normflows are as follows:

- `normflows.NormalizingFlow`: The base class for normalizing flows.
- `normflows.transforms`: Contains various transform classes, such as `AffineCoupling` and `IAF`.
- `normflows.utils`: Utility functions for sampling and visualization.

Here is an example of creating a simple flow and sampling from it:

```python
import normflows

# Create a simple flow
model = normflows.NormalizingFlow(transforms=[normflows.transforms.AffineCoupling()])

# Sample from the flow
samples = model.sample(1000)
print(samples)
```

This example demonstrates the creation of a flow with a single affine coupling transform and sampling from it.

## Practical Examples

### Example 1: Generative Modeling Using a Simple Flow

In this example, we will create a normalizing flow for generative modeling. We will use a simple affine coupling transform and sample from the flow to generate new data points.

```python
import normflows
import numpy as np

# Create a simple flow
model = normflows.NormalizingFlow(transforms=[normflows.transforms.AffineCoupling()])

# Sample from the flow
samples = model.sample(1000)
print(samples)

# Visualize the samples
import matplotlib.pyplot as plt

plt.hist(samples[:, 0], bins=30, density=True, alpha=0.6, color='b')
plt.show()
```

This code creates a flow with a single affine coupling transform, samples from it, and visualizes the generated data.

### Example 2: Conditional Flows for Domain Adaptation

In this example, we will demonstrate the use of conditional flows for domain adaptation. We will create a flow that can adapt to different domains by conditioning on additional features.

```python
import normflows
import numpy as np

# Define the domain labels
domain_labels = np.random.randint(0, 2, 1000)

# Create a conditional flow
model = normflows.NormalizingFlow(transforms=[normflows.transforms.AffineCoupling()])

# Sample from the flow with conditioning
samples = model.sample(1000, condition=domain_labels)
print(samples)

# Visualize the samples conditioned on different domains
plt.hist(samples[domain_labels == 0, 0], bins=30, density=True, alpha=0.6, color='b', label='Domain 0')
plt.hist(samples[domain_labels == 1, 0], bins=30, density=True, alpha=0.6, color='r', label='Domain 1')
plt.legend()
plt.show()
```

This code creates a flow with a single affine coupling transform, samples from it conditionally based on domain labels, and visualizes the samples for different domains.

## Best Practices

- **Follow the Official Documentation**: The official documentation provides comprehensive guides and examples to help you get started and advanced usage.
- **Use the Latest Version**: Ensure you are using the latest version of normflows to avoid deprecated features and take advantage of the latest improvements.
- **Common Pitfalls**: Avoid using deprecated features and ensure compatibility with the current version.

By following these best practices, you can make the most out of normflows and integrate it effectively into your projects.

## Conclusion

Normflows is a powerful tool for probabilistic modeling and density estimation. It offers a flexible and efficient architecture, supporting various flow types and enabling tasks such as generative modeling and conditional flows. By exploring the official documentation, GitHub repository, and community discussions, you can deepen your understanding and utilize normflows effectively.

To get started, visit the official documentation and GitHub repository for the latest updates and resources. Encourage readers to explore normflows further and integrate it into their projects for advanced machine learning tasks.

- Official Documentation: <https://normflows.readthedocs.io/en/stable/getting_started.html>
- GitHub Repository: <https://github.com/vitchyr/normflows/tree/main/examples>
- GitHub: <https://github.com/vitchyr/normflows>

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
