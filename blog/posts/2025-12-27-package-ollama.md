---
title: "Ollama: Run Large Language Models Locally"
date: 2025-12-27T09:00:00+00:00
last_modified_at: 2025-12-27T09:00:00+00:00
topic_kind: "package"
topic_id: "ollama"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - ollama
  - llm
  - local-inference
  - python
  - llama
  - mistral
  - self-hosted
excerpt: "A practical guide to Ollama, the tool for running open-source large language models like Llama, Mistral, and Gemma locally on your own machine."
header:
  overlay_image: /assets/images/2025-12-27-package-ollama/header-data-science.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2025-12-27-package-ollama/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Ollama is a tool for running open-source large language models locally on your own hardware. It handles model downloading, quantization, and serving behind a simple interface, letting you run models like Llama 3, Mistral, Gemma, Phi, and many others without sending data to external APIs. Ollama provides both a command-line interface and a Python library for interacting with models programmatically. In this post, you will learn how to install Ollama, pull and run models, use the Python API for chat and text generation, and manage your local model library.

## Overview

Ollama simplifies local LLM deployment with:

- **One-command model setup** -- download and run models with `ollama pull` and `ollama run`
- **Wide model support** -- Llama 3, Mistral, Gemma, Phi, Code Llama, Qwen, and dozens more from the Ollama model library
- **Python client library** -- `ollama.chat()`, `ollama.generate()`, and `ollama.list()` for programmatic access
- **Streaming responses** -- stream tokens as they are generated for real-time output
- **REST API** -- a local HTTP server at `http://localhost:11434` compatible with the OpenAI API format
- **Custom Modelfiles** -- create customized model configurations with system prompts, parameters, and adapter layers
- **Cross-platform** -- runs on macOS, Linux, and Windows

Common use cases include private AI assistants, offline code generation, document analysis without data leaving your machine, and prototyping LLM applications locally before deploying to production.

## Getting Started

First, install the Ollama application from [ollama.com](https://ollama.com/). Then install the Python client:

```bash
pip install ollama
```

Pull a model and verify it is available:

```bash
ollama pull llama3.2
ollama list
```

Here is a minimal Python example using the chat API:

```python
import ollama

response = ollama.chat(
    model="llama3.2",
    messages=[
        {"role": "user", "content": "Explain what a REST API is in two sentences."}
    ],
)
print(response["message"]["content"])
```

## Core Concepts

### Chat API

The `ollama.chat()` function supports multi-turn conversations with a list of messages:

```python
import ollama

messages = [
    {"role": "system", "content": "You are a helpful coding assistant."},
    {"role": "user", "content": "Write a Python function to reverse a string."},
]

response = ollama.chat(model="llama3.2", messages=messages)
print(response["message"]["content"])

# Continue the conversation
messages.append(response["message"])
messages.append({"role": "user", "content": "Now add type hints to that function."})

response = ollama.chat(model="llama3.2", messages=messages)
print(response["message"]["content"])
```

### Generate API

For single-prompt text generation without chat history, use `ollama.generate()`:

```python
import ollama

response = ollama.generate(
    model="llama3.2",
    prompt="List three benefits of test-driven development.",
)
print(response["response"])
```

### Streaming Responses

Both `chat` and `generate` support streaming for real-time token output:

```python
import ollama

stream = ollama.chat(
    model="llama3.2",
    messages=[{"role": "user", "content": "Write a haiku about programming."}],
    stream=True,
)

for chunk in stream:
    print(chunk["message"]["content"], end="", flush=True)
print()
```

## Practical Examples

### Example 1: Managing Models

Ollama provides functions to list, pull, and inspect models from Python:

```python
import ollama

# List all locally available models
models = ollama.list()
for model in models["models"]:
    print(f"{model['name']} - {model['size'] / 1e9:.1f} GB")

# Show model details
info = ollama.show("llama3.2")
print(f"Family: {info['details']['family']}")
print(f"Parameters: {info['details']['parameter_size']}")
print(f"Quantization: {info['details']['quantization_level']}")
```

### Example 2: Structured Output with JSON

You can instruct models to return structured JSON output:

```python
import ollama
import json

response = ollama.chat(
    model="llama3.2",
    messages=[
        {
            "role": "system",
            "content": "You are a data extraction assistant. Always respond with valid JSON.",
        },
        {
            "role": "user",
            "content": "Extract the name, age, and city from this text: 'Alice is 30 years old and lives in Seattle.'",
        },
    ],
    format="json",
)

data = json.loads(response["message"]["content"])
print(data)
```

## Best Practices

- **Choose the right model size for your hardware** -- smaller quantized models (7B Q4) run well on 8 GB RAM, while larger models (70B) require 48+ GB.
- **Use streaming for interactive applications** -- streaming provides a better user experience by displaying tokens as they arrive.
- **Set system prompts for consistent behavior** -- use the system role in messages to define the model's persona and output format.
- **Use the `format` parameter for structured output** -- pass `format="json"` to get parseable JSON responses.
- **Keep models updated** -- run `ollama pull model_name` periodically to get updated quantizations and fixes.
- **Monitor resource usage** -- local LLMs are memory-intensive. Use `ollama ps` to check which models are loaded and their memory consumption.

## Conclusion

Ollama makes it straightforward to run open-source large language models on your own machine. With its simple CLI, Python client library, and broad model support, you can build private AI applications without relying on external API services. Whether you need a local coding assistant, a private chatbot, or a prototyping environment for LLM applications, Ollama provides the infrastructure to get started quickly.

Resources:

- [Ollama Official Website](https://ollama.com/)
- [Ollama Python Library on GitHub](https://github.com/ollama/ollama-python)
- [Ollama Model Library](https://ollama.com/library)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
