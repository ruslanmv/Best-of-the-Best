---
title: "Autofaiss: Automatically Build Optimal Faiss Indexes for Vector Search"
date: 2026-01-09T09:00:00+00:00
last_modified_at: 2026-01-09T09:00:00+00:00
topic_kind: "package"
topic_id: "autofaiss"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - vector-search
  - approximate-nearest-neighbor
  - faiss
  - embeddings
  - machine-learning
excerpt: "Autofaiss automatically selects the best Faiss index type and parameters for your embeddings, making it easy to build fast and memory-efficient approximate nearest neighbor search indexes."
header:
  overlay_image: /assets/images/2026-01-09-package-autofaiss/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-01-09-package-autofaiss/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Autofaiss is a library developed by Criteo that automatically builds optimal [Faiss](https://github.com/facebookresearch/faiss) indexes for approximate nearest neighbor (ANN) search. Faiss itself is a powerful library from Meta for similarity search, but choosing the right index type and tuning its parameters can be complex. Autofaiss removes that burden by analyzing your embeddings and automatically selecting the best index configuration given your constraints on memory usage and query speed.

This is valuable for anyone working with embedding-based retrieval systems, whether for semantic search, recommendation engines, or retrieval-augmented generation (RAG). Instead of manually experimenting with dozens of Faiss index types and parameters, Autofaiss handles the optimization for you.

In this guide, you will learn how to install Autofaiss, build an optimized index from NumPy embeddings, and use the resulting index for fast similarity search.

## Overview

Key features:

- **Automatic index selection**: Chooses the best Faiss index type (IVF, HNSW, OPQ, etc.) based on your data and constraints
- **Memory-aware optimization**: Respects a maximum memory budget you specify
- **Handles large datasets**: Can process embeddings stored on disk to handle datasets that do not fit in RAM
- **Simple API**: A single function call to go from raw embeddings to an optimized, ready-to-use index
- **CLI and Python API**: Usable both from the command line and as a Python library

Use cases:

- Semantic search and information retrieval
- Recommendation systems
- Image similarity search
- Retrieval-augmented generation (RAG) pipelines
- Deduplication of large embedding datasets

## Getting Started

Install Autofaiss using pip:

```bash
pip install autofaiss
```

Here is a complete working example that builds an index from NumPy embeddings:

```python
import numpy as np
from autofaiss import build_index

# Generate sample embeddings (10,000 vectors of dimension 128)
embeddings = np.random.rand(10000, 128).astype("float32")

# Build an optimized Faiss index
index, index_infos = build_index(
    embeddings=embeddings,
    save_on_disk=False,       # Return index in memory
    max_index_memory_usage="100MB",
    metric_type="ip"          # Inner product similarity
)

print(f"Index type: {index_infos.get('index_key', 'N/A')}")
print(f"Index size: {index.ntotal} vectors")
```

## Core Concepts

### The `build_index` Function

The `build_index` function is the primary entry point. It accepts embeddings and constraint parameters, then returns an optimized Faiss index:

```python
from autofaiss import build_index

index, index_infos = build_index(
    embeddings=embeddings,           # NumPy array or path to .npy file(s)
    save_on_disk=True,               # Save index to disk
    index_path="my_index.index",     # Output path for the index file
    index_infos_path="index_infos.json",  # Output path for index metadata
    max_index_memory_usage="4GB",    # Maximum RAM for the index
    max_index_query_time_ms=10,      # Target query latency in milliseconds
    metric_type="ip"                 # "ip" (inner product) or "l2" (Euclidean)
)
```

The function returns:
- `index`: A Faiss index object ready for querying
- `index_infos`: A dictionary with metadata about the chosen index configuration

### Querying the Index

Once built, the index is a standard Faiss index and can be queried directly:

```python
import numpy as np

# Query vector
query = np.random.rand(1, 128).astype("float32")

# Search for the 5 nearest neighbors
distances, indices = index.search(query, k=5)

print(f"Nearest neighbor indices: {indices[0]}")
print(f"Distances: {distances[0]}")
```

### Building from Files on Disk

For large datasets that do not fit in memory, you can pass a directory of `.npy` files:

```python
from autofaiss import build_index

# Embeddings are stored as .npy files in a directory
index, index_infos = build_index(
    embeddings="path/to/embeddings_dir",
    save_on_disk=True,
    index_path="large_index.index",
    max_index_memory_usage="16GB",
    metric_type="l2"
)
```

## Practical Examples

### Example 1: Building a Semantic Search Index

```python
import numpy as np
from autofaiss import build_index

# Suppose you have sentence embeddings from a model
# (In practice, these come from a sentence transformer or similar)
num_documents = 100000
embedding_dim = 384
embeddings = np.random.rand(num_documents, embedding_dim).astype("float32")

# Build an index optimized for low memory usage
index, index_infos = build_index(
    embeddings=embeddings,
    save_on_disk=True,
    index_path="semantic_search.index",
    index_infos_path="semantic_search_infos.json",
    max_index_memory_usage="256MB",
    metric_type="ip"
)

print(f"Chosen index type: {index_infos.get('index_key')}")

# Search for documents similar to a query
query_embedding = np.random.rand(1, embedding_dim).astype("float32")
distances, doc_indices = index.search(query_embedding, k=10)

print(f"Top 10 document indices: {doc_indices[0]}")
```

### Example 2: Using the Command-Line Interface

Autofaiss also provides a CLI for building indexes without writing Python code:

```bash
autofaiss build_index \
    --embeddings="path/to/embeddings" \
    --index_path="output.index" \
    --index_infos_path="output_infos.json" \
    --max_index_memory_usage="2GB" \
    --metric_type="l2"
```

This is useful for integrating index building into data pipelines or CI/CD workflows.

## Best Practices

- **Use float32 embeddings**: Autofaiss expects embeddings as `float32` NumPy arrays. Convert from other dtypes before building.
- **Set realistic memory constraints**: The `max_index_memory_usage` parameter drives index type selection. Tighter constraints lead to more compressed (and slightly less accurate) indexes.
- **Normalize embeddings for inner product**: If using `metric_type="ip"`, normalize your vectors to unit length so that inner product equals cosine similarity.
- **Save indexes to disk**: For production use, always set `save_on_disk=True` so you can reload the index without rebuilding.
- **Use the index metadata**: The `index_infos` dictionary contains the chosen index key and parameters, which is useful for documentation and reproducibility.

Common pitfalls:

- Passing embeddings with fewer than a few hundred vectors may result in suboptimal index choices, as Autofaiss is designed for larger datasets.
- Forgetting to cast embeddings to `float32` will cause errors.
- Very tight memory constraints on large datasets may result in significant accuracy loss.

## Conclusion

Autofaiss takes the guesswork out of building Faiss indexes by automatically selecting and tuning the best index configuration for your data and constraints. Whether you are building a semantic search engine, a recommendation system, or a RAG pipeline, Autofaiss lets you focus on your application logic rather than index engineering.

Resources:
- [GitHub - criteo/autofaiss](https://github.com/criteo/autofaiss)
- [Faiss Documentation](https://faiss.ai/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
