---
title: "Ollama: Run LLMs Locally — Setup, Python Examples, and Production Considerations"
date: 2025-12-27T09:00:00+00:00
last_modified_at: 2026-06-11T09:00:00+00:00
topic_kind: "package"
topic_id: "ollama"
topic_version: 2
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
excerpt: "How Ollama makes local LLMs practical: setup, the Python client and OpenAI-compatible API, when local inference beats hosted models, and how it pairs with watsonx.ai in hybrid architectures."
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

## Why Ollama matters

Before Ollama, running an open-weight model on your own machine meant compiling llama.cpp, hunting down the right GGUF file on Hugging Face, guessing at quantization levels, and writing your own server wrapper. Ollama collapsed all of that into two commands. That is the whole pitch, and it is enough.

Three reasons it earns a permanent place on my development machines:

**Privacy.** Prompts and documents never leave localhost. If you are prototyping against contracts, medical notes, source code under NDA, or anything your legal team would wince at, local inference removes an entire category of approval meetings.

**Cost.** A hosted API bills per token for every iteration of a prompt you are still debugging, and the ratio of throwaway calls to useful calls during development is brutal. With Ollama, that experimentation costs electricity and nothing else.

**Offline, fast dev loops.** No rate limits, no network latency, no API key rotation, works on a plane. When the model is one process away, you iterate differently — more recklessly, in a good way.

What Ollama abstracts away is the unglamorous middle layer: model file management, quantization selection, GPU/CPU layer offloading, prompt templating per model family, and keeping a server process alive. You stop thinking about inference plumbing and start thinking about your application.

## How it works

Ollama is a local server written in Go that wraps llama.cpp as its inference engine. When you install it, you get a background service exposing a REST API on `http://localhost:11434`, plus a CLI that talks to that service.

Models are distributed in GGUF format — pre-quantized weights (typically 4-bit, with other levels available) that trade a small amount of quality for dramatically lower memory requirements. A 7–8B parameter model at Q4 quantization fits in roughly 5 GB, which is why these models run on ordinary laptops at all.

`ollama pull` fetches models from the Ollama library using a layered, content-addressed format much like Docker images: weights, parameters, and the chat template are separate layers, so variants of the same base model share storage. Each model ships with its correct prompt template baked in — applying the wrong chat template silently degrades output quality, and Ollama makes that mistake hard to make. You can also define custom model variants through a Modelfile, a Dockerfile-like text format that sets the system prompt and sampling parameters on top of an existing base model.

At request time, Ollama loads the model into RAM or VRAM (offloading as many layers to the GPU as fit), serves the request, and keeps the model warm for a few minutes before unloading it. Everything — CLI, Python client, third-party tools — speaks to the same REST API.

## Quick start

Install the runtime from [ollama.com](https://ollama.com/) (macOS and Windows installers, or a one-line script on Linux). Then pull and chat with a model:

```bash
ollama pull llama3.2
ollama run llama3.2
```

`ollama run` drops you into an interactive REPL — useful for a smoke test, but the real work happens through the API. Install the official Python client:

```bash
pip install ollama
```

The chat API mirrors the messages format every modern LLM API uses:

```python
import ollama

response = ollama.chat(
    model="llama3.2",
    messages=[
        {"role": "system", "content": "You are a concise technical assistant."},
        {"role": "user", "content": "Explain GGUF quantization in three sentences."},
    ],
)
print(response["message"]["content"])
```

For anything interactive, stream the tokens. Local models on modest hardware generate at reading speed, so streaming is the difference between an app that feels alive and one that appears frozen:

```python
import ollama

stream = ollama.chat(
    model="llama3.2",
    messages=[{"role": "user", "content": "Write a short docstring for a retry decorator."}],
    stream=True,
)

for chunk in stream:
    print(chunk["message"]["content"], end="", flush=True)
print()
```

The package also exposes `ollama.generate()` for single-shot completion without chat history, and `ollama.Client(host=...)` when the server runs on another machine — say, a GPU box on your LAN.

## The OpenAI-compatible endpoint

Ollama ships an OpenAI-compatible API at `/v1`, which is documented, supported behavior — not a hack. This is quietly its most useful feature: any codebase, framework, or tool built against the OpenAI SDK can target a local model by changing two constructor arguments.

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",  # required by the SDK, ignored by Ollama
)

