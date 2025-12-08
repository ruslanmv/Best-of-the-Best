#!/usr/bin/env python3
"""
scripts/finder.py - PRODUCTION v3.1 BLOG-ENHANCED (LOW-RESOURCE FRIENDLY)

Deep Web Documentation & README Finder with:
- ✅ FIXED: URL extraction from search results
- ✅ FIXED: Code extraction using BOTH markdown AND HTML
- ✅ ENHANCED: Detailed logging for debugging
- ✅ ENHANCED: Better search result parsing
- ✅ BLOG MODE: README first (PyPI/GitHub), then deep web pages with content snapshots
- ✅ LOW-RESOURCE MODE: Tuned for small local LLMs (e.g. 3B) and ~5GB RAM

🎯 FIXES & FEATURES:
  1. Robust URL extraction from formatted search results
  2. HTML + Markdown code extraction (not just markdown)
  3. Detailed logging showing exactly what was retrieved
  4. Better deduplication of URLs
  5. Blog-friendly output:
     - PyPI/GitHub README (when resolvable from topic)
     - Deep search pages with both URLs and content snippets
  6. Low-resource controls:
     - Fewer pages, fewer workers, shorter snippets by default
     - Environment tunables for CrewAI + small context models
"""

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from urllib.parse import urlparse
import sys

# -----------------------------------------------------------------------------
# Import from scripts/search.py
# -----------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import search  # type: ignore
except ImportError:
    ROOT_DIR = SCRIPT_DIR.parent
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    import scripts.search as search  # type: ignore

from search import (  # type: ignore
    search_web_impl,
    scrape_webpage_impl,
    CodeDetector,
    validate_url,
    rate_limiter,
    scrape_readme_smart,  # ⬅️ PyPI/GitHub README
)

# CrewAI tool decorator
try:
    from crewai.tools import tool  # type: ignore
    CREWAI_AVAILABLE = True
except ImportError:
    try:
        from crewai_tools import tool  # type: ignore
        CREWAI_AVAILABLE = True
    except ImportError:
        CREWAI_AVAILABLE = False

        def tool(func):
            return func

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION (LOW-RESOURCE AWARE)
# ============================================================================

LOW_RESOURCE_MODE = os.getenv("FINDER_LOW_RESOURCE", "").lower() in {
    "1", "true", "yes", "on"
}

# Defaults are smaller when LOW_RESOURCE_MODE is enabled
MAX_PAGES_TO_VISIT = int(os.getenv(
    "FINDER_MAX_PAGES",
    "5" if LOW_RESOURCE_MODE else "10",
))
MAX_PARALLEL_WORKERS = int(os.getenv(
    "FINDER_WORKERS",
    "2" if LOW_RESOURCE_MODE else "4",
))
PAGE_SCRAPE_TIMEOUT = int(os.getenv(
    "FINDER_PAGE_TIMEOUT",
    "20" if LOW_RESOURCE_MODE else "30",
))
TOTAL_SEARCH_TIMEOUT = int(os.getenv(
    "FINDER_TOTAL_TIMEOUT",
    "90" if LOW_RESOURCE_MODE else "120",
))
MIN_CODE_BLOCKS_TARGET = int(os.getenv(
    "FINDER_MIN_CODE",
    "2" if LOW_RESOURCE_MODE else "3",
))

# How many characters of page content to keep per source
SNIPPET_CHARS = int(os.getenv(
    "FINDER_SNIPPET_CHARS",
    "1200" if LOW_RESOURCE_MODE else "3000",
))

# How many examples to show in the final report (for small-context LLMs)
MAX_PYTHON_EXAMPLES = int(os.getenv(
    "FINDER_MAX_PY_EXAMPLES",
    "3" if LOW_RESOURCE_MODE else "5",
))
MAX_BASH_EXAMPLES = int(os.getenv(
    "FINDER_MAX_BASH_EXAMPLES",
    "2" if LOW_RESOURCE_MODE else "3",
))

