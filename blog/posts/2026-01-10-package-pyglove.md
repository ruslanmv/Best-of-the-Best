---
title: "PyGlove: Symbolic Programming for AutoML and Beyond"
date: 2026-01-10T09:00:00+00:00
last_modified_at: 2026-01-10T09:00:00+00:00
topic_kind: "package"
topic_id: "pyglove"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - symbolic-programming
  - automl
  - hyperparameter-tuning
  - neural-architecture-search
  - google
excerpt: "PyGlove is Google's library for symbolic programming in Python, enabling manipulation of programs as mutable objects for AutoML, hyperparameter tuning, and neural architecture search."
header:
  overlay_image: /assets/images/2026-01-10-package-pyglove/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-01-10-package-pyglove/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

PyGlove is a general-purpose symbolic programming library developed by Google that allows you to manipulate Python objects as mutable, searchable symbolic trees. Originally designed to power large-scale AutoML research, PyGlove enables hyperparameter tuning, neural architecture search, and program synthesis by treating Python classes and their parameters as symbolic, composable building blocks.

What makes PyGlove distinctive is that it does not require you to define a separate search space specification. Instead, you annotate your existing Python classes with symbolic types, and PyGlove can then traverse, mutate, and search over them. This approach bridges the gap between program definition and search space definition, making complex AutoML workflows far more natural.

In this guide, you will learn how to define symbolic classes, specify search spaces inline, and run hyperparameter searches using PyGlove.

## Overview

Key features of PyGlove:

- **Symbolic classes**: Define Python classes whose attributes are symbolically typed and mutable after construction
- **Inline search spaces**: Use `pg.oneof`, `pg.floatv`, `pg.intv`, and other hyper primitives directly in object construction
- **Search algorithms**: Built-in support for random search, evolutionary algorithms, and more
- **Symbolic manipulation**: Clone, traverse, query, and rebind any symbolic object programmatically
- **Composability**: Nest symbolic objects arbitrarily to represent complex, hierarchical configurations

Use cases:

- Hyperparameter tuning for machine learning models
- Neural architecture search (NAS)
- Automated program synthesis and configuration optimization
- Managing complex, hierarchical experiment configurations

## Getting Started

Install PyGlove using pip:

```bash
pip install pyglove
```

Here is a complete working example that defines a symbolic class and searches over its parameters:

```python
import pyglove as pg

# Define a symbolic class for a training configuration
@pg.members([
    ('learning_rate', pg.typing.Float(min_value=1e-5, max_value=1.0)),
    ('batch_size', pg.typing.Int(min_value=8, max_value=256)),
    ('optimizer', pg.typing.Str()),
])
class TrainConfig(pg.Object):
    pass

# Create a concrete instance
config = TrainConfig(learning_rate=0.001, batch_size=32, optimizer='adam')
print(config)

# Symbolically rebind a parameter
config.rebind({'learning_rate': 0.01})
print(config.learning_rate)  # 0.01
```

## Core Concepts

### Symbolic Classes with `pg.Object` and `pg.members`

PyGlove's foundation is the `pg.Object` base class. By decorating a class with `@pg.members`, you declare its attributes with symbolic types:

```python
import pyglove as pg

@pg.members([
    ('hidden_size', pg.typing.Int(min_value=16, max_value=1024)),
    ('dropout', pg.typing.Float(min_value=0.0, max_value=0.5)),
    ('activation', pg.typing.Enum('relu', ['relu', 'gelu', 'tanh'])),
])
class ModelConfig(pg.Object):
    pass

config = ModelConfig(hidden_size=256, dropout=0.1, activation='gelu')
```

Symbolic objects support deep cloning, comparison, serialization, and programmatic traversal out of the box.

### Defining Search Spaces with Hyper Primitives

PyGlove provides hyper primitives to define search spaces inline within symbolic objects:

```python
import pyglove as pg

# Define a search space using hyper primitives
search_space = TrainConfig(
    learning_rate=pg.floatv(1e-4, 1e-1),   # Continuous float range
    batch_size=pg.oneof([16, 32, 64, 128]), # Categorical choice
    optimizer=pg.oneof(['adam', 'sgd', 'adamw'])
)
```

Key hyper primitives:

- `pg.oneof(candidates)`: Choose one from a list of candidates
- `pg.floatv(min, max)`: A continuous float in a range
- `pg.intv(min, max)`: An integer in a range
- `pg.manyof(k, candidates)`: Choose k items from candidates
- `pg.sublist_of(k, candidates)`: An ordered sublist of length k

### Running a Search

Use `pg.sample` to iterate over the search space with a search algorithm:

