---
title: "BERTScore for LLM Evaluation: When to Use It, Examples, and watsonx.ai Workflows"
date: 2026-01-07T09:00:00+00:00
last_modified_at: 2026-06-11T09:00:00+00:00
topic_kind: "package"
topic_id: "bert-score"
topic_version: 2
categories:
  - Engineering
  - AI
tags:
  - nlp
  - text-evaluation
  - bert
  - machine-learning
  - metrics
excerpt: "Learn how BERTScore evaluates generated text with contextual embeddings, when to use it instead of ROUGE, BLEU, or LLM-as-judge, and how to wire it into watsonx.ai evaluation workflows."
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

## Why BERTScore matters

If you have ever watched ROUGE give a near-zero score to a perfectly good summary because the model wrote "physicians" instead of "doctors", you understand the problem BERTScore solves. N-gram metrics reward surface overlap, not meaning, and punish exactly what modern LLMs are best at: saying the right thing in different words.

BERTScore, introduced by Zhang et al. at ICLR 2020, replaces exact string matching with similarity in embedding space. Every token in the candidate and the reference is encoded with a pre-trained transformer, then greedily matched against the most similar token on the other side by cosine similarity. Aggregating those matches yields precision, recall, and F1 that survive paraphrasing, synonyms, and reordering. The paper showed markedly better correlation with human judgment than BLEU and ROUGE; in my experience that holds for summarization and RAG answers too.

The practical upshot: BERTScore is the cheapest meaningful upgrade to a reference-based evaluation pipeline. It is deterministic, runs offline, costs nothing per call, and takes ten lines of code to adopt.

## Quick start

Install from PyPI:

```bash
pip install bert-score
```

Then score a candidate against a reference; `lang` picks a sensible default model (`roberta-large` for English):

```python
from bert_score import score

candidates = ["The physician recommended rest and plenty of fluids."]
references = ["The doctor advised the patient to rest and drink fluids."]

P, R, F1 = score(candidates, references, lang="en", verbose=True)

print(f"Precision: {P.item():.4f}")
print(f"Recall:    {R.item():.4f}")
print(f"F1:        {F1.item():.4f}")
```

The first call downloads the model from Hugging Face (about 1.4 GB for `roberta-large`). `P`, `R`, and `F1` are PyTorch tensors with one element per pair. ROUGE-L would rate this pair around 0.4 because few tokens overlap literally; BERTScore lands far higher because the sentences mean the same thing.

## Metrics and knobs that actually matter

### Precision, recall, F1

The three numbers answer different questions. **Precision**: is everything the model said grounded in the reference? Low precision suggests hallucinated or extraneous content. **Recall**: did the model cover everything the reference says? Low recall means incompleteness. **F1** is the harmonic mean and the number most people track, but keep the other two: for summarization I watch recall, for constrained tasks like answer extraction, precision.

### model_type

The English default is `roberta-large`, which is fine, but the maintainers' own correlation benchmarks put `microsoft/deberta-xlarge-mnli` at the top for agreement with human judgment. If you have the memory, pass `model_type="microsoft/deberta-xlarge-mnli"` to `score()` or `BERTScorer`. For other languages, pass `lang` and the package falls back to `bert-base-multilingual-cased`. Whatever you pick, pin it: scores from different models live on different scales and are not comparable.

### rescale_with_baseline

Raw BERTScore values cluster in a narrow band — typically 0.85 to 0.95 for English — because even unrelated sentences share a lot of embedding-space geometry. `rescale_with_baseline=True` linearly rescales against a precomputed random-pairing baseline so scores spread across a readable range. It changes nothing about ranking. I turn it on and leave it on, so historical scores stay comparable.

### idf weighting

With `idf=True`, frequent tokens ("the", "is", "of") are downweighted and content words dominate, with frequencies computed from your reference corpus. It helps on longer texts but ties scores to the IDF reference set — one more thing to keep fixed.

### BERTScorer for reuse

Calling `score()` repeatedly reloads the model each time; for any real pipeline, instantiate `BERTScorer` once:

```python
from bert_score import BERTScorer

scorer = BERTScorer(lang="en", rescale_with_baseline=True, idf=False)

P, R, F1 = scorer.score(
    ["The weather is pleasant today."],
    ["Today the weather is nice."],
)
print(f"F1: {F1.item():.4f}")
```

It takes the same knobs as the function (`model_type`, `num_layers`, `idf`, `rescale_with_baseline`, `batch_size`) and keeps the model in memory.