# Extended strategies
SEARCH_STRATEGIES = [
    "{topic} python tutorial",
    "{topic} code examples",
    "{topic} quickstart guide",
    "how to use {topic} python",
    "{topic} github source code",
]

# ============================================================================
# HELPER: Infer probable package name(s) from a topic string
# ============================================================================


def _infer_package_candidates_from_topic(topic: str) -> List[str]:
    """
    Given a natural-language topic like:
        'xgboost python tutorial'
        'pandas dataframe guide'
    infer likely Python package name candidates.
    """
    tokens = re.findall(r"[A-Za-z0-9_\-]+", topic)
    ignore = {
        "python",
        "tutorial",
        "guide",
        "quickstart",
        "quick",
        "start",
        "docs",
        "documentation",
        "examples",
        "example",
        "how",
        "to",
        "library",
        "package",
        "intro",
        "introduction",
        "blog",
        "article",
        "post",
    }
    candidates: List[str] = []

    for t in tokens:
        low = t.lower()
        if low in ignore:
            continue
        if low not in candidates:
            candidates.append(low)

    return candidates


# ============================================================================
# HELPER: Lightweight public HTTP URL check (for search results)
# ============================================================================


def _is_public_http_url(url: str) -> bool:
    """
    Lightweight check for URLs extracted from LLM-formatted search results.

    - Allows any HTTP/HTTPS URL
    - Rejects localhost / private IP ranges
    - Full SSRF allowlist is enforced later in search.fetch_url()/validate_url
    """
    try:
        url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            return False

        private_patterns = [
            r"^localhost$",
            r"^127\.",
            r"^10\.",
            r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
            r"^192\.168\.",
            r"^169\.254\.",
        ]
        for pat in private_patterns:
            if re.match(pat, hostname):
                return False

        return True
    except Exception:
        return False


# ============================================================================
# ENHANCED URL EXTRACTOR
# ============================================================================


class URLExtractor:
    """
    FIXED: Robust URL extraction from search_web_impl() formatted results.
    Uses a lightweight public-URL check for flexibility on search results,
    while keeping strict SSRF checks for actual fetching.
    """

    @staticmethod
    def extract_urls_from_search_results(result_text: str) -> List[Dict[str, str]]:
        """
        Extract URLs from search results with multiple strategies

        Handles:
        1. "**URL:** https://..." format
        2. Markdown links [title](url)
        3. Raw URLs in text
        """
        urls: List[Dict[str, str]] = []
        seen_urls = set()

        # Strategy 1: Extract from "**URL:** https://..." lines
        url_pattern = r"\*\*URL:\*\*\s*(https?://[^\s]+)"
        for match in re.finditer(url_pattern, result_text):
            url = match.group(1).strip()
            # Clean trailing punctuation
            url = re.sub(r"[.,;!?)\]]+$", "", url)

            if url not in seen_urls and _is_public_http_url(url):
                urls.append(
                    {
                        "url": url,
                        "title": "Search Result",
                        "source": "formatted_url_line",
                    }
                )
                seen_urls.add(url)

        # Strategy 2: Extract from Markdown links [title](url)
        md_pattern = r"\[([^\]]+)\]\((https?://[^)]+)\)"
        for match in re.finditer(md_pattern, result_text):
            title = match.group(1).strip()
            url = match.group(2).strip()
            url = re.sub(r"[.,;!?)\]]+$", "", url)

            if url not in seen_urls and _is_public_http_url(url):
                urls.append(
                    {
                        "url": url,
                        "title": title,
                        "source": "markdown_link",
                    }
                )
                seen_urls.add(url)

        # Strategy 3: Extract raw URLs (fallback for any missed ones)
        raw_pattern = r"(?:^|\s)(https?://[^\s\)\]>,]+)"
        for match in re.finditer(raw_pattern, result_text, re.MULTILINE):
            url = match.group(1).strip()
            url = re.sub(r"[.,;!?)\]]+$", "", url)

            if url not in seen_urls and _is_public_http_url(url):
                urls.append(
                    {
                        "url": url,
                        "title": "Search Result",
                        "source": "raw_url",
                    }
                )
                seen_urls.add(url)

        return urls


