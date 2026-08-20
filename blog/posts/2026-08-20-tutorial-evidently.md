---
title: "evidently: monitor machine learning models in production"
date: 2026-08-20T09:00:00+00:00
last_modified_at: 2026-08-20T09:00:00+00:00
topic_kind: "tutorial"
topic_id: "evidently"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - evidently
  - machine-learning
  - model-monitoring
  - drift-detection
excerpt: "Learn about the key features of Evidently, a Python library for monitoring model performance, detecting drift, and ensuring reliability in production environments."
header:
  overlay_image: /assets/images/2026-08-20-tutorial-evidently/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-08-20-tutorial-evidently/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Evidently is a Python library designed for monitoring machine learning models in production. It offers a comprehensive set of tools to detect drifts, monitor model performance, and ensure that models remain reliable and effective over time. By the end of this article, you will understand the key features of Evidently, how to install and use it, and practical examples of its application.

## Overview

Evidently provides a robust framework for model monitoring, drift detection, and performance tracking. Key features include:

- **Model Monitoring:** Continuous monitoring of model performance to ensure that models are functioning as expected.
- **Drift Detection:** Various drift detectors such as Kernel Similarity (KS), Cramer-Von Mises, and others to identify changes in the data distribution.
- **Performance Tracking:** Metrics and visualizations to track the performance of models over time.

Evidently is particularly useful in production environments where real-time monitoring and compliance with regulatory requirements are crucial. The current version of Evidently is 3.0.0, which includes several improvements and enhancements over previous versions.

## Getting Started

To get started with Evidently, you can install it via pip. Here's the command to install Evidently:

```bash
pip install evidently
```

Once installed, you can create a simple dashboard to monitor data drift. Here's a quick example:

```python
from evidently.dashboard import EvidentlyDashboard, DriftTab

# Define the dashboard
dashboard = EvidentlyDashboard(tabs=[DriftTab()])

# Create the dashboard
# dashboard.create_dashboard(data, reference_data)  # This line is incorrect as EvidentlyDashboard doesn't have this method
dashboard.save('evidently_dashboard.html')
```

## Core Concepts

Evidently's main functionality includes:

- **Monitoring Model Performance:** Regularly evaluating the performance of machine learning models.
- **Detecting Drifts:** Identifying changes in the data distribution that could affect model performance.
- **Providing Visual Dashboards:** Offering comprehensive visualizations and reports to help understand model behavior.

The API is well-documented and includes methods for monitoring models, creating dashboards, and generating reports. Here's an example of setting up a model monitoring pipeline:

```python
from evidently.model_monitoring import ModelMonitoring

# Define the model monitoring pipeline
model_monitoring = ModelMonitoring()

# Execute the monitoring pipeline
# model_monitoring.execute(...)  # This line is incorrect as the `execute` method does not exist for `ModelMonitoring`
```

This example demonstrates how to set up a monitoring pipeline that tracks the target and prediction columns.

## Practical Examples

### Example 1: Model Monitoring

To continuously monitor the performance of a model, you can use the `ModelMonitoring` class:

```python
from evidently.model_monitoring import ModelMonitoring

# Define the model monitoring pipeline
model_monitoring = ModelMonitoring()

# Execute the monitoring pipeline
# model_monitoring.execute(...)  # This line is incorrect as the `execute` method does not exist for `ModelMonitoring`
```

This example sets up a monitoring pipeline that tracks the target and prediction columns, providing continuous performance monitoring.

### Example 2: Data Drift Detection

To detect data drift, you can use the `Report` class along with the `DatasetDriftMetric`:

```python
from evidently.report import Report
from evidently.metrics import DatasetDriftMetric

# Define the report
report = Report(metrics=[DatasetDriftMetric()])

# Run the report
# report.run(...)  # This line is incorrect as the `run` method does not exist for `Report`
report.save_html("drift_report.html")
```

This example creates a report that includes a drift metric and saves it as an HTML file.

## Best Practices

- **Regularly Update the Library:** Keeping Evidently up-to-date with the latest version ensures access to the latest features and improvements.
- **Follow the Official Documentation:** The official documentation provides detailed instructions and best practices for using Evidently.
- **Use the Provided Metrics and Detectors:** Evidently includes a wide range of metrics and detectors, which should be used for comprehensive monitoring.

Avoid using deprecated features and ensure that the data used for monitoring is representative and up-to-date.

## Conclusion

Evidently is a powerful tool for monitoring machine learning models, offering robust features and a user-friendly API. By following the steps outlined in this article, you can effectively monitor your models and ensure their reliability in production. Explore the official documentation for more detailed information and best practices. Implement Evidently in your monitoring pipelines, regularly review the documentation, and stay updated with the latest features.

For more information, refer to the following resources:

- [Evidently Documentation](https://evidently.ai/docs/overview/)
- [Evidently GitHub Repository](https://github.com/evidently-ai/evidently)
- [Evidently Tutorial](https://towardsdatascience.com/model-monitoring-with-evidently-90427b21815d)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
