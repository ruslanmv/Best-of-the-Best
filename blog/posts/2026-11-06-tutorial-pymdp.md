---
title: "pymdp: Python Package for Markov Decision Processes"
date: 2026-11-06T09:00:00+00:00
last_modified_at: 2026-11-06T09:00:00+00:00
topic_kind: "tutorial"
topic_id: "pymdp"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - pymdp
  - markov-decision-processes
  - robotics
  - economics
excerpt: "Learn about pymdp, a powerful Python library for modeling and solving MDPs. Explore its key features, installation, and practical examples in robotics and economics."
header:
  overlay_image: /assets/images/2026-11-06-tutorial-pymdp/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-11-06-tutorial-pymdp/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

pymdp is a Python package designed for modeling and solving Markov Decision Processes (MDPs) using a discrete-state framework. MDPs are widely used in various fields such as robotics, economics, and healthcare for decision-making under uncertainty. This article aims to provide an overview of pymdp, guide readers through its installation and basic usage, and present practical examples of its application. By the end of this article, you will have a solid understanding of how to leverage pymdp for your MDP modeling needs.

## Overview

pymdp is a powerful and flexible toolset for researchers and practitioners working with MDPs. Its key features include support for a wide range of MDP models and the provision of tools for both forward and backward inference. The current stable version, 0.4.0, includes updated features and bug fixes, ensuring reliability and performance.

## Getting Started

To install pymdp, use the following command:

```sh
pip install pymdp
```

Once installed, you can start using the package by importing the necessary components. Here is a quick example to demonstrate the basic setup:

```python
from pymdp.core import StateSpace, ObservationSpace, ActionSpace, TransitionModel, EmissionModel, PriorModel, PosteriorModel
from pymdp.algos import hmm_filter, hmm_baum_welch

# Define state, action, and observation spaces
state_space = StateSpace([0, 1])
action_space = ActionSpace([0, 1])
observation_space = ObservationSpace([0, 1])

# Define transition, emission, and prior models
transition_model = TransitionModel(state_space, action_space)
emission_model = EmissionModel(state_space, observation_space)
prior_model = PriorModel(state_space)

# Perform filtering and smoothing
posterior_model = PosteriorModel(transition_model, emission_model, prior_model)
filtered_posteriors = hmm_filter(posterior_model, [0, 1])
```

## Core Concepts

pymdp provides a comprehensive set of tools for modeling and solving MDPs, including state space, action space, observation space, transition models, emission models, and prior models. The package's API is well-documented and easy to navigate, offering both high-level and low-level functions for flexibility.

### Example Usage

To illustrate the core concepts, let's walk through an example of robot navigation. In this scenario, the robot needs to navigate through a series of states based on its observations and actions.

```python
from pymdp.core import StateSpace, ObservationSpace, ActionSpace, TransitionModel, EmissionModel, PriorModel, PosteriorModel
from pymdp.algos import hmm_filter, hmm_baum_welch

# Define state and observation spaces
state_space = StateSpace([0, 1])
observation_space = ObservationSpace([0, 1])

# Define transition and emission models
transition_model = TransitionModel(state_space, action_space)
emission_model = EmissionModel(state_space, observation_space)

# Perform filtering
posterior_model = PosteriorModel(transition_model, emission_model, prior_model)
filtered_posteriors = hmm_filter(posterior_model, [0, 1])
```

Similarly, let's explore an example of economic decision-making, where the model needs to predict future states based on current observations and actions.

```python
from pymdp.core import StateSpace, ObservationSpace, ActionSpace, TransitionModel, EmissionModel, PriorModel, PosteriorModel
from pymdp.algos import hmm_filter, hmm_baum_welch

# Define state and observation spaces
state_space = StateSpace([0, 1])
observation_space = ObservationSpace([0, 1])

# Define transition and emission models
transition_model = TransitionModel(state_space, action_space)
emission_model = EmissionModel(state_space, observation_space)

# Perform filtering
posterior_model = PosteriorModel(transition_model, emission_model, prior_model)
filtered_posteriors = hmm_filter(posterior_model, [0, 1])
```

## Best Practices

### Tips and Recommendations

- Always use the latest stable version, 0.4.0, for the most up-to-date features and bug fixes.
- Follow the comprehensive documentation and examples available in the GitHub repository and the PyMDP official documentation to get started with the package.

### Common Pitfalls

- Avoid using deprecated features, which are noted in the package's documentation.

## Conclusion

pymdp is a robust and versatile package for modeling and solving MDPs, offering a wide range of functionalities and extensive documentation. By staying updated with the latest version and examples provided by the official documentation, you can effectively leverage pymdp for your MDP modeling needs. Readers are encouraged to explore the official documentation and GitHub repository for more detailed information and examples.

### Resources

- [pymdp Official Documentation](https://pymdp.readthedocs.io/en/latest/)
- [GitHub Repository](https://github.com/alan-turing-institute/pymdp)
- [PyPI Page](https://pypi.org/project/pymdp/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
