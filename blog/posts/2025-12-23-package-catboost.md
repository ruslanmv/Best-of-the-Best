---
title: "CatBoost: Gradient Boosting with Native Categorical Feature Support"
date: 2025-12-23T09:00:00+00:00
last_modified_at: 2025-12-23T09:00:00+00:00
topic_kind: "package"
topic_id: "catboost"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - catboost
  - machine-learning
  - gradient-boosting
  - data-science
  - python
  - classification
  - regression
excerpt: "A practical guide to CatBoost, Yandex's gradient boosting library that handles categorical features natively without manual encoding."
header:
  overlay_image: /assets/images/2025-12-23-package-catboost/header-data-science.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2025-12-23-package-catboost/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

CatBoost is an open-source gradient boosting library developed by Yandex. Its distinguishing feature is native support for categorical features -- it can process string and categorical columns directly without requiring manual one-hot encoding or label encoding. CatBoost also uses ordered boosting, a permutation-based technique that reduces prediction shift and overfitting. In this post, you will learn how to install CatBoost, train classifiers and regressors, handle categorical features natively, and tune key hyperparameters.

## Overview

CatBoost stands for "Categorical Boosting" and provides several advantages over other gradient boosting libraries:

- **Native categorical feature handling** -- pass categorical columns directly without preprocessing
- **Ordered boosting** -- reduces overfitting by using a permutation-driven approach to compute target statistics
- **GPU training support** -- accelerate training on NVIDIA GPUs with `task_type="GPU"`
- **Built-in overfitting detection** -- automatically stops training when validation metrics stop improving
- **Feature importance and model analysis** -- built-in methods for SHAP values, feature importance, and model visualization
- **Cross-platform support** -- works on Linux, macOS, and Windows

Common use cases include tabular data classification and regression, ranking tasks, recommendation systems, and any scenario involving datasets with many categorical features.

## Getting Started

Install CatBoost using pip:

```bash
pip install catboost
```

Here is a quick classification example using the Iris dataset:

```python
from catboost import CatBoostClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Load the Iris dataset
iris = load_iris()
X_train, X_test, y_train, y_test = train_test_split(
    iris.data, iris.target, test_size=0.2, random_state=42
)

# Train a CatBoost classifier
model = CatBoostClassifier(iterations=100, learning_rate=0.1, depth=6, verbose=0)
model.fit(X_train, y_train)

# Evaluate
predictions = model.predict(X_test)
print(f"Accuracy: {accuracy_score(y_test, predictions):.4f}")
```

## Core Concepts

### Native Categorical Feature Support

The key differentiator of CatBoost is that you can pass categorical features directly by specifying the `cat_features` parameter. CatBoost computes target statistics internally using ordered boosting:

```python
from catboost import CatBoostClassifier, Pool

# Sample data with categorical features
X = [
    ["sunny", "hot", 85],
    ["sunny", "hot", 90],
    ["overcast", "hot", 78],
    ["rain", "mild", 96],
    ["rain", "cool", 80],
    ["overcast", "cool", 65],
    ["sunny", "mild", 70],
    ["rain", "mild", 75],
]
y = [0, 0, 1, 1, 1, 1, 0, 1]

# Specify which columns are categorical (by index)
cat_features = [0, 1]

# Create a Pool object for efficient data handling
train_pool = Pool(X, y, cat_features=cat_features)

model = CatBoostClassifier(iterations=50, verbose=0)
model.fit(train_pool)

print(model.predict(["overcast", "mild", 72]))
```

### Regression

For regression tasks, use `CatBoostRegressor` with the California Housing dataset:

```python
from catboost import CatBoostRegressor
from sklearn.datasets import fetch_california_housing
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# Load dataset
housing = fetch_california_housing()
X_train, X_test, y_train, y_test = train_test_split(
    housing.data, housing.target, test_size=0.2, random_state=42
)

model = CatBoostRegressor(iterations=500, learning_rate=0.05, depth=8, verbose=0)
model.fit(X_train, y_train, eval_set=(X_test, y_test), early_stopping_rounds=50)

predictions = model.predict(X_test)
rmse = mean_squared_error(y_test, predictions, squared=False)
print(f"RMSE: {rmse:.4f}")
```

## Practical Examples

### Example 1: Feature Importance Analysis

CatBoost provides built-in feature importance methods to understand which features drive predictions:

```python
from catboost import CatBoostClassifier
from sklearn.datasets import load_iris

iris = load_iris()
model = CatBoostClassifier(iterations=100, verbose=0)
model.fit(iris.data, iris.target)

# Get feature importance scores
importance = model.get_feature_importance()
for name, score in zip(iris.feature_names, importance):
    print(f"{name}: {score:.2f}")
```

### Example 2: GPU Training and Hyperparameter Tuning

CatBoost supports GPU-accelerated training and provides a built-in grid search:

```python
from catboost import CatBoostClassifier, Pool
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split

iris = load_iris()
X_train, X_test, y_train, y_test = train_test_split(
    iris.data, iris.target, test_size=0.2, random_state=42
)

train_pool = Pool(X_train, y_train)
eval_pool = Pool(X_test, y_test)

model = CatBoostClassifier(verbose=0)

# Define a grid of hyperparameters
grid = {
    "iterations": [100, 200],
    "depth": [4, 6, 8],
    "learning_rate": [0.01, 0.05, 0.1],
}

grid_search_result = model.grid_search(grid, train_pool, verbose=0)
print("Best parameters:", grid_search_result["params"])
```

## Best Practices

- **Specify `cat_features` explicitly** -- always declare which columns are categorical so CatBoost can apply its ordered target encoding rather than treating them as numeric.
- **Use `Pool` objects** -- wrapping data in `Pool` improves memory efficiency and is required for some advanced features.
- **Enable early stopping** -- pass `eval_set` and `early_stopping_rounds` to prevent overfitting and reduce unnecessary training iterations.
- **Start with default hyperparameters** -- CatBoost defaults are well-tuned. Only customize after establishing a baseline.
- **Set `verbose=0` in production** -- suppress training output for cleaner logs.

## Conclusion

CatBoost is a high-performance gradient boosting library that excels when working with categorical features. Its ordered boosting approach, built-in overfitting detection, and GPU support make it a strong choice for tabular machine learning tasks. To learn more, consult the official documentation and experiment with your own datasets.

Resources:

- [CatBoost Official Documentation](https://catboost.ai/docs/)
- [CatBoost GitHub Repository](https://github.com/catboost/catboost)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
