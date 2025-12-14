#!/usr/bin/env python3
"""
scripts/finder.py - PRODUCTION v3.2 (BLOG-ENHANCED, LOW-RESOURCE FRIENDLY)

Deep Web Documentation & README Finder.

Key goals:
- Robust URL extraction from formatted search results.
- Code extraction from Markdown fences *and* HTML <pre><code> blocks.
- Blog-friendly output: includes page snapshots (trimmed) plus a small set of examples.
- Low-resource mode defaults (small local LLMs + limited RAM).
- Avoid brittle imports / CrewAI decorator variance.

Environment knobs:
- FINDER_LOW_RESOURCE=1|0
- FINDER_MAX_PAGES, FINDER_WORKERS, FINDER_PAGE_TIMEOUT, FINDER_TOTAL_TIMEOUT
- FINDER_MIN_CODE, FINDER_SNIPPET_CHARS
- FINDER_MAX_PY_EXAMPLES, FINDER_MAX_BASH_EXAMPLES
- FINDER_MAX_README_CHARS  (caps README report length before returning)
"""


import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as CFTimeout
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Import from scripts/search.py (robust to different entrypoints)
# -----------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    # Prefer local sibling import when running from scripts/
    import search  # type: ignore
except Exception:
    # Fallback to package-style
    import scripts.search as search  # type: ignore


# Re-exported helpers from search.py (single source of truth)
search_web_impl = search.search_web_impl
scrape_webpage_impl = search.scrape_webpage_impl
CodeDetector = search.CodeDetector
rate_limiter = search.rate_limiter
scrape_readme_smart = search.scrape_readme_smart

# -----------------------------------------------------------------------------
# CrewAI tool decorator (optional)
# -----------------------------------------------------------------------------
try:
    from crewai.tools import tool  # type: ignore

    CREWAI_AVAILABLE = True
except Exception:
    try:
        from crewai_tools import tool  # type: ignore

        CREWAI_AVAILABLE = True
    except Exception:
        CREWAI_AVAILABLE = False

        def tool(func):  # type: ignore
            return func


# ============================================================================
# CONFIGURATION (LOW-RESOURCE AWARE)
# ============================================================================