## A realistic evaluation workflow

Here is the shape of a real run: a batch of generated summaries scored against human references, with per-example results and a corpus aggregate to assert against in CI.

```python
from bert_score import BERTScorer

# Outputs from your summarization system
candidates = [
    "The central bank raised interest rates by half a point to fight inflation.",
    "Researchers found the new vaccine was 89 percent effective in trials.",
    "The company reported record quarterly revenue driven by cloud services.",
]

# Human-written references
references = [
    "To combat inflation, the central bank increased rates by 0.5 percentage points.",
    "Trial results showed the novel vaccine achieved 89% efficacy.",
    "Cloud growth pushed the firm to its highest quarterly revenue ever.",
]

scorer = BERTScorer(
    model_type="microsoft/deberta-xlarge-mnli",
    rescale_with_baseline=True,
    lang="en",
    batch_size=32,
)

P, R, F1 = scorer.score(candidates, references)

for i, (cand, f1) in enumerate(zip(candidates, F1.tolist())):
    flag = "  <-- review" if f1 < 0.55 else ""
    print(f"[{i}] F1={f1:.4f}{flag}  {cand[:60]}")

mean_f1 = F1.mean().item()
print(f"\nCorpus mean F1: {mean_f1:.4f}")

# CI gate
THRESHOLD = 0.55
assert mean_f1 >= THRESHOLD, f"Mean BERTScore F1 {mean_f1:.4f} below {THRESHOLD}"
```

Two habits make this useful. First, always inspect the worst-scoring examples by hand — the tail is where real regressions hide. Second, calibrate the threshold empirically: score known-good and known-bad batches and set the gate between the two distributions. A threshold copied from a blog post (including this one) means nothing for your model and domain.

## When to use it

- **Reference-based generation**: summarization, translation, paraphrasing — anywhere you have gold outputs and care about meaning over wording.
- **Regression testing LLM systems**: you changed a prompt or swapped a model and want a deterministic signal that quality did not drift.
- **Ranking prompt or model variants**: it orders candidates reliably even when absolute values are hard to interpret.
- **High-volume offline evaluation**: thousands of examples per run, where an LLM judge's price and nondeterminism would hurt.
- **As one signal among several**: paired with ROUGE plus spot-checked human review.

## When not to use it

- **No references exist.** BERTScore is strictly reference-based. For open-ended chat or production traffic without gold answers, use LLM-as-judge or humans.
- **Factuality is the question.** A summary that inverts a number or negates a claim can still score high — "rose" and "fell" sit close in embedding space. Use entailment-based factuality checks or RAGAS-style faithfulness metrics.
- **Format compliance.** Whether the model returned valid JSON is a job for assertions, not embeddings.
- **Cross-system leaderboards.** Unless everyone fixes the same model, layer, and baseline settings, numbers are not comparable.
- **Very short outputs.** Single words give the greedy matcher almost nothing to work with; exact match is more honest.

## Integration with IBM watsonx.ai

Most of my recent BERTScore use is regression-testing text generated by foundation models on watsonx.ai. The pattern: maintain a fixed evaluation set with curated references, generate candidates through the watsonx.ai inference API with the current prompt template and model, then score with a pinned `BERTScorer` configuration. Store scores alongside run metadata — model id, prompt version, generation parameters — so every prompt edit and model swap gets a before/after comparison instead of a gut feeling.

This matters on watsonx.ai because the platform makes it easy to swap a Granite, Llama, or Mistral model behind the same prompt. BERTScore answers "did that swap hurt my summaries?" deterministically, within minutes, at no per-token cost. The sketch below shows the wiring; credentials come only from the environment.

```python
import os
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference
from bert_score import BERTScorer

creds = Credentials(
    url=os.environ["WATSONX_URL"],
    api_key=os.environ["WATSONX_APIKEY"],
)
model = ModelInference(
    model_id="ibm/granite-3-8b-instruct",
    credentials=creds,
    project_id=os.environ["WATSONX_PROJECT_ID"],
)

inputs = ["Summarize: The central bank raised rates by 0.5 points to curb inflation."]
references = ["The central bank increased rates half a point to fight inflation."]

candidates = [model.generate_text(prompt=text) for text in inputs]

scorer = BERTScorer(lang="en", rescale_with_baseline=True)
_, _, F1 = scorer.score(candidates, references)
print(f"Mean F1: {F1.mean().item():.4f}")
```

