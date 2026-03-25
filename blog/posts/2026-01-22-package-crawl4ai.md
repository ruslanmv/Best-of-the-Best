---
title: "Crawl4AI: Open-Source Web Crawling for LLMs and AI Pipelines"
date: 2026-01-22T09:00:00+00:00
last_modified_at: 2026-01-22T09:00:00+00:00
topic_kind: "package"
topic_id: "Crawl4AI"
topic_version: 1
categories:
  - Engineering
  - AI
tags:
  - python
  - package
  - pypi
  - web-crawling
  - llm
  - data-extraction
  - async
  - rag
excerpt: "Crawl4AI is an open-source, async-first web crawler built for feeding clean, structured content to LLMs and AI applications."
header:
  overlay_image: /assets/images/2026-01-22-package-crawl4ai/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/2026-01-22-package-crawl4ai/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

## Introduction

Crawl4AI is an open-source Python library purpose-built for web crawling in AI and LLM workflows. Unlike general-purpose scrapers, Crawl4AI focuses on extracting clean, structured content -- Markdown, JSON, or plain text -- from web pages so that it can be fed directly into language models, RAG pipelines, or knowledge bases.

The library is async-first, built on top of Playwright for browser automation, and requires no API keys or external services.

## Overview

Key features:

* Async architecture using `AsyncWebCrawler` for high-throughput crawling
* Automatic conversion of HTML to clean Markdown
* Structured data extraction using CSS selectors, LLM-based strategies, or JsonCssExtractionStrategy
* JavaScript execution support via Playwright
* Screenshot and PDF capture
* Session management for multi-step crawling (login, pagination)
* Chunking strategies for splitting content into LLM-friendly segments

Use cases:

* Building RAG (Retrieval-Augmented Generation) pipelines
* Collecting training data for LLMs
* Monitoring and extracting structured data from websites
* Converting web content to Markdown for knowledge bases

## Getting Started

Installation:

```
pip install crawl4ai
```

After installation, run the post-install setup to download browser binaries:

```
crawl4ai-setup
```

Basic example -- crawl a single page and get Markdown output:

```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://example.com")
        print(result.markdown)

asyncio.run(main())
```

## Core Concepts

### AsyncWebCrawler

The main entry point is `AsyncWebCrawler`, used as an async context manager. It manages a Playwright browser instance and handles page loading, JavaScript execution, and content extraction.

```python
from crawl4ai import AsyncWebCrawler

async with AsyncWebCrawler(verbose=True) as crawler:
    result = await crawler.arun(url="https://example.com")
```

### CrawlResult

The `arun()` method returns a `CrawlResult` object with the following key attributes:

* `result.html` -- the raw HTML of the page
* `result.markdown` -- cleaned Markdown content
* `result.cleaned_html` -- sanitized HTML
* `result.success` -- boolean indicating if the crawl succeeded
* `result.extracted_content` -- structured data if an extraction strategy was used

### Extraction Strategies

Crawl4AI supports multiple strategies for extracting structured data:

* **JsonCssExtractionStrategy** -- extract data using CSS selectors and a schema definition
* **LLMExtractionStrategy** -- use an LLM to extract structured data from page content

## Practical Examples

### Example 1: Basic Page Crawl with Markdown Output

```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url="https://example.com")

        if result.success:
            print(f"Page title extracted successfully")
            print(f"Markdown length: {len(result.markdown)} characters")
            print(result.markdown[:500])
        else:
            print(f"Crawl failed: {result.error_message}")

asyncio.run(main())
```

### Example 2: Structured Data Extraction with CSS Selectors

```python
import asyncio
import json
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

async def main():
    schema = {
        "name": "Article Links",
        "baseSelector": "a",
        "fields": [
            {"name": "text", "selector": "", "type": "text"},
            {"name": "href", "selector": "", "type": "attribute", "attribute": "href"},
        ],
    }

    extraction_strategy = JsonCssExtractionStrategy(schema)

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.com",
            extraction_strategy=extraction_strategy,
        )

        if result.success and result.extracted_content:
            data = json.loads(result.extracted_content)
            for item in data[:5]:
                print(f"Link: {item.get('text', '')} -> {item.get('href', '')}")

asyncio.run(main())
```

### Example 3: Executing JavaScript Before Extraction

```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://example.com",
            js_code="window.scrollTo(0, document.body.scrollHeight);",
            wait_for="css:.dynamic-content",
        )

        if result.success:
            print(f"Content after JS execution: {len(result.markdown)} chars")

asyncio.run(main())
```

### Example 4: Crawling Multiple Pages

```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3",
    ]

    async with AsyncWebCrawler() as crawler:
        for url in urls:
            result = await crawler.arun(url=url)
            if result.success:
                print(f"{url}: {len(result.markdown)} chars of Markdown")

asyncio.run(main())
```

## Best Practices

* Always use `AsyncWebCrawler` as an async context manager (`async with`) to ensure browser resources are properly cleaned up.
* Run `crawl4ai-setup` after installation to ensure Playwright browser binaries are available.
* Use `JsonCssExtractionStrategy` when the page structure is known and consistent -- it is faster and more reliable than LLM-based extraction.
* Set `wait_for` when crawling JavaScript-heavy pages to ensure dynamic content has loaded before extraction.
* Respect website terms of service and robots.txt. Add delays between requests with `delay_before_return_html` to avoid overwhelming servers.
* For production workloads, handle `result.success` checks and implement retry logic for transient failures.

## Conclusion

Crawl4AI fills a specific niche in the AI toolchain: converting live web content into clean, structured formats that LLMs can consume directly. Its async-first design, built-in Markdown conversion, and flexible extraction strategies make it a practical choice for RAG pipelines, dataset construction, and web monitoring tasks.

Resources:

* [Crawl4AI Documentation](https://docs.crawl4ai.com/)
* [Crawl4AI GitHub](https://github.com/unclecode/crawl4ai)
* [Crawl4AI on PyPI](https://pypi.org/project/crawl4ai/)

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