LOW_RESOURCE_MODE = os.getenv("FINDER_LOW_RESOURCE", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

MAX_PAGES_TO_VISIT = int(os.getenv("FINDER_MAX_PAGES", "5" if LOW_RESOURCE_MODE else "10"))
MAX_PARALLEL_WORKERS = int(os.getenv("FINDER_WORKERS", "2" if LOW_RESOURCE_MODE else "4"))
PAGE_SCRAPE_TIMEOUT = int(os.getenv("FINDER_PAGE_TIMEOUT", "20" if LOW_RESOURCE_MODE else "30"))
TOTAL_SEARCH_TIMEOUT = int(os.getenv("FINDER_TOTAL_TIMEOUT", "90" if LOW_RESOURCE_MODE else "120"))
MIN_CODE_BLOCKS_TARGET = int(os.getenv("FINDER_MIN_CODE", "2" if LOW_RESOURCE_MODE else "3"))

SNIPPET_CHARS = int(os.getenv("FINDER_SNIPPET_CHARS", "1200" if LOW_RESOURCE_MODE else "3000"))
MAX_PYTHON_EXAMPLES = int(os.getenv("FINDER_MAX_PY_EXAMPLES", "3" if LOW_RESOURCE_MODE else "5"))
MAX_BASH_EXAMPLES = int(os.getenv("FINDER_MAX_BASH_EXAMPLES", "2" if LOW_RESOURCE_MODE else "3"))

MAX_README_CHARS = int(os.getenv("FINDER_MAX_README_CHARS", "12000" if LOW_RESOURCE_MODE else "20000"))

SEARCH_STRATEGIES = [
    "{topic} python tutorial",
    "{topic} code examples",
    "{topic} quickstart guide",
    "how to use {topic} python",
    "{topic} github source code",
]


# ============================================================================
# HELPERS
# ============================================================================

def _infer_package_candidates_from_topic(topic: str) -> List[str]:
    """Infer likely package candidates from a topic string."""
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


def _is_public_http_url(url: str) -> bool:
    """Lightweight public HTTP URL check (SSRF-hardening happens in search.py fetch)."""
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
        return not any(re.match(p, hostname) for p in private_patterns)
    except Exception:
        return False


def _truncate(text: str, limit: int, marker: str) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n[{marker}: truncated from {len(text)} chars]"


# ============================================================================
# URL EXTRACTOR
# ============================================================================

class URLExtractor:
    """Extract URLs from the formatted output of search.search_web_impl()."""

    @staticmethod
    def extract_urls_from_search_results(result_text: str) -> List[Dict[str, str]]:
        urls: List[Dict[str, str]] = []
        seen = set()

        # 1) Lines like: **URL:** https://...
        for match in re.finditer(r"\*\*URL:\*\*\s*(https?://[^\s]+)", result_text):
            url = re.sub(r"[\.,;!?)\]]+$", "", match.group(1).strip())
            if url not in seen and _is_public_http_url(url):
                urls.append({"url": url, "title": "Search Result", "source": "formatted_url_line"})
                seen.add(url)

        # 2) Markdown links: [title](url)
        for match in re.finditer(r"\[([^\]]+)\]\((https?://[^)]+)\)", result_text):
            title = match.group(1).strip()
            url = re.sub(r"[\.,;!?)\]]+$", "", match.group(2).strip())
            if url not in seen and _is_public_http_url(url):
                urls.append({"url": url, "title": title, "source": "markdown_link"})
                seen.add(url)

        # 3) Raw URLs
        for match in re.finditer(r"(?:^|\s)(https?://[^\s\)\]>,]+)", result_text, re.MULTILINE):
            url = re.sub(r"[\.,;!?)\]]+$", "", match.group(1).strip())
            if url not in seen and _is_public_http_url(url):
                urls.append({"url": url, "title": "Search Result", "source": "raw_url"})
                seen.add(url)

        return urls


# ============================================================================
# CODE EXTRACTOR (Markdown + HTML)
# ============================================================================

class EnhancedCodeExtractor:
    """Extract code using Markdown fences (primary) and HTML parsing (optional)."""

    @staticmethod
    def extract_all_code(content: str) -> List[Dict[str, Any]]:
        all_blocks: List[Dict[str, Any]] = []
        seen_hashes: set[int] = set()

        md_blocks = CodeDetector.extract_from_markdown(content)
        logger.info("  📝 Markdown extraction: %d blocks", len(md_blocks))

        for b in md_blocks:
            code_text = (b.get("code") or "").strip()
            if not code_text:
                continue
            h = hash(code_text)
            if h in seen_hashes:
                continue
            all_blocks.append(b)
            seen_hashes.add(h)

        # If content is HTML-ish, attempt parsing (best-effort)
        if any(x in content for x in ("<pre", "<code", "<div", "highlight")):
            try:
                from bs4 import BeautifulSoup  # type: ignore

                soup = BeautifulSoup(content, "html.parser")
                html_blocks = CodeDetector.extract_from_html(soup)
                logger.info("  🔍 HTML extraction: %d blocks", len(html_blocks))
                for b in html_blocks:
                    code_text = (b.get("code") or "").strip()
                    if not code_text:
                        continue
                    h = hash(code_text)
                    if h in seen_hashes:
                        continue
                    all_blocks.append(b)
                    seen_hashes.add(h)
            except Exception as exc:
                logger.debug("  ⚠️ HTML parsing failed: %s", exc)

        logger.info("  ✅ Total unique blocks: %d", len(all_blocks))
        return all_blocks


# ============================================================================
# CORE: DeepFinder
# ============================================================================

class DeepFinder:
    """Search and scrape multiple pages, returning a blog-friendly report."""

    def __init__(self, topic: str, max_pages: int = MAX_PAGES_TO_VISIT):
        self.topic = topic
        self.max_pages = max_pages

        self.visited_urls: set[str] = set()
        self.all_code_blocks: List[Dict[str, Any]] = []
        self.all_sources: List[Dict[str, Any]] = []

        self.total_pages_scraped = 0
        self.successful_scrapes = 0

    def search_and_scrape(self) -> Tuple[bool, str]:
        logger.info("🚀 Starting deep search for: %r", self.topic)
        start_time = time.time()

        urls = self._get_search_results(f"{self.topic} python tutorial documentation")
        logger.info("  → Found %d URLs after initial search", len(urls))

        if len(urls) < 3:
            logger.info("📍 Extended search (only %d URLs initially)", len(urls))
            for strat in SEARCH_STRATEGIES:
                if len(urls) >= self.max_pages:
                    break
                query = strat.format(topic=self.topic)
                new_urls = self._get_search_results(query)

                existing = {u["url"] for u in urls}
                for nu in new_urls:
                    if nu["url"] not in existing:
                        urls.append(nu)
                        existing.add(nu["url"])

                if len(urls) >= self.max_pages:
                    break

        if not urls:
            logger.warning("❌ No URLs found after all search strategies")
            return False, self._format_failure_report()

        logger.info("📋 Final URL count: %d sources to visit", len(urls))

        self._visit_pages_parallel(urls[: self.max_pages])

        # GitHub fallback if we found *nothing* useful
        if not self.all_code_blocks:
            logger.info("📍 GitHub fallback search")
            github_urls = self._get_search_results(f"{self.topic} github source code")
            self._visit_pages_parallel(github_urls[:2])

        elapsed = time.time() - start_time
        logger.info("✅ Deep search complete in %.1fs", elapsed)
        logger.info("  📊 Pages visited: %d, successful: %d, code blocks: %d",
                    self.total_pages_scraped, self.successful_scrapes, len(self.all_code_blocks))

        if len(self.all_code_blocks) >= MIN_CODE_BLOCKS_TARGET:
            return True, self._format_success_report()
        if self.all_code_blocks:
            return True, self._format_partial_report()
        return False, self._format_failure_report()

    def _get_search_results(self, query: str) -> List[Dict[str, str]]:
        logger.info("🔍 Searching: %s", query)
        try:
            result_text = search_web_impl(query)
            urls = URLExtractor.extract_urls_from_search_results(result_text)
            if not urls:
                logger.debug("No URLs extracted; search output preview: %s", result_text[:800])
            return urls
        except Exception as exc:
            logger.error("Search failed: %s", exc)
            return []

    def _visit_pages_parallel(self, search_results: List[Dict[str, str]]) -> None:
        if not search_results:
            return

        logger.info("🌐 Visiting %d pages in parallel...", len(search_results))

        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_WORKERS) as executor:
            futures = {executor.submit(self._scrape_single_page, r): r for r in search_results}

            try:
                for future in as_completed(futures, timeout=TOTAL_SEARCH_TIMEOUT):
                    try:
                        ok = future.result(timeout=PAGE_SCRAPE_TIMEOUT)
                        if ok:
                            self.successful_scrapes += 1
                    except CFTimeout:
                        r = futures.get(future, {})
                        logger.debug("Page scrape timeout: %s", r.get("url"))
                    except Exception as exc:
                        r = futures.get(future, {})
                        logger.debug("Scrape error for %s: %s", r.get("url"), exc)
            except CFTimeout:
                logger.warning("⏱️ Total deep search timeout reached")
                for f in futures:
                    f.cancel()

    def _scrape_single_page(self, result_info: Dict[str, str]) -> bool:
        url = result_info.get("url", "")
        if not url or url in self.visited_urls:
            return False

        self.visited_urls.add(url)
        self.total_pages_scraped += 1

        logger.info("📄 [%d] Scraping: %s", self.total_pages_scraped, url[:90])

        try:
            rate_limiter.wait_if_needed()
            content = scrape_webpage_impl(url)  # already formatted by search.py

            if not content:
                self.all_sources.append(
                    {"url": url, "title": result_info.get("title", "Unknown"), "code_blocks": 0, "content_snippet": ""}
                )
                return False

            snippet = _truncate(content, SNIPPET_CHARS, "page snippet")
            code_blocks = EnhancedCodeExtractor.extract_all_code(content)

            for block in code_blocks:
                block["source_url"] = url
                block["source_title"] = result_info.get("title", "Unknown")
                self.all_code_blocks.append(block)

            self.all_sources.append(
                {
                    "url": url,
                    "title": result_info.get("title", "Unknown"),
                    "code_blocks": len(code_blocks),
                    "content_snippet": snippet,
                }
            )

            # Consider successful if we got non-trivial content
            return len(content) >= 200

        except Exception as exc:
            logger.debug("Error scraping %s: %s", url, exc)
            self.all_sources.append(
                {"url": url, "title": result_info.get("title", "Unknown"), "code_blocks": 0, "content_snippet": ""}
            )
            return False

    # ------------------------------------------------------------------ #
    # REPORTS
    # ------------------------------------------------------------------ #

    def _format_success_report(self) -> str:
        output: List[str] = []
        output.append(f"# 🎯 Deep Search Results: {self.topic}")
        output.append("=" * 70)
        output.append(f"Status: SUCCESS - Found {len(self.all_code_blocks)} code blocks")
        output.append(f"Pages Visited: {self.total_pages_scraped}")
        output.append(f"Successful Scrapes: {self.successful_scrapes}")
        output.append("")

        python_blocks = [b for b in self.all_code_blocks if "python" in (b.get("language", "") or "").lower()]
        bash_blocks = [b for b in self.all_code_blocks if b.get("language") in {"bash", "sh", "shell", "console"}]

        output.append("## Summary")
        output.append(f"- Python Examples: {len(python_blocks)}")
        output.append(f"- Setup Commands: {len(bash_blocks)}")
        output.append(f"- Total Code Blocks: {len(self.all_code_blocks)}")
        output.append("")

        sorted_sources = sorted(self.all_sources, key=lambda x: x.get("code_blocks", 0), reverse=True)

        output.append("## Sources (best first)")
        for i, s in enumerate(sorted_sources, 1):
            url = s.get("url", "")
            blocks = int(s.get("code_blocks", 0))
            indicator = "🎯" if blocks > 10 else ("✓" if blocks > 0 else "✗")
            output.append(f"{i}. {indicator} {url} - {blocks} code blocks")
        output.append("")

        output.append("## Page Snapshots")
        for i, s in enumerate(sorted_sources, 1):
            output.append(f"### {i}. {s.get('title', 'Unknown')}")
            output.append(f"URL: {s.get('url', '')}")
            snippet = (s.get("content_snippet") or "").strip()
            if snippet:
                output.append("```text")
                output.append(snippet)
                output.append("```")
            else:
                output.append("_No preview captured._")
            output.append("")

        if python_blocks:
            output.append("## Python Code Examples")
            for i, b in enumerate(python_blocks[:MAX_PYTHON_EXAMPLES], 1):
                output.append(f"### Example {i} - From: {b.get('source_url', 'Unknown')}")
                output.append(f"```python\n{b.get('code','')}\n```")
                output.append("")

        if bash_blocks:
            output.append("## Installation / Setup")
            for i, b in enumerate(bash_blocks[:MAX_BASH_EXAMPLES], 1):
                output.append(f"### Setup {i}")
                output.append(f"```bash\n{b.get('code','')}\n```")
                output.append("")

        return "\n".join(output)

    def _format_partial_report(self) -> str:
        output: List[str] = []
        output.append(f"# ⚠️ Partial Results: {self.topic}")
        output.append("=" * 70)
        output.append(f"Status: PARTIAL - Found {len(self.all_code_blocks)} code blocks")
        output.append(f"Pages Visited: {self.total_pages_scraped}")
        output.append("")

        output.append("## Code Examples")
        for i, b in enumerate(self.all_code_blocks[: MAX_PYTHON_EXAMPLES + MAX_BASH_EXAMPLES], 1):
            lang = b.get("language", "text")
            output.append(f"### Example {i} ({lang}) - From: {b.get('source_url','Unknown')}")
            output.append(f"```{lang}\n{b.get('code','')}\n```")
            output.append("")

        output.append("## Page Snapshots")
        for i, s in enumerate(self.all_sources, 1):
            output.append(f"### {i}. {s.get('title', 'Unknown')}")
            output.append(f"URL: {s.get('url', '')}")
            snippet = (s.get("content_snippet") or "").strip()
            if snippet:
                output.append("```text")
                output.append(snippet)
                output.append("```")
            else:
                output.append("_No preview captured._")
            output.append("")

        return "\n".join(output)

    def _format_failure_report(self) -> str:
        output: List[str] = []
        output.append(f"# ❌ Deep Search: {self.topic}")
        output.append("=" * 70)
        output.append("Status: FAILED - No code examples found (snapshots may still help)")
        output.append(f"Pages Visited: {self.total_pages_scraped}")
        output.append(f"URLs Checked: {len(self.visited_urls)}")
        output.append("")

        if self.all_sources:
            output.append("## Page Snapshots")
            for i, s in enumerate(self.all_sources, 1):
                output.append(f"### {i}. {s.get('title', 'Unknown')}")
                output.append(f"URL: {s.get('url', '')}")
                snippet = (s.get("content_snippet") or "").strip()
                if snippet:
                    output.append("```text")
                    output.append(snippet)
                    output.append("```")
                else:
                    output.append("_No preview captured._")
                output.append("")
        else:
            output.append("No pages were scraped successfully.")

        output.append("## Debugging Tips")
        output.append("- Try increasing FINDER_MAX_PAGES / FINDER_WORKERS.")
        output.append("- Some sites block scraping; prefer README / GitHub sources.")
        output.append("- Run: python scripts/search.py readme <package>")
        return "\n".join(output)