response = client.chat.completions.create(
    model="llama3.2",
    messages=[{"role": "user", "content": "Summarize what a vector index does."}],
)
print(response.choices[0].message.content)
```

In practice this means your application code stays provider-agnostic. I structure projects so the base URL and model name come from configuration; the same code runs against Ollama in development and a hosted endpoint in production.

## When to use it

- **Prototyping LLM features** before committing to a hosted provider or model.
- **Sensitive-data workloads** — PII redaction, document triage, log summarization — where data residency rules make hosted APIs a non-starter.
- **High-volume, low-stakes batch tasks**: classification, tagging, embedding-adjacent preprocessing where an 8B model is plenty and per-token billing would be silly.
- **Internal tools and personal assistants** serving one user or a small team.
- **CI and integration tests** that need a real model behind an OpenAI-shaped endpoint without spending money or leaking fixtures.

## When not to use it

Skip Ollama when:

- **You need high-throughput, multi-user serving.** Ollama parallelizes a handful of requests per loaded model, but it has no continuous batching, no paged attention, no tensor parallelism across GPUs. Past a few concurrent users, latency degrades fast.
- **You need frontier-quality reasoning.** The best open-weight models are genuinely good, but for the hardest reasoning, agentic, and long-context tasks, hosted frontier models still win. A quantized 8B model will not match them, and pretending otherwise produces disappointing products.
- **You have strict SLAs.** A single process on a single machine has no story for failover, autoscaling, or uptime guarantees. If a contract specifies availability, you need real serving infrastructure or a managed platform.

## Production considerations

If you do put Ollama behind something user-facing, go in with clear eyes.

**Concurrency.** Ollama can load multiple models and handle a configurable number of parallel requests (controlled by environment variables like `OLLAMA_NUM_PARALLEL` and `OLLAMA_MAX_LOADED_MODELS`), but it is not a batching inference server. vLLM with continuous batching will deliver many times the aggregate throughput on identical hardware. Ollama optimizes for one developer's latency; vLLM optimizes for a fleet's throughput. Pick accordingly.

**VRAM and quantization.** Budget roughly: 8B at Q4 needs ~5–6 GB, 13–14B needs ~10 GB, 70B at Q4 needs ~40+ GB — plus headroom for the KV cache, which grows with context length. If the model does not fully fit in VRAM, layers spill to CPU and throughput falls off a cliff. Lower quantization (Q3, Q2) buys memory at a real quality cost; for most work, Q4 variants are the sweet spot, and Q8 rarely justifies double the memory.

**Licensing.** "Open weights" is not one license. Llama models carry Meta's community license with an acceptable-use policy and a clause covering very large deployments; Mistral and Qwen releases are mostly Apache 2.0; Gemma has its own terms. Check the actual license of the actual model before it ships in a commercial product — this is a five-minute task that prevents a very bad meeting.

## Integration with IBM watsonx.ai

The pattern I have settled on for enterprise work is hybrid: Ollama in the inner loop, watsonx.ai in production. They solve different problems and complement each other well.

During development, local models running under Ollama let teams iterate on prompts, RAG pipelines, and evaluation harnesses without sending a single byte of client data off the workstation. This is especially valuable for preprocessing stages — chunking strategies, PII scrubbing, document classification — where the data is at its most sensitive and the model quality bar is modest. IBM's Granite models are published in the Ollama library, which makes this unusually clean: you can develop locally against the same model family that watsonx.ai serves in production, so prompt behavior carries over instead of resetting when you switch environments.

In production, watsonx.ai brings what a local runtime structurally cannot: governed, audited inference with model lifecycle management, usage tracking, guardrails, and enterprise SLAs. My routing rule is simple — route by data sensitivity and quality requirement. Sensitive preprocessing and bulk low-stakes inference can stay local or on self-managed infrastructure; anything customer-facing, compliance-relevant, or quality-critical goes through the governed platform. The OpenAI-compatible endpoint makes this routing a configuration concern rather than a code rewrite.

## Integration with IBM Watson Orchestrate

A similar division of labor applies to agents. Ollama is a good substrate for experimenting with agent tooling locally — function calling against local models, testing tool schemas, validating conversation flows — cheaply and privately. Watson Orchestrate operates at the other end of the spectrum: governed, enterprise-grade automation that connects agents to business systems with access control and auditability. Prototype the agent's skills and prompts locally, then implement the production automation in Orchestrate where IT can actually govern it. Trying to make a laptop-grade runtime do enterprise orchestration is a mistake in both directions.

## Alternatives compared

| Tool | Audience | Throughput | API | Best for |
|---|---|---|---|---|
| **Ollama** | Developers | Single-user / small team | REST + OpenAI-compatible + Python/JS clients | Fastest path from zero to local inference |
| **llama.cpp** (direct) | Tinkerers, embedders | Single-user, maximally tunable | C API, CLI, minimal server | Squeezing every token/s out of specific hardware |
| **vLLM** | ML platform teams | High — continuous batching, multi-GPU | OpenAI-compatible | Production serving at scale |
| **LM Studio** | Desktop / GUI users | Single-user | GUI + OpenAI-compatible local server | Non-CLI users exploring models |
| **GPT4All** | Desktop privacy-focused users | Single-user | GUI + local API | Simple offline chat with local documents |

My honest read: Ollama wins on developer experience and it is not close. The Docker-like model management, the correct-by-default prompt templates, and the OpenAI-compatible endpoint mean a competent developer goes from nothing to a working integration in under ten minutes. Using llama.cpp directly buys you fine-grained control and slightly better performance tuning, but you pay for it in setup time and maintenance — worthwhile for embedded targets or exotic hardware, not for everyday development.

vLLM is the correct answer to a different question. If you are serving many concurrent users on dedicated GPUs, continuous batching is not optional, and vLLM (or an equivalent like TGI) is the production tool. I have seen teams try to scale Ollama into that role; it ends with sad latency graphs. The two tools coexist naturally: Ollama on laptops, vLLM in the cluster, the same OpenAI-style client code pointed at either.

LM Studio and GPT4All are fine products for people who want a GUI, and LM Studio's model discovery is genuinely pleasant. But for anyone scripting, building, or automating, a daemon plus a CLI plus a clean API beats a desktop app every time.

## Limitations

- No continuous batching or multi-GPU tensor parallelism — throughput ceilings arrive quickly.
- Quantized models lose measurable quality on hard reasoning tasks versus full-precision hosted equivalents.
- Model availability lags the bleeding edge; brand-new architectures need llama.cpp support first.
- Operational tooling (metrics, auth, multi-tenancy) is essentially absent — by design. Put a gateway in front of it if you expose it beyond localhost.
- Context length is constrained by KV-cache memory; long-context use on consumer hardware requires care.

## Final recommendation

Install it. Even if every production token you serve comes from a hosted platform, Ollama pays for itself as a development tool within a week: free iteration, private experimentation, and an OpenAI-compatible endpoint that keeps your code portable. Treat it as what it is — the best local LLM developer experience available — and pair it with vLLM or a governed platform like watsonx.ai when concurrency, quality ceilings, or compliance demand more. The teams that get this right are not choosing between local and hosted; they are routing between them deliberately.

## References

- [Ollama on GitHub](https://github.com/ollama/ollama)
- [Ollama official site and model library](https://ollama.com/)
- [Ollama Python client on GitHub](https://github.com/ollama/ollama-python)
- [ollama on PyPI](https://pypi.org/project/ollama/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
