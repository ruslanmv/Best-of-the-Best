---
title: "sample-factory: modular reinforcement learning framework"
date: 2026-11-20T09:00:00+00:00
last_modified_at: 2026-11-20T09:00:00+00:00
topic_kind: "tutorial"
topic_id: "sample-factory"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - sample-factory
  - reinforcement-learning
  - rl-algorithms
  - modular-architecture
excerpt: "sample factory is a flexible and efficient platform for researchers and practitioners to experiment with rl algorithms. learn key features, installation, and practical examples."
header:
  overlay_image: /assets/images/2026-11-20-tutorial-sample-factory/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-11-20-tutorial-sample-factory/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Sample Factory is a modular reinforcement learning (RL) framework that supports a wide range of RL algorithms and environments. It matters because Sample Factory provides a flexible and efficient platform for researchers and practitioners to experiment with RL algorithms. Readers will learn about the key features of Sample Factory, how to get started, and practical examples of using the framework.

## Overview

Sample Factory's modular architecture allows for easy integration of different RL algorithms and environments. It supports various RL algorithms and has an extensive environment library. The current version is 3.2.1. The framework is ideal for research and development of RL agents, training and evaluation of RL models, and more.

## Getting Started

To install Sample Factory, use the following command:

```bash
pip install sample-factory
```

```python
from sample_factory.run import main

def dqn_example():
    config = {
        "algo": "dqn",
        "env": "atari破冰船",
        "num_workers": 4,
        "num_envs_per_worker": 1,
        "log_interval_steps": 10000,
    }
    return main(config)

if __name__ == "__main__":
    dqn_example()
```

This script sets up a DQN agent to train on the "atari破冰船" environment, using 4 workers and logging every 10,000 steps.

## Core Concepts

Sample Factory's modular design allows for easy integration of different RL algorithms and environments. The main functionality is provided through the `sample_factory.run.main` function, which takes a configuration dictionary as input. The configuration dictionary specifies the algorithm to use, the environment, and other parameters.

Here is an example of using the PPO algorithm with a custom environment:

```python
from sample_factory.run import main

def custom_example():
    config = {
        "algo": "ppo",
        "env": "custom_env",
        "num_workers": 2,
        "num_envs_per_worker": 2,
        "log_interval_steps": 5000,
    }
    return main(config)

if __name__ == "__main__":
    custom_example()
```

In this example, the PPO algorithm is used with a custom environment, running 2 workers, each with 2 environments, and logging every 5,000 steps.

## Practical Examples

### Example 1: DQN Agent

The following code demonstrates how to train a DQN agent on the "atari破冰船" environment:

```python
from sample_factory.run import main

def dqn_example():
    config = {
        "algo": "dqn",
        "env": "atari破冰船",
        "num_workers": 4,
        "num_envs_per_worker": 1,
        "log_interval_steps": 10000,
    }
    return main(config)

if __name__ == "__main__":
    dqn_example()
```

### Example 2: PPO Agent with Custom Environment

This example shows how to train a PPO agent using a custom environment:

```python
from sample_factory.run import main

def custom_example():
    config = {
        "algo": "ppo",
        "env": "custom_env",
        "num_workers": 2,
        "num_envs_per_worker": 2,
        "log_interval_steps": 5000,
    }
    return main(config)

if __name__ == "__main__":
    custom_example()
```

## Best Practices

- **Tips and Recommendations**:
  - Always specify the environment and algorithm in the configuration.
  - Use `num_workers` and `num_envs_per_worker` to adjust the training workload.
- **Common Pitfalls**:
  - Forgetting to specify the environment name can lead to errors.

## Conclusion

Sample Factory is a robust RL framework with a modular design and extensive support for various algorithms and environments. The framework is ideal for researchers and practitioners looking to experiment with RL algorithms. For more details, explore the official documentation and GitHub repository.

- [Sample Factory GitHub Repository](https://github.com/sample-factory/sample-factory)
- [Sample Factory Project Website](https://sample-factory.org/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
