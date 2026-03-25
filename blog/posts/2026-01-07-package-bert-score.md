---
title: "BERTScore: Evaluating Text Generation with Contextual Embeddings"
date: 2026-01-07T09:00:00+00:00
last_modified_at: 2026-01-07T09:00:00+00:00
topic_kind: "package"
topic_id: "bert-score"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - nlp
  - text-evaluation
  - bert
  - machine-learning
  - metrics
excerpt: "BERTScore leverages BERT contextual embeddings to evaluate text generation quality, providing precision, recall, and F1 scores that correlate better with human judgment than traditional n-gram metrics."
header:
  overlay_image: /assets/images/2026-01-07-package-bert-score/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-01-07-package-bert-score/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

BERTScore is an automatic evaluation metric for text generation that computes token-level similarity between candidate and reference sentences using contextual embeddings from pre-trained BERT models. Unlike traditional metrics such as BLEU or ROUGE that rely on exact n-gram matching, BERTScore captures semantic similarity, making it more robust to paraphrasing and synonyms.

This matters because evaluating the quality of generated text is a fundamental challenge in NLP. Machine translation, summarization, and dialogue systems all benefit from metrics that align with human judgment, and BERTScore has been shown to correlate more strongly with human evaluations than surface-level metrics.

In this guide, you will learn how to install BERTScore, compute precision, recall, and F1 scores for generated text, and apply it to practical evaluation scenarios.

## Overview

BERTScore works by computing pairwise cosine similarities between tokens in the candidate and reference sentences using contextual embeddings. It then uses greedy matching to produce three scores:

- **Precision**: How much of the candidate is supported by the reference.
- **Recall**: How much of the reference is covered by the candidate.
- **F1**: The harmonic mean of precision and recall.

Key features include:

- Support for over 100 pre-trained models (RoBERTa, DeBERTa, etc.)
- Multi-language support via multilingual models
- Optional importance weighting using inverse document frequency (IDF)
- Command-line interface for batch evaluation
- Baseline rescaling for more interpretable scores

## Getting Started

Install BERTScore using pip:

```bash
pip install bert-score
```

Here is a complete working example:

```python
from bert_score import score

# Candidate sentences (generated text)
cands = [
    "The cat sat on the mat.",
    "It is raining outside today."
]

# Reference sentences (ground truth)
refs = [
    "The cat is sitting on the mat.",
    "Today it is raining outdoors."
]

# Compute BERTScore
P, R, F1 = score(cands, refs, lang="en", verbose=True)

print(f"Precision: {P.tolist()}")
print(f"Recall:    {R.tolist()}")
print(f"F1:        {F1.tolist()}")
```

## Core Concepts

### The `score` Function

The primary interface is the `score` function, which accepts lists of candidate and reference strings:

```python
from bert_score import score

P, R, F1 = score(
    cands,           # List of candidate sentences
    refs,            # List of reference sentences
    lang="en",       # Language (used to select default model)
    model_type=None, # Specify a model explicitly, e.g., "roberta-large"
    num_layers=None, # Which layer to use for embeddings
    verbose=False,   # Print progress
    idf=False,       # Use IDF weighting
    rescale_with_baseline=False  # Apply baseline rescaling
)
```

The return values `P`, `R`, and `F1` are PyTorch tensors, one score per sentence pair.

### The `BERTScorer` Class

For repeated evaluations, use the `BERTScorer` class to avoid reloading the model:

```python
from bert_score import BERTScorer

scorer = BERTScorer(lang="en", rescale_with_baseline=True)

P, R, F1 = scorer.score(
    ["The weather is nice today."],
    ["Today the weather is pleasant."]
)

print(f"F1: {F1.item():.4f}")
```

## Practical Examples

### Example 1: Evaluating Machine Translation Output

```python
from bert_score import score

# Machine translation outputs
translations = [
    "The house is big and beautiful.",
    "She goes to the school every day.",
    "We had dinner at the restaurant last night."
]

# Human reference translations
references = [
    "The house is large and lovely.",
    "She attends school daily.",
    "Last night, we dined at the restaurant."
]

P, R, F1 = score(translations, references, lang="en", rescale_with_baseline=True)

for i, (p, r, f) in enumerate(zip(P, R, F1)):
    print(f"Sentence {i+1} - P: {p:.4f}, R: {r:.4f}, F1: {f:.4f}")
```

### Example 2: Comparing Summarization Models

```python
from bert_score import score

source_text = "The original article about climate change..."

summary_a = ["Global temperatures have risen significantly over the past century due to human activities."]
summary_b = ["Climate change is caused by greenhouse gas emissions from industrial processes."]
reference = ["Human-caused greenhouse gas emissions have led to significant global temperature increases."]

_, _, f1_a = score(summary_a, reference, lang="en")
_, _, f1_b = score(summary_b, reference, lang="en")

print(f"Summary A F1: {f1_a.item():.4f}")
print(f"Summary B F1: {f1_b.item():.4f}")
print(f"Better summary: {'A' if f1_a > f1_b else 'B'}")
```

## Best Practices

- **Choose the right model**: Use `roberta-large` for English evaluations for best correlation with human judgment. Use multilingual models for non-English text.
- **Enable baseline rescaling**: Set `rescale_with_baseline=True` to get scores that are more interpretable and spread across the 0-1 range.
- **Use IDF weighting**: When evaluating longer texts, IDF weighting can help downweight common tokens and emphasize content words.
- **Reuse the scorer**: When evaluating many sentence pairs, instantiate `BERTScorer` once rather than calling `score()` repeatedly to avoid reloading the model.
- **Batch processing**: Pass all candidates and references at once rather than scoring one pair at a time.

Common pitfalls:

- BERTScore requires a GPU for efficient computation on large datasets. CPU evaluation works but is slow.
- Scores are not directly comparable across different models or layer selections.
- Very short sentences may produce unreliable scores.

## Conclusion

BERTScore provides a semantically meaningful evaluation metric for text generation that significantly improves upon traditional n-gram-based approaches. By leveraging contextual embeddings, it captures paraphrasing, synonymy, and sentence structure in ways that better align with human judgment.

Resources:
- [GitHub - Tiiiger/bert_score](https://github.com/Tiiiger/bert_score)
- [BERTScore Paper (ICLR 2020)](https://arxiv.org/abs/1904.09675)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