In CI, that mean feeds the threshold assertion shown earlier; the gate runs on every prompt-template change and has caught more silent regressions than any other single check.

## Integration with IBM Watson Orchestrate

In IBM watsonx Orchestrate, BERTScore works best as a quality gate inside automated content workflows, not as something an end user sees. Picture a skill flow that drafts customer-facing emails or knowledge-base summaries: before the flow routes a draft onward, a custom skill backed by a small scoring service compares it against approved reference content. Drafts that clear the threshold continue automatically; the rest go to a human-review step.

The same idea applies to batch operations Orchestrate automates — regenerating hundreds of product descriptions after a source-data update. Scoring each regenerated text against its previously approved version flags items that drifted semantically, so reviewers read the 5 percent that changed meaning instead of everything. Keep the scorer behind an internal HTTP endpoint with a pinned configuration; Orchestrate calls it like any other tool, and the metric's determinism means the gate behaves identically across runs.

## Alternatives compared

| Metric | What it measures | Needs references? | Cost | Best for |
|---|---|---|---|---|
| BERTScore | Token-level semantic similarity via contextual embeddings | Yes | One-time model download; GPU recommended | Paraphrase-tolerant scoring of summaries, translations, RAG answers |
| BLEU | N-gram precision with brevity penalty | Yes | Negligible CPU | Machine translation benchmarks, legacy comparability |
| ROUGE | N-gram and longest-common-subsequence overlap | Yes | Negligible CPU | Summarization surface overlap, quick sanity checks |
| METEOR | Unigram matching with stemming and synonyms | Yes | Low CPU | Translation evaluation when BLEU is too rigid |
| RAGAS | RAG-specific: faithfulness, answer relevance, context precision | Partially (LLM-judged) | Per-call LLM cost | End-to-end retrieval-augmented pipelines |
| LLM-as-judge | Whatever your rubric says | No | Per-call API cost; nondeterministic | Open-ended quality, no-reference settings |

My honest take: BLEU and ROUGE are not obsolete, just narrow. They are free, instant, and fine as a tripwire — if ROUGE-L collapses between runs, something broke. But fluent models routinely produce excellent text that n-gram overlap rates as mediocre, so I no longer treat them as quality metrics. METEOR sits awkwardly in the middle and is rarely worth the setup anymore.

The real decision in 2026 is BERTScore versus LLM-as-judge. The judge is flexible and needs no references, but it costs money every run, drifts when the judge model updates, and adds variance. BERTScore is rigid but free, fast, and reproducible — properties that matter enormously in CI. RAGAS is not a competitor; it measures faithfulness to retrieved context and runs happily alongside BERTScore on RAG systems.

## Limitations

Be clear-eyed about the trade-offs. **Compute**: scoring is a forward pass of a large transformer per text; on CPU a few thousand pairs takes long enough to annoy you, so plan for a GPU in CI or batch aggressively. **Comparability**: scores are only meaningful relative to a fixed model, layer (`num_layers`), and baseline configuration — change any of those and historical numbers are void, so pin them like dependencies. **Factuality blindness**: semantic similarity is not truth; numerically wrong or subtly negated statements can score nearly as well as correct ones. **Short-text instability**: with a handful of tokens, one greedy match swings the score wildly. It also inherits its model's domain gaps — clinical or legal jargon matches less reliably than newsroom English.

## Final recommendation

If you ship anything that generates text against known-good references — summarization, translation, templated content, RAG answers with curated golden sets — you should be running BERTScore in CI today. It is the best signal-to-effort ratio in reference-based evaluation: ten minutes to integrate, zero marginal cost, deterministic, and far better aligned with human judgment than the n-gram metrics it replaces. Use `microsoft/deberta-xlarge-mnli` if you have the VRAM, turn on `rescale_with_baseline`, pin the configuration, and calibrate thresholds on your own data.

Do not adopt it as a lone arbiter of quality. It belongs in a stack: n-gram tripwires below it, a sampled LLM judge and factuality checks above it, human review at the top. Teams on watsonx.ai get a particularly clean fit — fixed evaluation set, generate, score, gate — and that loop pays for itself the first time it catches a prompt change that quietly degraded output.

## References

- [bert_score on GitHub (Tiiiger/bert_score)](https://github.com/Tiiiger/bert_score)
- [BERTScore: Evaluating Text Generation with BERT — ICLR 2020 paper](https://arxiv.org/abs/1904.09675)
- [bert-score on PyPI](https://pypi.org/project/bert-score/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