# ============================================================================
# ENHANCED CODE EXTRACTOR
# ============================================================================


class EnhancedCodeExtractor:
    """
    FIXED: Extract code from BOTH HTML and Markdown
    """

    @staticmethod
    def extract_all_code(content: str, url: str = "") -> List[Dict[str, Any]]:
        """
        Extract code blocks using multiple methods

        Args:
            content: Content from scrape_webpage_impl (could be markdown with HTML blocks)
            url: Source URL for logging

        Returns:
            List of code blocks
        """
        all_blocks: List[Dict[str, Any]] = []
        seen_code = set()

        # Method 1: Extract from markdown fences (```lang ... ```)
        md_blocks = CodeDetector.extract_from_markdown(content)
        logger.info(f"  📝 Markdown extraction: {len(md_blocks)} blocks")

        for block in md_blocks:
            code_text = (block.get("code") or "").strip()
            if not code_text:
                continue
            code_hash = hash(code_text)
            if code_hash not in seen_code:
                all_blocks.append(block)
                seen_code.add(code_hash)

        # Method 2: Try HTML extraction if content looks like HTML-ish
        if "<div" in content or "<pre" in content or "highlight" in content:
            try:
                from bs4 import BeautifulSoup

                soup = BeautifulSoup(content, "html.parser")
                html_blocks = CodeDetector.extract_from_html(soup)
                logger.info(f"  🔍 HTML extraction: {len(html_blocks)} blocks")

                for block in html_blocks:
                    code_text = (block.get("code") or "").strip()
                    if not code_text:
                        continue
                    code_hash = hash(code_text)
                    if code_hash not in seen_code:
                        all_blocks.append(block)
                        seen_code.add(code_hash)
            except Exception as e:
                logger.debug(f"  ⚠️ HTML parsing failed: {e}")

        logger.info(f"  ✅ Total unique blocks: {len(all_blocks)}")
        return all_blocks


# ============================================================================
# CORE: DEEP PAGE SCRAPER (ENHANCED, BLOG-FRIENDLY, LOW-RESOURCE)
# ============================================================================


