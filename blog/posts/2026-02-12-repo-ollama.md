---
title: "Ollama - Run Large Language Models Locally"
date: 2026-02-12T09:00:00+00:00
last_modified_at: 2026-02-12T09:00:00+00:00
topic_kind: "repo"
topic_id: "ollama/ollama"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - ollama
  - llm
  - local-inference
  - llama
  - self-hosted
  - python
excerpt: "A look at the ollama/ollama repository, a tool for downloading, running, and managing large language models locally on your own hardware."
header:
  overlay_image: /assets/images/2026-02-12-repo-ollama/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-02-12-repo-ollama/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

[Ollama](https://github.com/ollama/ollama) is an open-source tool that makes it straightforward to download, run, and interact with large language models on your local machine. It packages model weights, configuration, and a runtime into a single workflow, eliminating the need to manage complex dependencies or rely on external APIs. Whether you want to experiment with Llama 3, Mistral, Gemma, Phi, or dozens of other models, Ollama handles the setup so you can focus on building.

## Overview

The `ollama/ollama` repository is written primarily in Go and provides:

- A **CLI** for pulling, running, and managing models
- A **REST API** server that runs locally on port 11434
- A **Python library** (`ollama`) for programmatic access
- Support for **custom Modelfiles** to create and share model configurations
- Built-in **GPU acceleration** with automatic detection for NVIDIA and Apple Silicon

The repository has grown rapidly and supports a wide catalog of models including Llama 3, Mistral, Code Llama, Gemma, Phi-3, Qwen, and many more.

## Getting Started

### Installation

On macOS and Linux, install Ollama with a single command:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

On macOS, you can also download the desktop application from [ollama.com](https://ollama.com). On Windows, a native installer is available.

### Pulling and Running a Model

```bash
# Download and run Llama 3
ollama run llama3

# Pull a model without starting a conversation
ollama pull mistral

# List downloaded models
ollama list
```

### Python Client

Install the official Python library:

```bash
pip install ollama
```

## Core Concepts

### Chat Completions

The Python library mirrors the familiar chat completions pattern:

```python
import ollama

response = ollama.chat(
    model='llama3',
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Explain quantum computing in simple terms.'},
    ]
)
print(response['message']['content'])
```

### Text Generation

For simpler single-prompt generation, use `ollama.generate()`:

```python
import ollama

response = ollama.generate(
    model='llama3',
    prompt='Write a haiku about programming.'
)
print(response['response'])
```

### Streaming Responses

Both `chat` and `generate` support streaming for real-time output:

```python
import ollama

stream = ollama.chat(
    model='llama3',
    messages=[{'role': 'user', 'content': 'Tell me a short story.'}],
    stream=True,
)

for chunk in stream:
    print(chunk['message']['content'], end='', flush=True)
```

### Custom Modelfiles

Ollama supports Modelfiles for creating customized model configurations:

```dockerfile
FROM llama3
SYSTEM "You are a Python coding assistant. Always provide clear, well-commented code."
PARAMETER temperature 0.3
PARAMETER num_ctx 4096
```

Create and use the custom model:

```bash
ollama create python-helper -f Modelfile
ollama run python-helper
```

## Practical Examples

### Example 1: Building a Simple Q&A Script

```python
import ollama

def ask(question):
    response = ollama.chat(
        model='llama3',
        messages=[
            {'role': 'system', 'content': 'Answer concisely in 2-3 sentences.'},
            {'role': 'user', 'content': question},
        ]
    )
    return response['message']['content']

print(ask("What is the difference between TCP and UDP?"))
print(ask("How does garbage collection work in Python?"))
```

### Example 2: Using the REST API Directly

Ollama exposes a local REST API that any HTTP client can use:

```bash
# Generate a completion
curl http://localhost:11434/api/generate -d '{
  "model": "llama3",
  "prompt": "What is the capital of France?",
  "stream": false
}'

# Chat completion
curl http://localhost:11434/api/chat -d '{
  "model": "llama3",
  "messages": [{"role": "user", "content": "Hello!"}],
  "stream": false
}'
```

## Best Practices

- **Choose the right model size for your hardware.** Smaller quantized models (7B, 8B) run well on consumer hardware, while larger models (70B+) require significant RAM or GPU memory.
- **Use the system prompt** to control model behavior and keep responses focused.
- **Set `stream: true`** in interactive applications to provide immediate feedback to users.
- **Create custom Modelfiles** for recurring use cases to standardize system prompts and parameters across your team.

## Conclusion

Ollama simplifies the process of running LLMs locally, providing a polished CLI, a REST API, and client libraries for Python and JavaScript. The `ollama/ollama` repository is actively maintained and continues to add support for new models and features. For developers who need local inference without cloud dependencies, Ollama is an excellent choice.

For more details, visit the [Ollama GitHub repository](https://github.com/ollama/ollama).

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
