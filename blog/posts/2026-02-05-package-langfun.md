---
title: "Langfun - Building Natural Language-Powered Functions with LLMs"
date: 2026-02-05T09:00:00+00:00
last_modified_at: 2026-02-05T09:00:00+00:00
topic_kind: "package"
topic_id: "langfun"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - langfun
  - llm
  - prompt-engineering
  - google
  - natural-language-functions
  - python
excerpt: "Explore Langfun, Google's Python library for composing and calling LLM-powered functions using natural language prompt templates and structured output."
header:
  overlay_image: /assets/images/2026-02-05-package-langfun/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-02-05-package-langfun/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Langfun is a Google-developed Python library that enables developers to build natural language-powered functions using large language models (LLMs). Rather than treating LLMs as simple text-in, text-out systems, Langfun provides a structured programming model where prompt templates, variable bindings, and typed outputs come together to create composable, reusable LLM-based components.

## Overview

Langfun bridges the gap between traditional programming and LLM-based generation. Its core philosophy is that natural language prompts are functions: they accept inputs, process them through an LLM, and return structured outputs. The library supports multiple LLM backends including Google Gemini, OpenAI, and others, and integrates tightly with PyGlove for object-oriented symbolic programming.

Key capabilities include:

- **Prompt templates** with `{{variable}}` syntax for parameterized generation
- **Structured output** parsing that maps LLM responses to Python objects
- **LangFunc** for defining reusable natural language functions
- **`lf.query()`** for one-shot structured queries against LLMs
- **Multi-modal support** including text and image inputs

## Getting Started

Install Langfun from PyPI:

```bash
pip install langfun
```

Import the library and configure an LLM backend:

```python
import langfun as lf

# Configure a language model (e.g., Google Gemini)
lm = lf.llms.GenAI(model="gemini-1.5-flash", api_key="YOUR_API_KEY")
```

## Core Concepts

### Prompt Templates

Langfun uses `{{variable}}` syntax to define parameterized prompt templates. Templates are first-class objects that can be composed and reused:

```python
import langfun as lf

# Define a prompt template
prompt = lf.LangFunc("Translate the following to {{language}}: {{text}}")

# Render the prompt with variable bindings
result = prompt(language="French", text="Hello, world!", lm=lm)
print(result)
```

### Structured Queries with `lf.query()`

One of Langfun's most powerful features is `lf.query()`, which allows you to request structured Python objects directly from an LLM:

```python
import langfun as lf

# Query the LLM and get a Python list back
result = lf.query(
    "List 5 popular programming languages.",
    list[str],
    lm=lm,
)
print(result)
# Output: ['Python', 'JavaScript', 'Java', 'C++', 'TypeScript']
```

### Dataclass-Based Structured Output

You can define structured schemas using Python dataclasses and have the LLM populate them:

```python
import dataclasses
import langfun as lf

@dataclasses.dataclass
class Country:
    name: str
    capital: str
    population: int
    language: str

result = lf.query(
    "Tell me about France.",
    Country,
    lm=lm,
)
print(result.name)       # France
print(result.capital)    # Paris
print(result.language)   # French
```

## Practical Examples

### Example 1: Sentiment Classification

```python
import langfun as lf
import enum

class Sentiment(enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

sentiment = lf.query(
    "Classify the sentiment of: '{{text}}'",
    Sentiment,
    text="I absolutely love this product, it changed my life!",
    lm=lm,
)
print(sentiment)  # Sentiment.POSITIVE
```

### Example 2: Composing Multiple LangFuncs

```python
import langfun as lf

summarize = lf.LangFunc(
    "Summarize the following text in one sentence: {{text}}"
)

translate = lf.LangFunc(
    "Translate the following to {{language}}: {{text}}"
)

# Chain operations: summarize first, then translate
article = "Langfun is a Python library developed by Google for building..."
summary = summarize(text=article, lm=lm)
translated = translate(text=str(summary), language="Spanish", lm=lm)
print(translated)
```

## Best Practices

- **Use structured output types** whenever possible. Requesting `list[str]` or a dataclass is more reliable than parsing free-form text.
- **Keep prompt templates focused.** Smaller, composable templates are easier to debug and reuse than monolithic prompts.
- **Handle LLM errors gracefully.** Wrap calls in try/except blocks since LLM responses can occasionally fail to parse into the requested type.
- **Pin your LLM model version** in production to ensure consistent behavior across deployments.

## Conclusion

Langfun provides an elegant programming model for building LLM-powered applications. By treating prompts as functions with typed inputs and outputs, it brings software engineering rigor to prompt engineering. Whether you need simple text generation, structured data extraction, or complex multi-step LLM workflows, Langfun offers a clean and composable approach.

For more information, visit the [Langfun GitHub repository](https://github.com/google/langfun).

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