class DeepFinder:
    """
    Enhanced documentation finder with detailed logging and better extraction.
    Blog-friendly: keeps per-page content snippets, not just URLs and code.
    Low-resource friendly: fewer pages, capped snippet sizes, capped examples.
    """

    def __init__(self, topic: str, max_pages: int = MAX_PAGES_TO_VISIT):
        self.topic = topic
        self.max_pages = max_pages
        self.visited_urls = set()
        self.all_code_blocks: List[Dict[str, Any]] = []
        self.all_sources: List[Dict[str, Any]] = []
        self.total_pages_scraped = 0
        self.successful_scrapes = 0

    def search_and_scrape(self) -> Tuple[bool, str]:
        logger.info(f"🚀 Starting deep search for: {self.topic!r}")
        start_time = time.time()

        # 1. Initial Search
        logger.info("📍 PHASE 1: Initial search")
        urls = self._get_search_results(
            f"{self.topic} python tutorial documentation"
        )
        logger.info(f"  → Found {len(urls)} URLs after initial search")

        # 2. Aggressive Retry Strategy
        if len(urls) < 3:
            logger.info(
                f"📍 PHASE 2: Extended search (found only {len(urls)} URLs initially)"
            )
            for i, strat in enumerate(SEARCH_STRATEGIES, 1):
                if len(urls) >= self.max_pages:
                    break

                query = strat.format(topic=self.topic)
                logger.info(f"  Strategy {i}/{len(SEARCH_STRATEGIES)}: {query}")
                new_urls = self._get_search_results(query)

                # Add unique URLs
                existing = {u["url"] for u in urls}
                before_count = len(urls)
                for nu in new_urls:
                    if nu["url"] not in existing:
                        urls.append(nu)
                        existing.add(nu["url"])

                added = len(urls) - before_count
                logger.info(f"    → Added {added} new URLs (total: {len(urls)})")

                if len(urls) >= self.max_pages:
                    break

        if not urls:
            logger.warning("❌ No URLs found after all search strategies")
            return False, self._format_failure_report()

        logger.info(f"📋 Final URL count: {len(urls)} sources to visit")

        # 3. Visit pages in parallel
        logger.info(
            f"📍 PHASE 3: Scraping {min(len(urls), self.max_pages)} pages"
        )
        self._visit_pages_parallel(urls[: self.max_pages])

        # 4. Final Fallback: GitHub
        if not self.all_code_blocks:
            logger.info("📍 PHASE 4: GitHub fallback search")
            github_urls = self._get_search_results(
                f"{self.topic} github source code"
            )
            logger.info(f"  → Found {len(github_urls)} GitHub URLs")
            self._visit_pages_parallel(github_urls[:2])

        elapsed = time.time() - start_time
        logger.info(f"✅ Deep search complete in {elapsed:.1f}s")
        logger.info("  📊 Final stats:")
        logger.info(f"    - Pages visited: {self.total_pages_scraped}")
        logger.info(f"    - Successful scrapes: {self.successful_scrapes}")
        logger.info(f"    - Total code blocks: {len(self.all_code_blocks)}")

        # 5. Return Report (even if 0 code blocks, pages can still be useful)
        if len(self.all_code_blocks) >= MIN_CODE_BLOCKS_TARGET:
            return True, self._format_success_report()
        elif len(self.all_code_blocks) > 0:
            return True, self._format_partial_report()
        else:
            # Even on "failure", we still include whatever sources were scraped
            return False, self._format_failure_report()

    # ------------------------------------------------------------------ #
    # ENHANCED: Search with better URL extraction and logging
    # ------------------------------------------------------------------ #
    def _get_search_results(self, query: str) -> List[Dict[str, str]]:
        """
        ENHANCED: Better URL extraction and detailed logging
        """
        logger.info(f"🔍 Searching: {query}...")
        try:
            result_text = search_web_impl(query)

            # Log the raw result (truncated for readability)
            result_preview = result_text[:500].replace("\n", " ")
            logger.debug(f"  📥 Search result preview: {result_preview}...")

            # Use enhanced URL extractor
            urls = URLExtractor.extract_urls_from_search_results(result_text)

            # Detailed logging of extracted URLs
            if urls:
                logger.info(f"  📊 Extracted {len(urls)} URLs:")
                for i, url_info in enumerate(urls[:5], 1):  # Show first 5
                    url = url_info["url"]
                    source = url_info["source"]
                    logger.info(f"    {i}. [{source}] {url[:80]}...")
                if len(urls) > 5:
                    logger.info(f"    ... and {len(urls) - 5} more")
            else:
                logger.warning(
                    "  ⚠️ No valid URLs extracted from search results"
                )
                logger.debug(f"  Raw search result:\n{result_text[:1000]}")

            return urls

        except Exception as e:
            logger.error(f"  ❌ Search failed: {e}")
            return []

    # ------------------------------------------------------------------ #
    # ENHANCED: Page scraping with detailed logging
    # ------------------------------------------------------------------ #
    def _visit_pages_parallel(self, search_results: List[Dict[str, str]]) -> None:
        logger.info(f"🌐 Visiting {len(search_results)} pages in parallel...")

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
            futures = {
                executor.submit(self._scrape_single_page, result): result
                for result in search_results
            }

            try:
                for future in as_completed(futures, timeout=TOTAL_SEARCH_TIMEOUT):
                    try:
                        success = future.result(timeout=PAGE_SCRAPE_TIMEOUT)
                        if success:
                            self.successful_scrapes += 1
                    except Exception as e:
                        result = futures[future]
                        logger.debug(
                            f"  ❌ Task error for {result['url']}: {e}"
                        )
            except FuturesTimeout:
                logger.warning("⏱️  Total search timeout reached")
                for f in futures:
                    f.cancel()

    def _scrape_single_page(self, result_info: Dict[str, str]) -> bool:
        """
        ENHANCED: Better code extraction with detailed logging
        AND always keeps page content (even if no code is found),
        making the result more useful for blog/article generation.
        """
        url = result_info["url"]
        if url in self.visited_urls:
            return False

        self.visited_urls.add(url)
        self.total_pages_scraped += 1

        logger.info(f"📄 [{self.total_pages_scraped}] Scraping: {url[:70]}...")

        try:
            rate_limiter.wait_if_needed()

            # Get content (LLM-friendly, already formatted by scrape_webpage_impl)
            content = scrape_webpage_impl(url)

            if not content or len(content) < 200:
                logger.info(
                    f"  ⚠️ Content too short ({len(content) if content else 0} chars)"
                )
                # Even if short, keep a minimal snapshot
                self.all_sources.append(
                    {
                        "url": url,
                        "title": result_info.get("title", "Unknown"),
                        "code_blocks": 0,
                        "content_snippet": (content or "")[:SNIPPET_CHARS],
                    }
                )
                return False

            logger.info(f"  📥 Retrieved {len(content):,} characters")

            # Use enhanced extractor for BOTH markdown AND HTML
            code_blocks = EnhancedCodeExtractor.extract_all_code(content, url)

            if code_blocks:
                logger.info(f"  ✅ Found {len(code_blocks)} code blocks")

                # Log code block details
                python_count = sum(
                    1
                    for b in code_blocks
                    if "python" in (b.get("language", "") or "").lower()
                )
                bash_count = sum(
                    1
                    for b in code_blocks
                    if b.get("language") in ["bash", "console", "shell", "sh"]
                )
                other_count = len(code_blocks) - python_count - bash_count

                logger.info(
                    f"    → Python: {python_count}, Bash: {bash_count}, Other: {other_count}"
                )

                for block in code_blocks:
                    block["source_url"] = url
                    block["source_title"] = result_info.get("title", "Unknown")
                    self.all_code_blocks.append(block)
            else:
                logger.info("  ℹ️ No code blocks found")

            # ALWAYS keep a page snapshot, even with zero code blocks
            self.all_sources.append(
                {
                    "url": url,
                    "title": result_info.get("title", "Unknown"),
                    "code_blocks": len(code_blocks),
                    # Store a truncated snapshot of the page content for blog context
                    "content_snippet": content[:SNIPPET_CHARS],
                }
            )

            # Treat as a "successful scrape" if we got non-trivial content,
            # regardless of whether code was present.
            return True

        except Exception as e:
            logger.warning(f"  ❌ Error scraping: {e}")
            return False

    # ------------------------------------------------------------------ #
    # Report formatting (BLOG-FRIENDLY, SMALL-CONTEXT FRIENDLY)
    # ------------------------------------------------------------------ #
    def _format_success_report_old(self) -> str:
        output: List[str] = []
        output.append(f"# 🎯 Deep Search Results: {self.topic}")
        output.append("=" * 70)
        output.append(
            f"**Status:** ✅ SUCCESS - Found {len(self.all_code_blocks)} code blocks"
        )
        output.append(f"**Pages Visited:** {self.total_pages_scraped}")
        output.append(f"**Successful Scrapes:** {self.successful_scrapes}")
        output.append("")

        python_blocks = [
            b
            for b in self.all_code_blocks
            if "python" in (b.get("language", "") or "").lower()
        ]
        bash_blocks = [
            b
            for b in self.all_code_blocks
            if b.get("language") in ["bash", "sh", "shell", "console"]
        ]

        output.append("## 📊 Summary")
        output.append(f"- Python Examples: {len(python_blocks)}")
        output.append(f"- Setup Commands: {len(bash_blocks)}")
        output.append(f"- Total Code Blocks: {len(self.all_code_blocks)}")
        output.append("")

        output.append("## 📚 Sources (with code counts)")
        for i, source in enumerate(self.all_sources, 1):
            url = source["url"]
            blocks = source["code_blocks"]
            output.append(f"{i}. {url} - {blocks} code blocks")
        output.append("")

        # Page content snapshots to help blog generation (truncated)
        output.append("## 📄 Page Snapshots (Content for Blog Writing)")
        for i, source in enumerate(self.all_sources, 1):
            title = source.get("title", "Unknown")
            url = source["url"]
            snippet = source.get("content_snippet", "") or ""
            output.append(f"\n### {i}. {title}\n")
            output.append(f"**URL:** {url}\n")
            if snippet:
                output.append("```text")
                output.append(snippet)
                output.append("```")
            else:
                output.append(
                    "_No preview content captured for this page._"
                )
        output.append("")

        # Limit number of examples to keep context small
        if python_blocks:
            output.append("## 🐍 Python Code Examples")
            for i, block in enumerate(python_blocks[:MAX_PYTHON_EXAMPLES], 1):
                output.append(
                    f"### Example {i} - From: {block.get('source_url', 'Unknown')}"
                )
                output.append(f"```python\n{block['code']}\n```")
                output.append("")

        if bash_blocks:
            output.append("## 📦 Installation / Setup")
            for i, block in enumerate(bash_blocks[:MAX_BASH_EXAMPLES], 1):
                output.append(f"### Setup {i}")
                output.append(f"```bash\n{block['code']}\n```")
                output.append("")

        return "\n".join(output)

    def _format_success_report(self) -> str:
        """Format successful deep search results with sources sorted by code count"""
        output: List[str] = []
        output.append(f"# 🎯 Deep Search Results: {self.topic}")
        output.append("=" * 70)
        output.append(
            f"**Status:** ✅ SUCCESS - Found {len(self.all_code_blocks)} code blocks"
        )
        output.append(f"**Pages Visited:** {self.total_pages_scraped}")
        output.append(f"**Successful Scrapes:** {self.successful_scrapes}")
        output.append("")

        python_blocks = [
            b
            for b in self.all_code_blocks
            if "python" in (b.get("language", "") or "").lower()
        ]
        bash_blocks = [
            b
            for b in self.all_code_blocks
            if b.get("language") in ["bash", "sh", "shell", "console"]
        ]

        output.append("## 📊 Summary")
        output.append(f"- Python Examples: {len(python_blocks)}")
        output.append(f"- Setup Commands: {len(bash_blocks)}")
        output.append(f"- Total Code Blocks: {len(self.all_code_blocks)}")
        output.append("")

        # ✨ NEW: Sort sources by code count (most code first)
        output.append("## 📚 Sources (sorted by code count - best first)")
        sorted_sources = sorted(
            self.all_sources,
            key=lambda x: x["code_blocks"],
            reverse=True  # Descending: most code first
        )
        
        for i, source in enumerate(sorted_sources, 1):
            url = source["url"]
            blocks = source["code_blocks"]
            
            # ✨ NEW: Add visual indicators
            if blocks > 10:
                indicator = "🎯"  # Excellent source
            elif blocks > 0:
                indicator = "✓"   # Has code
            else:
                indicator = "✗"   # No code or failed
            
            output.append(f"{i}. {indicator} {url} - {blocks} code blocks")
        output.append("")

        # ✨ NEW: Page snapshots in same sorted order
        output.append("## 📄 Page Snapshots (Content for Blog Writing)")
        for i, source in enumerate(sorted_sources, 1):
            title = source.get("title", "Search Result")
            url = source["url"]
            snippet = source.get("content_snippet", "") or ""
            
            output.append(f"\n### {i}. {title}\n")
            output.append(f"**URL:** {url}\n")
            
            if snippet:
                output.append("```text")
                output.append(snippet)
                output.append("```")
            else:
                output.append("_No preview content captured for this page._")
        output.append("")

        # Show code examples (limit to keep context manageable)
        if python_blocks:
            output.append("## 🐍 Python Code Examples")
            for i, block in enumerate(python_blocks[:MAX_PYTHON_EXAMPLES], 1):
                output.append(
                    f"### Example {i} - From: {block.get('source_url', 'Unknown')}"
                )
                output.append(f"```python\n{block['code']}\n```")
                output.append("")

        if bash_blocks:
            output.append("## 📦 Installation / Setup")
            for i, block in enumerate(bash_blocks[:MAX_BASH_EXAMPLES], 1):
                output.append(f"### Setup {i}")
                output.append(f"```bash\n{block['code']}\n```")
                output.append("")

        return "\n".join(output)

    def _format_partial_report(self) -> str:
        output: List[str] = [
            f"# ⚠️ Partial Results: {self.topic}",
            "=" * 70,
        ]
        output.append(
            f"**Status:** ⚠️ PARTIAL - Found {len(self.all_code_blocks)} blocks"
        )
        output.append(f"**Pages Visited:** {self.total_pages_scraped}")
        output.append("")

        output.append("## 💻 Code Examples Found")
        for i, block in enumerate(self.all_code_blocks[:MAX_PYTHON_EXAMPLES + MAX_BASH_EXAMPLES], 1):
            lang = block.get("language", "text")
            source = block.get("source_url", "Unknown")
            output.append(f"### Example {i} ({lang}) - From: {source}")
            output.append(f"```{lang}\n{block['code']}\n```\n")

        # Page snapshots here as well
        output.append("## 📄 Page Snapshots (Content for Blog Writing)")
        for i, source in enumerate(self.all_sources, 1):
            title = source.get("title", "Unknown")
            url = source["url"]
            snippet = source.get("content_snippet", "") or ""
            output.append(f"\n### {i}. {title}\n")
            output.append(f"**URL:** {url}\n")
            if snippet:
                output.append("```text")
                output.append(snippet)
                output.append("```")
            else:
                output.append(
                    "_No preview content captured for this page._"
                )

        return "\n".join(output)

    def _format_failure_report(self) -> str:
        output: List[str] = [
            f"# ❌ Deep Search Failed: {self.topic}",
            "=" * 70,
        ]
        output.append(
            "**Status:** ❌ FAILED - NO_CODE_EXAMPLES_FOUND (but page snapshots may still be useful)"
        )
        output.append(f"**Pages Visited:** {self.total_pages_scraped}")
        output.append(f"**URLs Checked:** {len(self.visited_urls)}")
        output.append("")

        if self.all_sources:
            output.append("## 📄 Page Snapshots (Content for Blog Writing)")
            for i, source in enumerate(self.all_sources, 1):
                title = source.get("title", "Unknown")
                url = source["url"]
                snippet = source.get("content_snippet", "") or ""
                output.append(f"\n### {i}. {title}\n")
                output.append(f"**URL:** {url}\n")
                if snippet:
                    output.append("```text")
                    output.append(snippet)
                    output.append("```")
                else:
                    output.append(
                        "_No preview content captured for this page._"
                    )
        else:
            output.append("## 📄 Pages Checked (No Code Found)")
            for url in self.visited_urls:
                output.append(f"- {url}")

        output.append("\n## 💡 Debugging Info")
        output.append("Possible issues:")
        output.append(
            "1. ReadTheDocs HTML detection might be missing (check search.py)"
        )
        output.append("2. URLs might be returning empty content")
        output.append("3. Sites might be blocking scraping")
        output.append("\nTry: python scripts/search.py readme xgboost")

        return "\n".join(output)


