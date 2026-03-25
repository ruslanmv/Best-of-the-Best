---
title: "TensorFlow Federated: A Framework for Federated Learning and Analytics"
date: 2026-02-04T09:00:00+00:00
last_modified_at: 2026-02-04T09:00:00+00:00
topic_kind: "package"
topic_id: "tensorflow-federated"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - python
  - package
  - pypi
  - tensorflow
  - federated-learning
  - privacy-preserving-ml
  - distributed-computing
  - differential-privacy
excerpt: "TensorFlow Federated (TFF) is an open-source framework for federated learning and federated analytics, enabling machine learning on decentralized data while preserving privacy."
header:
  overlay_image: /assets/images/2026-02-04-package-tensorflow-federated/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-02-04-package-tensorflow-federated/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

TensorFlow Federated (TFF) is an open-source framework for machine learning and computation on decentralized data. It implements the federated learning paradigm, where a shared model is trained across multiple clients (devices or organizations) without collecting their raw data in a central location. Each client trains on its local data and only shares model updates, preserving data privacy.

TFF provides both a high-level API for standard federated learning workflows and a low-level API for expressing custom federated computations.

## Overview

Key features:

* **Federated Learning API** (`tff.learning`) -- high-level tools for federated training and evaluation of Keras and functional models
* **Federated Core API** (`tff.federated_computation`) -- a low-level programming model for expressing arbitrary federated algorithms
* **Simulation runtime** (`tff.simulation`) -- tools for running federated experiments locally with simulated clients
* **Built-in datasets** -- federated versions of EMNIST, Shakespeare, CIFAR-100, Stack Overflow, and more via `tff.simulation.datasets`
* **Differential privacy** integration with `tensorflow-privacy`
* **Aggregation strategies** -- federated averaging, federated SGD, and custom aggregators

Use cases:

* Training models across hospitals without sharing patient records
* Mobile keyboard prediction where typing data stays on device
* Cross-organization collaboration on sensitive financial data
* Federated analytics (computing aggregate statistics without centralizing data)

## Getting Started

Installation:

```
pip install tensorflow-federated
```

TFF requires TensorFlow 2.x. Verify the installation:

```python
import tensorflow_federated as tff
print(tff.__version__)
```

Quick example -- set up federated averaging on the EMNIST dataset:

```python
import tensorflow as tf
import tensorflow_federated as tff

# Load a federated dataset (split by writer/client)
emnist_train, emnist_test = tff.simulation.datasets.emnist.load_data()

# Inspect the dataset structure
example_dataset = emnist_train.create_tf_dataset_for_client(
    emnist_train.client_ids[0]
)
print(f"Number of clients: {len(emnist_train.client_ids)}")
for batch in example_dataset.take(1):
    print(f"Image shape: {batch['pixels'].shape}")
    print(f"Label: {batch['label'].numpy()}")
```

## Core Concepts

### Federated Learning API (tff.learning)

The `tff.learning` module provides high-level building blocks for federated learning. The standard workflow is:

1. Define a Keras model wrapped with `tff.learning.models.from_keras_model()`
2. Build a federated learning process with `tff.learning.algorithms.build_weighted_fed_avg()`
3. Run training rounds by selecting clients and calling the process

### Federated Computation

TFF introduces two placement types that describe where data and computation live:

* `tff.SERVER` -- data or computation on the central server
* `tff.CLIENTS` -- data or computation distributed across clients

The `@tff.federated_computation` decorator lets you define computations that operate across these placements.

### Simulation

The `tff.simulation` module provides tools for simulating federated training locally. `tff.simulation.datasets` includes built-in federated datasets partitioned by natural client boundaries (e.g., by handwriting author in EMNIST).

## Practical Examples

### Example 1: Federated Averaging on EMNIST

