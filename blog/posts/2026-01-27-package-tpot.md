---
title: "TPOT: Automated Machine Learning with Genetic Programming"
date: 2026-01-27T09:00:00+00:00
last_modified_at: 2026-01-27T09:00:00+00:00
topic_kind: "package"
topic_id: "TPOT"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - python
  - package
  - pypi
  - automl
  - machine-learning
  - genetic-programming
  - scikit-learn
  - pipeline-optimization
excerpt: "TPOT is a Python AutoML tool that uses genetic programming to automatically design and optimize scikit-learn machine learning pipelines."
header:
  overlay_image: /assets/images/2026-01-27-package-tpot/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-01-27-package-tpot/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

TPOT (Tree-based Pipeline Optimization Tool) is a Python AutoML library that uses genetic programming to automatically find the best machine learning pipeline for a given dataset. Rather than requiring you to manually select preprocessors, feature selectors, and classifiers, TPOT explores thousands of possible pipeline configurations and returns the one that performs best under cross-validation.

TPOT builds on top of scikit-learn, so the pipelines it produces are standard scikit-learn `Pipeline` objects that you can inspect, modify, and deploy.

## Overview

Key features:

* Automated pipeline search using genetic programming (evolutionary optimization)
* Explores preprocessors, feature selection, and model hyperparameters jointly
* Supports both classification (`TPOTClassifier`) and regression (`TPOTRegressor`)
* Exports the best pipeline as a standalone Python script
* Built on scikit-learn -- all generated pipelines use familiar scikit-learn components
* Configurable search space, scoring metrics, and computational budget

Use cases:

* Rapid prototyping -- find a strong baseline pipeline without manual experimentation
* Hyperparameter and pipeline architecture search
* Benchmarking against hand-tuned models
* Educational tool for understanding which preprocessing steps and models work well on a dataset

Current version: **TPOT 0.12.2**

## Getting Started

Installation:

```
pip install tpot
```

TPOT requires scikit-learn, NumPy, SciPy, pandas, joblib, and optionally XGBoost. Install everything with:

```
pip install tpot[optional]
```

Quick example -- run TPOT on the Iris dataset and export the best pipeline:

```python
from tpot import TPOTClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

# Load data
iris = load_iris()
X_train, X_test, y_train, y_test = train_test_split(
    iris.data, iris.target, test_size=0.2, random_state=42
)

# Create and run TPOT
tpot = TPOTClassifier(
    generations=5,
    population_size=20,
    verbosity=2,
    random_state=42,
)
tpot.fit(X_train, y_train)

# Evaluate on the test set
print(f"Test accuracy: {tpot.score(X_test, y_test):.4f}")

# Export the best pipeline as a Python script
tpot.export("best_pipeline.py")
print("Best pipeline exported to best_pipeline.py")
```

## Core Concepts

### Genetic Programming

TPOT represents machine learning pipelines as trees and uses genetic programming to evolve them. Each generation, TPOT:

1. Evaluates every pipeline in the population using cross-validation
2. Selects the top-performing pipelines
3. Applies mutation (random changes) and crossover (combining parts of two pipelines) to produce the next generation
4. Repeats until the generation budget is exhausted

### TPOTClassifier and TPOTRegressor

These are the two main classes:

* `TPOTClassifier` -- optimizes pipelines for classification tasks (default scoring: accuracy)
* `TPOTRegressor` -- optimizes pipelines for regression tasks (default scoring: negative MSE)

Both share the same key parameters:

* `generations` -- number of evolutionary generations to run
* `population_size` -- number of pipelines evaluated per generation
* `scoring` -- the metric to optimize (e.g., `"accuracy"`, `"f1"`, `"neg_mean_squared_error"`)
* `cv` -- number of cross-validation folds (default: 5)
* `max_time_mins` -- optional wall-clock time limit
* `n_jobs` -- number of parallel jobs

### Pipeline Export

After fitting, `tpot.export("pipeline.py")` writes a self-contained Python script that recreates the best pipeline using only scikit-learn imports. This makes it easy to deploy or share the result without depending on TPOT at runtime.

## Practical Examples

### Example 1: Classification with Custom Scoring

```python
from tpot import TPOTClassifier
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split

X, y = load_breast_cancer(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

tpot = TPOTClassifier(
    generations=10,
    population_size=30,
    scoring="f1",
    cv=5,
    verbosity=2,
    random_state=42,
)
tpot.fit(X_train, y_train)

print(f"Test F1 score: {tpot.score(X_test, y_test):.4f}")
tpot.export("breast_cancer_pipeline.py")
```

### Example 2: Regression on Boston-style Data

```python
from tpot import TPOTRegressor
from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import train_test_split

X, y = fetch_california_housing(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

tpot = TPOTRegressor(
    generations=5,
    population_size=20,
    scoring="neg_mean_squared_error",
    verbosity=2,
    random_state=42,
)
tpot.fit(X_train, y_train)

print(f"Test R^2 score: {tpot.score(X_test, y_test):.4f}")
tpot.export("housing_pipeline.py")
```

### Example 3: Time-limited Search

When you want results within a fixed time budget rather than a fixed number of generations:

```python
from tpot import TPOTClassifier
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split

X, y = load_digits(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

tpot = TPOTClassifier(
    max_time_mins=5,       # Stop after 5 minutes
    max_eval_time_mins=1,  # Kill any single pipeline that takes over 1 minute
    verbosity=2,
    random_state=42,
)
tpot.fit(X_train, y_train)

print(f"Test accuracy: {tpot.score(X_test, y_test):.4f}")
print(f"Best pipeline: {tpot.fitted_pipeline_}")
```

### Example 4: Inspecting the Exported Pipeline

After calling `tpot.export("pipeline.py")`, the generated file looks something like this:

```python
# Example output from tpot.export() -- actual content depends on dataset
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import MaxAbsScaler

# NOTE: Replace this with your actual data loading code
tpot_data = pd.read_csv("PATH/TO/DATA", sep="COLUMN_SEPARATOR", dtype=np.float64)
features = tpot_data.drop("target", axis=1)
training_features, testing_features, training_target, testing_target = \
    train_test_split(features, tpot_data["target"], random_state=42)

exported_pipeline = make_pipeline(
    MaxAbsScaler(),
    GradientBoostingClassifier(
        learning_rate=0.1, max_depth=7, n_estimators=100
    )
)
exported_pipeline.fit(training_features, training_target)
results = exported_pipeline.predict(testing_features)
```

## Best Practices

* Start with a small `generations` and `population_size` (e.g., 5 and 20) to get a quick baseline, then increase for better results.
* Set `max_time_mins` when running in CI or on shared resources to avoid unbounded runtimes.
* Use `n_jobs=-1` to parallelize pipeline evaluation across all available CPU cores.
* Use `periodic_checkpoint_folder` to save progress during long runs so you can resume or retrieve the best pipeline if the process is interrupted.
* Review the exported pipeline code before deploying -- it is plain scikit-learn and can be modified or integrated into your application directly.
* Set `random_state` for reproducible results.

## Conclusion

TPOT automates one of the most time-consuming parts of applied machine learning: selecting and tuning the right pipeline. By leveraging genetic programming over the scikit-learn ecosystem, it can discover competitive pipelines with minimal manual effort and export them as clean, standalone Python code.

Resources:

* [TPOT Documentation](http://epistasislab.github.io/tpot/)
* [TPOT on PyPI](https://pypi.org/project/TPOT/)
* [TPOT GitHub](https://github.com/EpistasisLab/tpot)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