# ============================================================================
# CREWAI TOOL WRAPPER
# ============================================================================


def deep_find_documentation_impl(topic: str) -> str:
    """
    Deep documentation finder for blog generation, tuned for small LLMs.

    Workflow:
      1. Try to infer a package name from the topic and fetch its README
         via scrape_readme_smart (PyPI → GitHub).
      2. Then run a deep search across web pages for additional code and prose.
      3. Return a single, blog-friendly report combining README + deep web content,
         with capped size so it fits into small-model contexts (e.g. 3B models).
    """
    if not topic or not topic.strip():
        return "Error: Empty topic provided"

    topic = topic.strip()
    logger.info(
        f"🚀 Starting deep documentation search for topic: {topic!r}"
    )

    report_parts: List[str] = []

    # ------------------------------------------------------------------ #
    # 1) Try to infer package name and fetch README (PyPI → GitHub)
    # ------------------------------------------------------------------ #
    candidates = _infer_package_candidates_from_topic(topic)
    readme_included = False

    if candidates:
        for cand in candidates:
            try:
                logger.info(
                    f"📦 Trying README for inferred package candidate: {cand!r}"
                )
                success, readme_report = scrape_readme_smart(cand)
                if success and readme_report:
                    report_parts.append(
                        f"# 📦 Package README (PyPI / GitHub) for `{cand}`"
                    )
                    report_parts.append("")
                    # For small models, you can optionally truncate here further if needed
                    report_parts.append(readme_report)
                    report_parts.append("\n\n---\n\n")
                    readme_included = True
                    break
            except Exception as e:
                logger.warning(
                    f"README fetch failed for candidate {cand!r}: {e}"
                )

    if not readme_included:
        report_parts.append("# 📦 Package README\n")
        report_parts.append(
            "_No README could be resolved from the topic. "
            "You may want to call `scrape_readme('<package-name>')` directly._"
        )
        report_parts.append("\n\n---\n\n")

    # ------------------------------------------------------------------ #
    # 2) Deep search across documentation/tutorial pages
    # ------------------------------------------------------------------ #
    try:
        finder = DeepFinder(topic=topic, max_pages=MAX_PAGES_TO_VISIT)
        success, deep_report = finder.search_and_scrape()
        report_parts.append(deep_report)
    except Exception as e:
        logger.error(f"Deep search error: {e}", exc_info=True)
        report_parts.append(f"❌ Deep search failed: {str(e)}")

    return "\n".join(report_parts)