```python
import pyglove as pg

@pg.members([
    ('learning_rate', pg.typing.Float()),
    ('batch_size', pg.typing.Int()),
    ('optimizer', pg.typing.Str()),
])
class TrainConfig(pg.Object):
    pass

search_space = TrainConfig(
    learning_rate=pg.floatv(1e-4, 1e-1),
    batch_size=pg.oneof([16, 32, 64, 128]),
    optimizer=pg.oneof(['adam', 'sgd', 'adamw'])
)

# Sample configurations using random search
for config, feedback in pg.sample(
    search_space,
    pg.geno.Random(),
    num_examples=5
):
    # Simulate an evaluation (replace with real training logic)
    score = 1.0 / config.learning_rate * config.batch_size
    feedback(score)  # Report the result back to the search algorithm
    print(f"Config: lr={config.learning_rate:.4f}, bs={config.batch_size}, "
          f"opt={config.optimizer}, score={score:.2f}")
```

## Practical Examples

### Example 1: Hyperparameter Tuning

```python
import pyglove as pg

@pg.members([
    ('lr', pg.typing.Float()),
    ('weight_decay', pg.typing.Float()),
    ('num_layers', pg.typing.Int()),
    ('hidden_dim', pg.typing.Int()),
])
class HyperParams(pg.Object):
    pass

space = HyperParams(
    lr=pg.floatv(1e-5, 1e-2),
    weight_decay=pg.floatv(1e-6, 1e-3),
    num_layers=pg.intv(2, 8),
    hidden_dim=pg.oneof([128, 256, 512, 1024])
)

best_score = 0
best_config = None

for params, feedback in pg.sample(space, pg.geno.Random(), num_examples=20):
    # Replace with actual model training and evaluation
    score = params.hidden_dim / (params.lr * 1000 + params.num_layers)
    feedback(score)

    if score > best_score:
        best_score = score
        best_config = params.clone()

print(f"Best config: {best_config}")
print(f"Best score: {best_score:.2f}")
```

### Example 2: Symbolic Object Manipulation

```python
import pyglove as pg

@pg.members([
    ('units', pg.typing.Int()),
    ('activation', pg.typing.Str()),
])
class DenseLayer(pg.Object):
    pass

@pg.members([
    ('layers', pg.typing.List(pg.typing.Any())),
    ('output_units', pg.typing.Int()),
])
class Network(pg.Object):
    pass

# Build a network configuration symbolically
network = Network(
    layers=[
        DenseLayer(units=256, activation='relu'),
        DenseLayer(units=128, activation='relu'),
    ],
    output_units=10
)

# Deep clone and modify
variant = network.clone()
variant.rebind({'layers[0].units': 512, 'layers[1].activation': 'gelu'})

print(f"Original first layer units: {network.layers[0].units}")   # 256
print(f"Variant first layer units: {variant.layers[0].units}")    # 512

# Serialize to JSON and back
json_str = network.to_json_str()
restored = pg.from_json_str(json_str)
print(f"Restored: {restored}")
```

## Best Practices

- **Start with `pg.Object`**: Define your configurations as symbolic classes rather than plain dictionaries. This gives you type checking, serialization, and traversal for free.
- **Use hyper primitives inline**: Place `pg.oneof`, `pg.floatv`, and `pg.intv` directly in your object construction to keep search space definitions close to the code they configure.
- **Leverage `rebind` for mutations**: Use `rebind` instead of creating new objects when you want to change specific parameters in a deep configuration tree.
- **Serialize configurations**: Use `to_json_str()` and `from_json_str()` to save and reload experiment configurations for reproducibility.
- **Choose appropriate search algorithms**: Start with `pg.geno.Random()` for exploration, then move to `pg.evolution.regularized_evolution()` for more efficient search.

Common pitfalls:

- PyGlove is not a general-purpose ML training library. It manages configurations and search spaces, not data loading or model training.
- Symbolic types enforce constraints at construction time. Passing values outside declared ranges will raise errors.
- Forgetting to call `feedback(score)` inside a `pg.sample` loop will prevent the search algorithm from learning.

## Conclusion

PyGlove provides a powerful paradigm for working with Python programs as symbolic, mutable objects. By combining symbolic class definitions with inline search space primitives, it enables clean and scalable approaches to hyperparameter tuning, neural architecture search, and configuration management. Its tight integration of program structure and search space makes it especially valuable for machine learning research at scale.

Resources:
- [GitHub - google/pyglove](https://github.com/google/pyglove)
- [PyGlove Paper (NeurIPS 2020)](https://arxiv.org/abs/2101.08809)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