```python
import collections
import tensorflow as tf
import tensorflow_federated as tff

# Load the federated EMNIST dataset
emnist_train, emnist_test = tff.simulation.datasets.emnist.load_data()

# Preprocessing function for each client dataset
def preprocess(dataset):
    def element_fn(element):
        return collections.OrderedDict(
            x=tf.reshape(element["pixels"], [-1, 784]),
            y=tf.reshape(element["label"], [-1, 1]),
        )
    return dataset.repeat(5).shuffle(500).batch(20).map(element_fn)

# Define a simple model function
def model_fn():
    keras_model = tf.keras.models.Sequential([
        tf.keras.layers.InputLayer(input_shape=(784,)),
        tf.keras.layers.Dense(200, activation="relu"),
        tf.keras.layers.Dense(200, activation="relu"),
        tf.keras.layers.Dense(10, activation="softmax"),
    ])
    return tff.learning.models.from_keras_model(
        keras_model,
        input_spec=collections.OrderedDict(
            x=tf.TensorSpec(shape=[None, 784], dtype=tf.float32),
            y=tf.TensorSpec(shape=[None, 1], dtype=tf.int32),
        ),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
    )

# Build the federated averaging process
learning_process = tff.learning.algorithms.build_weighted_fed_avg(
    model_fn,
    client_optimizer_fn=lambda: tf.keras.optimizers.SGD(learning_rate=0.02),
    server_optimizer_fn=lambda: tf.keras.optimizers.SGD(learning_rate=1.0),
)

# Initialize the process
state = learning_process.initialize()

# Run a few rounds of training
for round_num in range(5):
    # Select a sample of clients
    client_ids = emnist_train.client_ids[:10]
    client_datasets = [
        preprocess(emnist_train.create_tf_dataset_for_client(cid))
        for cid in client_ids
    ]

    result = learning_process.next(state, client_datasets)
    state = result.state
    metrics = result.metrics
    print(f"Round {round_num + 1}: {metrics['client_work']['train']}")
```

### Example 2: Federated Evaluation

```python
import collections
import tensorflow as tf
import tensorflow_federated as tff

emnist_train, emnist_test = tff.simulation.datasets.emnist.load_data()

def preprocess(dataset):
    def element_fn(element):
        return collections.OrderedDict(
            x=tf.reshape(element["pixels"], [-1, 784]),
            y=tf.reshape(element["label"], [-1, 1]),
        )
    return dataset.batch(20).map(element_fn)

def model_fn():
    keras_model = tf.keras.models.Sequential([
        tf.keras.layers.InputLayer(input_shape=(784,)),
        tf.keras.layers.Dense(200, activation="relu"),
        tf.keras.layers.Dense(10, activation="softmax"),
    ])
    return tff.learning.models.from_keras_model(
        keras_model,
        input_spec=collections.OrderedDict(
            x=tf.TensorSpec(shape=[None, 784], dtype=tf.float32),
            y=tf.TensorSpec(shape=[None, 1], dtype=tf.int32),
        ),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy()],
    )

# Build a federated evaluation computation
evaluation = tff.learning.algorithms.build_fed_eval(model_fn)

# Initialize and evaluate on a sample of test clients
eval_state = evaluation.initialize()
test_client_ids = emnist_test.client_ids[:20]
test_datasets = [
    preprocess(emnist_test.create_tf_dataset_for_client(cid))
    for cid in test_client_ids
]

eval_result = evaluation.next(eval_state, test_datasets)
print(f"Evaluation metrics: {eval_result.metrics}")
```

### Example 3: Custom Federated Computation

```python
import tensorflow_federated as tff

# Define a simple federated computation that averages values across clients
@tff.federated_computation(tff.FederatedType(tf.float32, tff.CLIENTS))
def federated_mean(client_values):
    return tff.federated_mean(client_values)

# Simulate with a list of client values
import tensorflow as tf
result = federated_mean([1.0, 2.0, 3.0, 4.0, 5.0])
print(f"Federated mean: {result}")  # 3.0
```

## Best Practices

* Start with `tff.simulation.datasets` and the built-in federated datasets for prototyping before moving to your own data.
* Use `tff.learning.algorithms.build_weighted_fed_avg()` for the standard Federated Averaging algorithm -- it handles model distribution, local training, and aggregation.
* Keep client datasets reasonably sized and shuffled to simulate realistic on-device training conditions.
* Monitor both server-side and client-side metrics to understand model convergence across the federation.
* For production deployments with privacy guarantees, integrate differential privacy using `tensorflow-privacy` and TFF's `DifferentiallyPrivateFactory` aggregators.
* Use `tff.backends.native.set_local_python_execution_context()` explicitly when running simulations to control the execution backend.

## Conclusion

TensorFlow Federated provides a complete framework for expressing, simulating, and experimenting with federated learning algorithms. Its layered API design -- from high-level federated averaging to low-level federated computations -- makes it suitable for both applied federated learning and research into novel federated algorithms.

Resources:

* [TensorFlow Federated Documentation](https://www.tensorflow.org/federated)
* [TensorFlow Federated GitHub](https://github.com/google-parfait/tensorflow-federated)
* [TFF Tutorials](https://www.tensorflow.org/federated/tutorials/tutorials_overview)
* [Federated Learning Paper (McMahan et al.)](https://arxiv.org/abs/1602.05629)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