# ============================================================================
# CREWAI TOOL WRAPPER
# ============================================================================

def deep_find_documentation_impl(topic: str) -> str:
    """Deep documentation finder for blog generation."""
    if not topic or not topic.strip():
        return "Error: Empty topic provided"

    topic = topic.strip()
    report_parts: List[str] = []

    # 1) README-first from inferred package candidates
    candidates = _infer_package_candidates_from_topic(topic)
    readme_included = False

    for cand in candidates:
        try:
            logger.info("📦 Trying README for inferred candidate: %r", cand)
            success, readme_report = scrape_readme_smart(cand)
            if success and readme_report:
                report_parts.append(f"# 📦 Package README (PyPI / GitHub) for `{cand}`")
                report_parts.append("")
                report_parts.append(_truncate(readme_report, MAX_README_CHARS, "README report"))
                report_parts.append("\n---\n")
                readme_included = True
                break
        except Exception as exc:
            logger.debug("README fetch failed for %r: %s", cand, exc)

    if not readme_included:
        report_parts.append("# 📦 Package README")
        report_parts.append(
            "_No README could be resolved from the topic. "
            "Call `scrape_readme('<package-name>')` directly if you know the package name._"
        )
        report_parts.append("\n---\n")

    # 2) Deep search across pages
    try:
        finder = DeepFinder(topic=topic, max_pages=MAX_PAGES_TO_VISIT)
        _success, deep_report = finder.search_and_scrape()
        report_parts.append(deep_report)
    except Exception as exc:
        logger.error("Deep search error: %s", exc, exc_info=True)
        report_parts.append(f"❌ Deep search failed: {exc}")

    return "\n".join(report_parts)


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
        except Exception as exc:
            logger.warning("CrewAI decorator failed for %s: %s", tool_name, exc)

    return func


deep_find_documentation = create_crewai_tool(
    func=deep_find_documentation_impl,
    tool_name="deep_find_documentation",
    tool_description=(
        "Deep documentation finder for blog creation. Pulls README when possible, "
        "then visits multiple web pages to find code and rich content, with small-model-friendly output."
    ),
)


# ============================================================================
# MAIN (CLI)
# ============================================================================

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if len(sys.argv) < 2:
        print("Usage: python scripts/finder.py <topic>")
        raise SystemExit(1)

    topic = " ".join(sys.argv[1:]).strip()
    result = deep_find_documentation_impl(topic)
    print(result)


if __name__ == "__main__":
    main()