# ============================================================================
# CREATE CREWAI TOOL
# ============================================================================


def create_crewai_tool(func, tool_name: str, tool_description: str):
    func.__name__ = tool_name
    func.name = tool_name
    func.description = tool_description
    func.__doc__ = tool_description

    if CREWAI_AVAILABLE:
        try:
            decorated = tool(func)
            if not hasattr(decorated, "name"):
                decorated.name = tool_name
            if not hasattr(decorated, "description"):
                decorated.description = tool_description
            return decorated
        except Exception as e:
            logger.warning(f"CrewAI decorator failed: {e}")
    return func


deep_find_documentation = create_crewai_tool(
    func=deep_find_documentation_impl,
    tool_name="deep_find_documentation",
    tool_description=(
        "Deep documentation finder for blog creation. "
        "First pulls PyPI/GitHub README when possible, then visits multiple "
        "web pages to find code and rich content, with small-model-friendly "
        "output sizes. Use when README alone is not enough."
    ),
)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    if len(sys.argv) < 2:
        print("Usage: python scripts/finder.py <topic>")
        sys.exit(1)

    print("\n" + "=" * 70)
    print("DEEP DOCUMENTATION SEARCH (BLOG MODE, LOW-RESOURCE FRIENDLY)")
    print("=" * 70 + "\n")

    result = deep_find_documentation_impl(" ".join(sys.argv[1:]))
    print(result)
