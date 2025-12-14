#!/usr/bin/env python3
"""
scripts/search.py - PRODUCTION READY v3.2 (SINGLE-FILE, CLEANED)

Enhanced Web Search & Package Analysis Tool for CrewAI Blog Generation.

Key features:
- Thread-safe rate limiting
- SSRF protection (blocks localhost/private IPs; allows public http/https)
- Smart retry (retries transient errors only; avoids 4xx retry loops)
- Versioned caching for search + README
- Robust code extraction from Markdown + HTML (preserves indentation)
- PyPI metadata + GitHub metadata helpers
- Blog-friendly outputs for LLM consumption
- CrewAI tool wrappers compatible with crewai.tools OR crewai_tools
- Tool input normalization (accepts plain string, dict, or JSON string)

Dependencies:
  pip install requests beautifulsoup4 tenacity
Optional:
  pip install markdown-it-py
  pip install ddgs

CLI:
  python scripts/search.py search <query>
  python scripts/search.py readme <package-or-github-url>
  python scripts/search.py health <package-or-github-url>
  python scripts/search.py scrape <url>
"""


import ast
import hashlib
import ipaddress
import json
import logging
import os
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# =============================================================================
# CrewAI tool decorator (compatible with multiple packages)
# =============================================================================

try:
    from crewai.tools import tool  # type: ignore
    _CREWAI_DECORATOR_AVAILABLE = True
except Exception:
    try:
        from crewai_tools import tool  # type: ignore
        _CREWAI_DECORATOR_AVAILABLE = True
    except Exception:
        _CREWAI_DECORATOR_AVAILABLE = False

        def tool(func_or_description):  # type: ignore
            """Fallback decorator supporting @tool and @tool('desc') syntax."""

            def decorator(func):
                func.name = getattr(func, "name", func.__name__)
                func.description = getattr(func, "description", func.__doc__ or "") or "No description"
                return func

            if callable(func_or_description):
                return decorator(func_or_description)
            return decorator


def create_crewai_tool(func, tool_name: str, tool_description: str):
    """Wrap a function as a CrewAI tool and guarantee required attributes."""
    func.__name__ = tool_name
    func.name = tool_name
    func.description = tool_description
    func.__doc__ = tool_description

    if _CREWAI_DECORATOR_AVAILABLE:
        try:
            decorated = tool(func)
            # Some decorators return wrapper objects that may drop attributes.
            for attr, value in (
                ("__name__", tool_name),
                ("name", tool_name),
                ("description", tool_description),
            ):
                if not hasattr(decorated, attr):
                    setattr(decorated, attr, value)
            return decorated
        except Exception as exc:
            logger.warning("CrewAI decorator failed for %s: %s", tool_name, exc)

    return func


# =============================================================================
# Configuration
# =============================================================================

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "search_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_VERSION = "v3.2"
CACHE_DURATION_HOURS = int(os.getenv("SEARCH_CACHE_HOURS", "24"))
MAX_RESULTS_PER_SEARCH = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
REQUEST_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "15"))
RATE_LIMIT = int(os.getenv("SEARCH_RATE_LIMIT", "10"))
MAX_README_SIZE = int(os.getenv("MAX_README_SIZE", "1048576"))  # 1MB

# GitHub API helpers
GITHUB_PATTERN_TIMEOUT = int(os.getenv("GITHUB_PATTERN_TIMEOUT", "20"))
MAX_GITHUB_PATTERNS = int(os.getenv("MAX_GITHUB_PATTERNS", "5"))

# A browser-y header set (avoid overly “botty” UA strings)
BROWSER_HEADERS: Dict[str, str] = {
    "User-Agent": os.getenv(
        "SEARCH_USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

USER_AGENT = BROWSER_HEADERS.get('User-Agent', 'Mozilla/5.0')
# Security: Allowed domains for URL fetching (SSRF protection)
ALLOWED_DOMAINS = {
    "github.com",
    "raw.githubusercontent.com",
    "pypi.org",
    "files.pythonhosted.org",
    "readthedocs.io",
    "readthedocs.org",
    "githubusercontent.com",
    "docs.python.org",
}

def _is_allowed_domain(hostname: str) -> bool:
    """Return True if hostname is in the allowlist or a subdomain of an allowed domain."""
    host = (hostname or "").lower().strip(".")
    for d in ALLOWED_DOMAINS:
        d = d.lower().strip(".")
        if host == d or host.endswith("." + d):
            return True
    return False


# =============================================================================
# Rate limiter (thread-safe, sliding window)
# =============================================================================


class RateLimiter:
    """Thread-safe rate limiter with a 60s sliding window."""

    def __init__(self, calls_per_minute: int = RATE_LIMIT) -> None:
        self.calls_per_minute = max(1, int(calls_per_minute))
        self._calls: List[float] = []
        self._lock = threading.Lock()

    def wait_if_needed(self) -> None:
        with self._lock:
            now = time.time()
            self._calls = [t for t in self._calls if now - t < 60.0]

            if len(self._calls) >= self.calls_per_minute:
                sleep_time = 60.0 - (now - self._calls[0]) + 0.25
                if sleep_time > 0:
                    logger.info("⏱️  Rate limit: sleeping %.2fs", sleep_time)
                    time.sleep(sleep_time)

            self._calls.append(time.time())


rate_limiter = RateLimiter()

# =============================================================================
# Caching (versioned)
# =============================================================================


def _cache_key(query: str, provider: str) -> str:
    combined = f"{CACHE_VERSION}:{provider}:{query.lower().strip()}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()

def get_cache_key(query: str, provider: str) -> str:
    """Public wrapper for cache key generation (backward compatible)."""
    return _cache_key(query, provider)



def get_cached_result(query: str, provider: str) -> Optional[Any]:
    key = _cache_key(query, provider)
    cache_file = CACHE_DIR / f"{key}.json"
    if not cache_file.exists():
        return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        if data.get("version") != CACHE_VERSION:
            cache_file.unlink(missing_ok=True)
            return None

        ts = data.get("timestamp")
        if not ts:
            cache_file.unlink(missing_ok=True)
            return None

        cached_time = datetime.fromisoformat(ts)
        if datetime.now(cached_time.tzinfo) - cached_time < timedelta(hours=CACHE_DURATION_HOURS):
            logger.info("💾 Cache hit: %s (%s)", query[:80], provider)
            return data.get("payload")
        cache_file.unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Cache read error: %s", exc)

    return None


def cache_result(query: str, provider: str, payload: Any) -> None:
    key = _cache_key(query, provider)
    cache_file = CACHE_DIR / f"{key}.json"
    try:
        data = {
            "version": CACHE_VERSION,
            "provider": provider,
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "payload": payload,
        }
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.warning("Cache write error: %s", exc)


# =============================================================================
# Security: URL validation (SSRF protection)
# =============================================================================


_PRIVATE_HOST_PATTERNS = [
    r"^localhost$",
    r"^127\.",
    r"^10\.",
    r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
    r"^192\.168\.",
    r"^169\.254\.",
    r"^0\.0\.0\.0$",
]


def validate_url(url: str, allow_private: bool = False) -> Tuple[bool, str]:
    """Validate URL to prevent SSRF attacks.

    Rules:
      - Only allow http/https
      - Only allow domains in ALLOWED_DOMAINS (or their subdomains)
      - Block localhost / private / link-local / reserved IPs by default
    """
    try:
        if not url or not isinstance(url, str):
            return False, "Empty or non-string URL"

        url = url.strip()
        parsed = urlparse(url)

        scheme = (parsed.scheme or "").lower()
        if scheme not in ("http", "https"):
            return False, f"Invalid scheme: {scheme or 'missing'}"

        hostname = (parsed.hostname or "").strip().lower()
        if not hostname:
            return False, "Missing hostname in URL"

        if not allow_private:
            # Quick hostname-pattern blocks
            private_patterns = [
                r"^localhost$",
                r"^127\.",
                r"^10\.",
                r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
                r"^192\.168\.",
                r"^169\.254\.",
                r"^0\.0\.0\.0$",
            ]
            for pat in private_patterns:
                if re.match(pat, hostname):
                    return False, f"Private/loopback host not allowed: {hostname}"

            # If it's a literal IP, validate with ipaddress too
            try:
                import ipaddress
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                    return False, f"Private/loopback IP not allowed: {hostname}"
            except ValueError:
                pass

        if not _is_allowed_domain(hostname):
            return False, f"Domain not allowed: {hostname}"

        return True, ""
    except Exception as exc:
        return False, f"URL validation error: {exc}"



# =============================================================================
# Fetching with smart retry (avoid infinite loops on permanent 4xx)
# =============================================================================


def should_retry_request(exc: Exception) -> bool:
    """Retry transient errors only."""
    if isinstance(exc, (requests.Timeout, requests.ConnectTimeout, requests.ReadTimeout)):
        return True
    if isinstance(exc, requests.ConnectionError):
        return True
    if isinstance(exc, requests.HTTPError) and getattr(exc, "response", None) is not None:
        status = exc.response.status_code
        return status == 429 or status >= 500
    return False


@retry(
    retry=retry_if_exception(should_retry_request),
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True,
)
def fetch_url_with_retry(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = REQUEST_TIMEOUT) -> requests.Response:
    headers = headers or BROWSER_HEADERS
    # Jitter reduces burstiness (helps rate limits)
    time.sleep(random.uniform(0.15, 0.45))
    session = requests.Session()
    session.headers.update(headers)
    resp = session.get(url, timeout=timeout, allow_redirects=True)
    resp.raise_for_status()
    return resp


def fetch_url(url: str, *, validate: bool = True, timeout: int = REQUEST_TIMEOUT) -> Optional[requests.Response]:
    if validate:
        ok, msg = validate_url(url)
        if not ok:
            logger.debug("URL rejected: %s (%s)", url, msg)
            return None

    try:
        return fetch_url_with_retry(url, headers=BROWSER_HEADERS, timeout=timeout)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status == 404:
            logger.debug("404 Not Found: %s", url)
        elif status == 403:
            logger.warning("🚫 403 Forbidden: %s", url)
        elif status == 429:
            logger.warning("⏱️ 429 Rate limited: %s", url)
        elif status and status >= 500:
            logger.warning("💥 %s Server error: %s", status, url)
        else:
            logger.warning("HTTP error on %s: %s", url, exc)
        return None
    except requests.Timeout:
        logger.warning("⏱️ Timeout: %s", url)
        return None
    except requests.ConnectionError as exc:
        logger.warning("🔌 Connection error: %s (%s)", url, str(exc)[:120])
        return None
    except Exception as exc:
        logger.debug("Fetch failed: %s (%s)", url, exc)
        return None


# =============================================================================
# Code extraction engine (Markdown + HTML)
# =============================================================================

try:
    from markdown_it import MarkdownIt  # type: ignore
    _HAS_MARKDOWN_IT = True
except Exception:
    MarkdownIt = None  # type: ignore
    _HAS_MARKDOWN_IT = False


class CodeDetector:
    """Extract code blocks from Markdown or HTML (preserves indentation)."""

    CODE_LANGUAGES = {
        "python", "py", "python3", "py3",
        "bash", "sh", "shell", "console", "terminal",
        "javascript", "js", "typescript", "ts",
        "java", "c", "cpp", "c++", "csharp", "c#",
        "ruby", "rb", "go", "rust", "php",
        "sql", "json", "yaml", "yml", "xml", "html", "css",
        "text", "txt", "plaintext", "output",
    }

    @staticmethod
    def extract_from_markdown(text: str, min_lines: int = 1) -> List[Dict[str, Any]]:
        if not text:
            return []
        if _HAS_MARKDOWN_IT:
            return CodeDetector._extract_from_markdown_ast(text, min_lines=min_lines)
        return CodeDetector._extract_from_markdown_regex(text, min_lines=min_lines)

    @staticmethod
    def _extract_from_markdown_ast(text: str, min_lines: int = 1) -> List[Dict[str, Any]]:
        try:
            md = MarkdownIt()
            tokens = md.parse(text)
        except Exception as exc:
            logger.debug("markdown-it parsing failed (%s), using regex fallback", exc)
            return CodeDetector._extract_from_markdown_regex(text, min_lines=min_lines)

        blocks: List[Dict[str, Any]] = []
        index = 1
        for token in tokens:
            if token.type != "fence":
                continue
            lang_raw = (token.info or "").strip().lower()
            code = token.content or ""
            if not code.strip():
                continue
            lines = code.splitlines()
            if len(lines) < min_lines:
                continue
            lang = lang_raw or CodeDetector._detect_language(code)
            if lang not in CodeDetector.CODE_LANGUAGES:
                lang = CodeDetector._detect_language(code)
            blocks.append({"index": index, "language": lang, "code": code, "lines": len(lines), "source": "markdown_ast"})
            index += 1
        return blocks

    @staticmethod
    def _extract_from_markdown_regex(text: str, min_lines: int = 1) -> List[Dict[str, Any]]:
        pattern = (
            r"(?P<fence>```|~~~)"
            r"(?P<lang>[\w\+\-\#\.]*)?\s*"
            r"(?:\r?\n|\r)"
            r"(?P<code>.*?)"
            r"(?:\r?\n|\r)\s*(?P=fence)"
        )
        blocks: List[Dict[str, Any]] = []
        for i, m in enumerate(re.finditer(pattern, text, re.DOTALL), 1):
            lang_raw = (m.group("lang") or "").strip().lower()
            code = m.group("code") or ""
            if not code.strip():
                continue
            lines = code.splitlines()
            if len(lines) < min_lines:
                continue
            lang = lang_raw if lang_raw in CodeDetector.CODE_LANGUAGES else ""
            if not lang:
                lang = CodeDetector._detect_language(code)
            blocks.append({"index": i, "language": lang, "code": code, "lines": len(lines), "source": "markdown_fence"})
        return blocks

    @staticmethod
    def _detect_language(code: str) -> str:
        snippet = code[:2000]
        if any(k in snippet for k in ("def ", "import ", "from ", "class ", "self.", "print(")):
            return "python"
        if any(k in snippet for k in ("pip install", "conda install", "apt-get", "yum install", "sudo ", "#!/bin/bash", "#!/bin/sh")):
            return "bash"
        if any(k in snippet for k in ("function ", "const ", "let ", "=>", "console.log")):
            return "javascript"
        if re.match(r"^(pip|npm|yarn|cargo|go get|composer)\b", snippet.strip(), re.MULTILINE):
            return "console"
        return "text"

    @staticmethod
    def extract_from_html(soup: BeautifulSoup) -> List[Dict[str, Any]]:
        blocks: List[Dict[str, Any]] = []
        if soup is None:
            return blocks

        index = 1

        # Strategy A: Sphinx/RTD highlight divs
        highlight_divs = soup.find_all(
            lambda tag: (
                tag.name == "div"
                and tag.get("class")
                and any(
                    "highlight" in c.lower() or "literal-block" in c.lower() for c in tag.get("class", [])
                )
            )
        )
        for div in highlight_divs:
            lang = "text"
            classes = div.get("class", []) or []
            for cls in classes:
                cls_l = str(cls).lower()
                if cls_l.startswith("highlight-"):
                    cand = cls_l.replace("highlight-", "").replace("notranslate", "").strip()
                    if cand in CodeDetector.CODE_LANGUAGES:
                        lang = cand
                        break
                if cls_l in CodeDetector.CODE_LANGUAGES:
                    lang = cls_l

            pre = div.find("pre")
            code_text = pre.get_text("\n", strip=False) if pre else div.get_text("\n", strip=False)
            if not code_text or len(code_text.strip()) <= 10:
                continue
            if any(b.get("code", "").strip() == code_text.strip() for b in blocks):
                continue
            blocks.append({"index": index, "language": lang, "code": code_text, "lines": len(code_text.splitlines()), "source": "html_highlight"})
            index += 1

        # Strategy B: <pre><code> blocks
        for pre in soup.find_all("pre"):
            # Skip if already captured via highlight div
            if pre.find_parent(lambda t: t.name == "div" and t.get("class") and any("highlight" in c.lower() for c in t.get("class", []))):
                continue
            code_elem = pre.find("code")
            node = code_elem if code_elem is not None else pre
            code_text = node.get_text("\n", strip=False)
            if not code_text or not code_text.strip():
                continue
            lang = CodeDetector._extract_language_from_classes(pre, code_elem)
            if any(b.get("code", "").strip() == code_text.strip() for b in blocks):
                continue
            blocks.append({"index": index, "language": lang, "code": code_text, "lines": len(code_text.splitlines()), "source": "html_pre"})
            index += 1

        return blocks

    @staticmethod
    def _extract_language_from_classes(pre_elem, code_elem) -> str:
        classes: List[str] = []
        if pre_elem is not None:
            classes.extend(pre_elem.get("class", []) or [])
        if code_elem is not None:
            classes.extend(code_elem.get("class", []) or [])
        for cls in classes:
            cls_l = str(cls).lower()
            parts = re.split(r"[-_]", cls_l)
            for part in parts:
                if part in CodeDetector.CODE_LANGUAGES:
                    return part
            if cls_l in CodeDetector.CODE_LANGUAGES:
                return cls_l
        return "text"

    @staticmethod
    def format_for_llm(context_text: str, code_blocks: List[Dict[str, Any]], source_url: str = "") -> str:
        out: List[str] = []
        if source_url:
            out.append(f"# Content from: {source_url}")
            out.append("")
        if not code_blocks:
            out.append("⚠️ [SYSTEM: NO CODE BLOCKS DETECTED IN SOURCE]")
            out.append("=" * 70)
            out.append("")
            out.append("[DOCUMENT CONTEXT]")
            clean_text = re.sub(r"\n{3,}", "\n\n", context_text or "")
            out.append((clean_text or "")[:4000])
            return "\n".join(out)

        out.append(f"✅ FOUND {len(code_blocks)} CODE BLOCKS IN SOURCE")
        out.append("=" * 70)
        out.append("")
        python_blocks = [b for b in code_blocks if (b.get("language") or "").lower() in {"python", "py", "python3", "py3"}]
        install_blocks = [b for b in code_blocks if (b.get("language") or "").lower() in {"bash", "sh", "shell", "console", "terminal"}]
        other_blocks = [b for b in code_blocks if b not in python_blocks and b not in install_blocks]

        if python_blocks:
            out.append("## Python Code Examples")
            for b in python_blocks:
                out.append(f"\n### Block {b['index']} ({b['lines']} lines)")
                out.append(f"```python\n{b['code']}\n```")
                out.append("")
        if install_blocks:
            out.append("## Installation / Setup Commands")
            for b in install_blocks:
                out.append(f"\n### Block {b['index']}")
                out.append(f"```bash\n{b['code']}\n```")
                out.append("")
        if other_blocks:
            out.append("## Other Code / Examples")
            for b in other_blocks:
                lang = b.get("language") or "text"
                out.append(f"\n### Block {b['index']} ({lang})")
                out.append(f"```{lang}\n{b['code']}\n```")
                out.append("")
        out.append("=" * 70)
        out.append("[DOCUMENT CONTEXT - Prose]")
        clean_text = re.sub(r"\n{3,}", "\n\n", context_text or "")
        out.append((clean_text or "")[:3000])
        return "\n".join(out)


# =============================================================================
# Search providers (DuckDuckGo via library, API fallback)
# =============================================================================


def search_duckduckgo_html(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Optional[List[Dict[str, str]]]:
    """Search via ddgs (preferred) or duckduckgo_search (fallback)."""
    try:
        try:
            from ddgs import DDGS, exceptions as ddg_exceptions  # type: ignore

            RatelimitException = getattr(ddg_exceptions, "RatelimitException", Exception)
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore
            try:
                from duckduckgo_search.exceptions import RatelimitException  # type: ignore
            except Exception:
                RatelimitException = Exception  # type: ignore
    except ImportError:
        logger.error("❌ Missing search backend. Install: pip install ddgs")
        return None

    try:
        results: List[Dict[str, str]] = []
        time.sleep(random.uniform(0.2, 0.6))
        with DDGS() as ddgs:
            ddg_results = ddgs.text(query, max_results=max_results)  # positional query for compatibility
            if ddg_results:
                for r in ddg_results:
                    url = r.get("href") or r.get("url") or ""
                    if not url:
                        continue
                    results.append(
                        {
                            "title": r.get("title", ""),
                            "url": url,
                            "snippet": r.get("body") or r.get("description") or "",
                            "source": "duckduckgo-lib",
                        }
                    )
        return results or None
    except Exception as exc:  # includes RatelimitException
        logger.warning("DuckDuckGo search failed: %s", exc)
        return None


def search_duckduckgo_api(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Optional[List[Dict[str, str]]]:
    """DuckDuckGo Instant Answer API (often sparse, but good fallback)."""
    try:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_redirect": "1", "no_html": "1", "skip_disambig": "1"}
        resp = requests.get(url, params=params, headers=BROWSER_HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        results: List[Dict[str, str]] = []

        for item in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(item, dict) and item.get("FirstURL") and item.get("Text"):
                results.append(
                    {
                        "title": (item.get("Text") or "")[:100],
                        "url": item.get("FirstURL") or "",
                        "snippet": item.get("Text") or "",
                        "source": "duckduckgo-api",
                    }
                )

        if not results and data.get("Abstract") and data.get("AbstractURL"):
            results.append(
                {
                    "title": data.get("Heading", query),
                    "url": data.get("AbstractURL") or "",
                    "snippet": data.get("Abstract") or "",
                    "source": "duckduckgo-api",
                }
            )
        return results or None
    except Exception as exc:
        logger.debug("DuckDuckGo API fallback failed: %s", exc)
        return None


def _format_search_results(results: List[Dict[str, str]], query: str) -> str:
    out: List[str] = []
    out.append(f"# 🔍 Search Results: {query}")
    out.append("")
    out.append(f"Found {len(results)} results:")
    out.append("=" * 70)
    out.append("")
    for i, r in enumerate(results, 1):
        out.append(f"## Result {i}")
        out.append(f"**Title:** {r.get('title','')}")
        out.append(f"**URL:** {r.get('url','')}")
        out.append(f"**Summary:** {r.get('snippet','')}")
        out.append("")
    out.append("---")
    out.append("## 📚 Resources (Citation Format)")
    out.append("")
    for r in results:
        title = r.get("title") or r.get("url") or "Source"
        url = r.get("url") or ""
        if url:
            out.append(f"- [{title}]({url})")
    out.append("")
    out.append("---")
    out.append("💡 Next Steps: Use `scrape_webpage(url)` to fetch full content and code.")
    return "\n".join(out)


def perform_web_search(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Tuple[bool, str]:
    if not query or not query.strip():
        return False, "Error: Empty search query."

    query = query.strip()

    cached = get_cached_result(query, "search")
    if cached:
        return True, _format_search_results(cached, query)

    rate_limiter.wait_if_needed()

    providers_tried: List[str] = []
    results = search_duckduckgo_html(query, max_results=max_results)
    providers_tried.append("duckduckgo-html")
    if not results:
        results = search_duckduckgo_api(query, max_results=max_results)
        providers_tried.append("duckduckgo-api")

    if results:
        cache_result(query, "search", results)
        return True, _format_search_results(results, query)

    # Return a rich “no results” message (success=True so callers can proceed)
    msg = [
        f"# 🔍 Search Results: {query}",
        "",
        "⚠️ **No results were returned by the configured search providers.**",
        "",
        "### Suggestions",
        "1. Add `python`, `docs`, `tutorial` to the query.",
        "2. Try the project name + `github`.",
        "3. If this is a package, run `scrape_readme('<package-name>')`.",
        "",
        "### Diagnostic Info",
        f"- Providers tried: `{', '.join(providers_tried)}`",
        f"- Max results: `{max_results}`",
    ]
    return True, "\n".join(msg)


# =============================================================================
# README scraping (PyPI -> repo link -> GitHub search -> patterns)
# =============================================================================


def is_stub_readme(content: str) -> bool:
    """Intelligent README stub detection.

    - Never flag short READMEs that include real code blocks.
    - Flag "redirect-only" READMEs that mainly point to external documentation,
      even if they are long.
    """
    if not content:
        return True

    text = content.strip()

    # Code blocks mean it's probably real docs.
    if re.search(r"```|~~~", text):
        return False

    if len(text) < 120:
        return True

    lower = text.lower()

    stub_phrases = [
        "see documentation at",
        "please visit",
        "for more information, visit",
        "full documentation at",
        "documentation can be found",
        "refer to the official",
        "visit our website",
        "check out the docs",
        "read the docs",
        "readthedocs",
    ]
    has_stub_phrase = any(p in lower for p in stub_phrases)

    has_structure = bool(
        re.search(
            r"#{1,6}\s*(usage|example|examples|install|installation|quick\s*start|getting\s*started|tutorial|api|features|overview)",
            text,
            re.IGNORECASE,
        )
    )

    # Redirect-only (no structure) should be considered stub regardless of length.
    if has_stub_phrase and not has_structure:
        return True

    # Very short with no structure is usually stub.
    if len(text) < 300:
        return True

    # Short/medium without structure needs at least some "real" keywords.
    if len(text) < 800 and not has_structure:
        keywords = ("install", "usage", "import", "example", "quickstart", "pip", "conda")
        return not any(k in lower for k in keywords)

    return False



def get_pypi_metadata(package_name: str) -> Optional[Dict[str, Any]]:
    try:
        resp = fetch_url(f"https://pypi.org/pypi/{package_name}/json")
        if not resp:
            return None
        data = resp.json()
        info = data.get("info", {}) or {}
        releases = data.get("releases", {}) or {}

        latest_version = info.get("version", "unknown")
        all_versions = sorted(releases.keys(), reverse=True)

        recent_versions: Dict[str, str] = {}
        for ver in all_versions[:5]:
            files = releases.get(ver) or []
            if files:
                upload_time = (files[0] or {}).get("upload_time", "")
                if upload_time:
                    recent_versions[ver] = upload_time

        last_release_date: Optional[datetime] = None
        is_actively_maintained: Optional[bool] = None
        if recent_versions:
            latest_upload = list(recent_versions.values())[0]
            try:
                last_release_date = datetime.fromisoformat(latest_upload.replace("Z", "+00:00"))
                is_actively_maintained = (datetime.now(last_release_date.tzinfo) - last_release_date).days < 730
            except Exception:
                pass

        description = (info.get("description") or "").lower()
        is_deprecated = any(w in description for w in ("deprecated", "no longer maintained", "unmaintained", "superseded"))

        return {
            "package_name": package_name,
            "latest_version": latest_version,
            "python_requires": info.get("requires_python", "Not specified"),
            "recent_versions": recent_versions,
            "is_deprecated": is_deprecated,
            "is_actively_maintained": is_actively_maintained,
            "homepage": info.get("home_page"),
            "docs_url": info.get("docs_url") or (info.get("project_urls") or {}).get("Documentation"),
            "repository": (info.get("project_urls") or {}).get("Source") or (info.get("project_urls") or {}).get("Repository"),
            "license": info.get("license"),
            "author": info.get("author"),
            "summary": info.get("summary"),
        }
    except Exception as exc:
        logger.warning("PyPI metadata failed for %s: %s", package_name, exc)
        return None


def get_github_metadata(repo_url: str) -> Optional[Dict[str, Any]]:
    try:
        m = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
        if not m:
            return None
        owner, repo = m.groups()
        repo = repo.replace(".git", "").rstrip("/")
        token = os.getenv("GITHUB_TOKEN")
        headers = {"User-Agent": BROWSER_HEADERS["User-Agent"], "Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        resp = fetch_url_with_retry(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        data = resp.json()

        commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=1"
        commits_resp = fetch_url_with_retry(commits_url, headers=headers, timeout=REQUEST_TIMEOUT)

        last_commit_date = None
        is_active = False
        if commits_resp.status_code == 200:
            commits_data = commits_resp.json()
            if commits_data:
                last_commit_date = commits_data[0].get("commit", {}).get("author", {}).get("date")
                if last_commit_date:
                    try:
                        commit_dt = datetime.fromisoformat(last_commit_date.replace("Z", "+00:00"))
                        is_active = (datetime.now(commit_dt.tzinfo) - commit_dt).days < 180
                    except Exception:
                        pass

        return {
            "repo_name": f"{owner}/{repo}",
            "description": data.get("description"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "language": data.get("language"),
            "license": (data.get("license") or {}).get("name") if data.get("license") else None,
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "default_branch": data.get("default_branch", "main"),
            "archived": data.get("archived", False),
            "disabled": data.get("disabled", False),
            "last_commit_date": last_commit_date,
            "is_active": is_active,
        }
    except Exception as exc:
        logger.warning("GitHub metadata failed: %s", exc)
        return None


def search_github_repository(package_name: str) -> Optional[str]:
    """Best-effort discovery via GitHub Search API (stars-desc)."""
    try:
        pkg = package_name.lower().strip()
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github.v3+json", "User-Agent": BROWSER_HEADERS["User-Agent"]}
        if token:
            headers["Authorization"] = f"token {token}"

        search_url = "https://api.github.com/search/repositories"
        params = {"q": f"{pkg} in:name", "sort": "stars", "order": "desc", "per_page": 5}
        resp = requests.get(search_url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 403:
            return None
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", []) or []
        if not items:
            return None

        for repo in items:
            name = (repo.get("name") or "").lower()
            full = (repo.get("full_name") or "").lower()
            if name == pkg or full.endswith(f"/{pkg}"):
                return repo.get("html_url")
        return items[0].get("html_url")
    except Exception:
        return None


def fetch_github_readme_direct(repo_url: str) -> Optional[str]:
    """Fetch README via GitHub API (raw), then raw.githubusercontent fallback."""
    try:
        m = re.search(r"github\.com/([^/]+)/([^/]+)", repo_url)
        if not m:
            return None
        owner, repo = m.groups()
        repo = repo.replace(".git", "").rstrip("/")
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github.v3.raw", "User-Agent": BROWSER_HEADERS["User-Agent"]}
        if token:
            headers["Authorization"] = f"token {token}"

        api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        resp = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200 and resp.text:
            return resp.text
        if resp.status_code == 404:
            return None

        # raw fallback (minimal)
        for branch in ("main", "master"):
            for fname in ("README.md", "readme.md", "Readme.md"):
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{fname}"
                raw = fetch_url(raw_url)
                if raw and raw.status_code == 200 and raw.text:
                    return raw.text
        return None
    except Exception:
        return None


def scrape_pypi_readme(package_name: str) -> Optional[str]:
    try:
        resp = fetch_url(f"https://pypi.org/pypi/{package_name}/json")
        if not resp:
            return None
        data = resp.json()
        desc = (data.get("info", {}) or {}).get("description") or ""
        return desc if desc and len(desc) > 100 else None
    except Exception:
        return None


def try_github_patterns(package_name: str) -> Optional[str]:
    pkg = package_name.lower().strip()
    patterns = [
        f"{pkg}/{pkg}",
        f"{pkg}-dev/{pkg}",
        f"python-{pkg}/{pkg}",
        f"google/{pkg}",
        f"dmlc/{pkg}",
    ][:MAX_GITHUB_PATTERNS]

    def _try(pattern: str) -> Optional[str]:
        url = f"https://github.com/{pattern}"
        return fetch_github_readme_direct(url)

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(_try, p): p for p in patterns}
        try:
            for fut in as_completed(futures, timeout=GITHUB_PATTERN_TIMEOUT):
                res = fut.result()
                if res:
                    for f in futures:
                        f.cancel()
                    return res
        except FuturesTimeout:
            for f in futures:
                f.cancel()
    return None


def scrape_readme_smart(package_or_url: str) -> Tuple[bool, str]:
    """
    Returns: (success, formatted_report)

    The formatted report includes:
    - Source (pypi/github)
    - Code Blocks Found
    - LLM-friendly separation of code vs prose
    """
    identifier = (package_or_url or "").strip()
    if not identifier:
        return False, "Error: Empty package or URL"

    cache_key = f"readme:{identifier}"
    cached = get_cached_result(cache_key, "readme")
    if cached:
        readme_content = cached.get("content")
        source = cached.get("source", "cache")
    else:
        readme_content = None
        source = None

        # Direct GitHub URL
        if "github.com" in identifier.lower():
            readme_content = fetch_github_readme_direct(identifier)
            source = "github_direct"
        else:
            pkg = identifier
            # Try PyPI README first
            readme_content = scrape_pypi_readme(pkg)
            if readme_content and is_stub_readme(readme_content):
                readme_content = None

            if readme_content:
                source = "pypi"
            else:
                # Try repo link from PyPI metadata
                meta = get_pypi_metadata(pkg)
                repo = (meta or {}).get("repository") or ""
                if repo and "github.com" in repo:
                    readme_content = fetch_github_readme_direct(repo)
                    source = "github_from_pypi"

            if not readme_content:
                repo_url = search_github_repository(pkg)
                if repo_url:
                    readme_content = fetch_github_readme_direct(repo_url)
                    source = "github_search_api"

            if not readme_content:
                readme_content = try_github_patterns(pkg)
                if readme_content:
                    source = "github_pattern"

        if readme_content:
            if len(readme_content) > MAX_README_SIZE:
                readme_content = readme_content[:MAX_README_SIZE] + "\n\n[... truncated for size ...]"
            cache_result(cache_key, "readme", {"content": readme_content, "source": source})

    if not readme_content:
        error_msg = [
            f"❌ Could not find README for: {identifier}",
            "",
            "**Attempted sources:**",
            "• PyPI (description)",
            "• PyPI metadata (repo link)",
            "• GitHub search API",
            "• Common GitHub patterns",
            "",
            "**Suggestions:**",
            f"1. Use: search_web('{identifier} python documentation')",
            f"2. Use: search_web('{identifier} github')",
        ]
        # Hyphen/underscore variants
        if "-" in identifier or "_" in identifier:
            vars_: List[str] = []
            if "-" in identifier:
                vars_.append(identifier.replace("-", "_"))
            if "_" in identifier:
                vars_.append(identifier.replace("_", "-"))
            if vars_:
                error_msg.append("")
                error_msg.append("**Try alternative spellings:**")
                for v in vars_:
                    error_msg.append(f"• scrape_readme('{v}')")
        return False, "\n".join(error_msg)

    code_blocks = CodeDetector.extract_from_markdown(readme_content)
    output = [
        f"# README for: {identifier}",
        f"Source: {source}",
        f"Length: {len(readme_content):,} characters",
        f"Code Blocks Found: {len(code_blocks)}",
        "",
        "---",
        "",
        CodeDetector.format_for_llm(readme_content, code_blocks),
    ]
    return True, "\n".join(output)


# =============================================================================
# Webpage scraping (preserve code indentation)
# =============================================================================


def scrape_webpage_smart(url: str) -> str:
    ok, msg = validate_url(url)
    if not ok:
        return f"Error: {msg}"

    resp = fetch_url(url, validate=False)
    if not resp:
        return f"Error: Could not fetch {url}"

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "iframe", "svg", "header"]):
        tag.decompose()

    code_blocks = CodeDetector.extract_from_html(soup)
    prose = soup.get_text(separator="\n", strip=True)
    return CodeDetector.format_for_llm(prose, code_blocks, source_url=url)


# =============================================================================
# Deprecation detection
# =============================================================================

def detect_deprecated_features(readme_content: str, package_name: str) -> Dict[str, Any]:
    """Detect deprecated APIs referenced in documentation with severity levels."""
    readme_lower = (readme_content or "").lower()

    known_deprecations: Dict[str, List[str]] = {
        "scikit-learn": ["load_boston", "fetch_mldata", "sklearn.cross_validation"],
        "pandas": ["append", "ix", "panel", ".as_matrix"],
        "tensorflow": ["tf.session", "tf.placeholder", "tf.contrib"],
        "numpy": ["np.matrix", "np.asmatrix"],
        "xgboost": ["get_fscore"],
        "keras": ["keras.layers.merge", "keras.engine"],
    }

    detected: List[Dict[str, Any]] = []
    target_norm = (package_name or "").lower().replace("-", "").replace("_", "")

    for lib, items in known_deprecations.items():
        lib_norm = lib.lower().replace("-", "").replace("_", "")
        is_target = lib_norm in target_norm or target_norm in lib_norm

        for item in items:
            if item.lower() in readme_lower:
                detected.append(
                    {
                        "library": lib,
                        "item": item,
                        "severity": "CRITICAL" if is_target else "WARNING",
                        "message": f"{'Target package' if is_target else 'Dependency'} uses deprecated: {item}",
                    }
                )

    deprecation_sections: List[Dict[str, Any]] = []
    lines = (readme_content or "").splitlines()
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in ("deprecated", "deprecation", "no longer supported", "removed in")):
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            deprecation_sections.append(
                {"line_number": i + 1, "text": line.strip(), "context": "\n".join(lines[start:end])}
            )

    critical = [d for d in detected if d["severity"] == "CRITICAL"]
    warnings = [d for d in detected if d["severity"] == "WARNING"]
    has_deprecations = bool(deprecation_sections or detected)

    return {
        "has_deprecation_warnings": has_deprecations,
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "critical_items": critical,
        "warning_items": warnings,
        "deprecation_sections": deprecation_sections[:5],
        "recommendation": (
            "⚠️ CRITICAL: Avoid deprecated features in target package"
            if critical
            else "⚠️ WARNING: Examples use deprecated features from dependencies"
            if warnings
            else "✅ No major deprecation warnings found"
        ),
    }

# =============================================================================
# Package health report (blog-friendly)
# =============================================================================


def _extract_python_blocks_for_validation(markdown_text: str) -> List[str]:
    return re.findall(r"```python\n(.*?)```", markdown_text, flags=re.DOTALL | re.IGNORECASE)


def get_package_health_report(package_or_url: str) -> Tuple[bool, str]:
    """High-level report combining metadata and a few extracted examples."""
    identifier = (package_or_url or "").strip()
    if not identifier:
        return False, "Error: Empty package or URL"

    report: List[str] = []
    report.append(f"# 📊 Package Health Report: {identifier}")
    report.append("=" * 70)
    report.append("")
    is_github = "github.com" in identifier.lower()

    success, readme_report = scrape_readme_smart(identifier)
    if not success:
        return False, f"❌ Failed to retrieve README for {identifier}\n\n{readme_report}"

    # Extract raw README content part for analysis (best effort)
    readme_content = readme_report
    if "---\n\n" in readme_report:
        readme_content = readme_report.split("---\n\n", 1)[-1]

    pypi_meta = None if is_github else get_pypi_metadata(identifier)
    github_meta = None

    if pypi_meta:
        report.append("## 📦 PyPI Package Information")
        report.append(f"Package: {pypi_meta.get('package_name')}")
        report.append(f"Latest Version: {pypi_meta.get('latest_version')}")
        report.append(f"Python: {pypi_meta.get('python_requires')}")
        lic = pypi_meta.get("license") or "Not specified"
        report.append(f"License: {lic[:80] + ('...' if len(lic) > 80 else '')}")
        if pypi_meta.get("is_deprecated"):
            report.append("\n🚨 CRITICAL WARNING: Package appears deprecated")
        report.append("")
        repo = pypi_meta.get("repository") or ""
        if repo and "github.com" in repo:
            github_meta = get_github_metadata(repo)

    if is_github and not github_meta:
        github_meta = get_github_metadata(identifier)

    if github_meta:
        report.append("## 🐙 GitHub Repository")
        report.append(f"Repository: {github_meta.get('repo_name')}")
        report.append(f"Stars: ⭐ {github_meta.get('stars', 0):,}")
        if github_meta.get("archived"):
            report.append("\n🚨 CRITICAL: Repository is archived (read-only)")
        report.append("")
    report.append("## 💻 Code Examples")
    blocks = CodeDetector.extract_from_markdown(readme_content)
    report.append(f"Total Blocks Found: {len(blocks)}")

    # Show a small, useful subset
    python_blocks = [b for b in blocks if (b.get("language") or "").lower() in {"python", "py", "python3", "py3"}]
    install_blocks = [b for b in blocks if (b.get("language") or "").lower() in {"bash", "sh", "shell", "console", "terminal"}]

    report.append(f"- Python: {len(python_blocks)}")
    report.append(f"- Setup:  {len(install_blocks)}")
    report.append("")
    report.append("### Extracted Examples")
    show: List[Dict[str, Any]] = []
    if install_blocks:
        show.append(install_blocks[0])
    show.extend(python_blocks[:3] if python_blocks else blocks[:3])

    for b in show:
        lang = b.get("language") or "text"
        code = b.get("code") or ""
        report.append(f"\nExample {b.get('index')} ({lang})")
        report.append(f"```{lang}\n{code}\n```")
    report.append("")
    report.append("=" * 70)

    return True, "\n".join(report)


# =============================================================================
# Tool input normalization (CrewAI Action Input compatibility)
# =============================================================================


def _normalize_tool_input(arg: Any, key: str) -> str:
    if isinstance(arg, dict):
        return str(arg.get(key) if key in arg else arg)
    if isinstance(arg, str):
        s = arg.strip()
        try:
            data = json.loads(s)
            if isinstance(data, dict) and key in data:
                return str(data[key])
        except Exception:
            return s
        return s
    return str(arg)


# =============================================================================
# Tool implementations (what CrewAI wraps)
# =============================================================================


def search_web_impl(query: str) -> str:
    q = _normalize_tool_input(query, "query")
    _success, result = perform_web_search(q)
    return result


def scrape_webpage_impl(url: str) -> str:
    u = _normalize_tool_input(url, "url")
    return scrape_webpage_smart(u)


def scrape_readme_impl(package_or_url: str) -> str:
    identifier = _normalize_tool_input(package_or_url, "package_or_url")
    _success, result = scrape_readme_smart(identifier)
    return result


def get_package_health_impl(package_or_url: str) -> str:
    identifier = _normalize_tool_input(package_or_url, "package_or_url")
    _success, result = get_package_health_report(identifier)
    return result


# =============================================================================
# Exported tools
# =============================================================================

search_web = create_crewai_tool(
    func=search_web_impl,
    tool_name="search_web",
    tool_description="Search the web for programming tutorials and documentation. Returns formatted results with titles, URLs, and summaries.",
)

scrape_webpage = create_crewai_tool(
    func=scrape_webpage_impl,
    tool_name="scrape_webpage",
    tool_description="Scrape a webpage and extract code examples with preserved formatting. Returns content with code blocks prominently displayed.",
)

scrape_readme = create_crewai_tool(
    func=scrape_readme_impl,
    tool_name="scrape_readme",
    tool_description="Extract README from PyPI packages or GitHub repositories with smart fallback and code extraction.",
)

get_package_health = create_crewai_tool(
    func=get_package_health_impl,
    tool_name="get_package_health",
    tool_description="Generate a blog-friendly health report for a Python package or GitHub repo, including versions, activity hints, and example code.",
)


# =============================================================================
# CLI
# =============================================================================

def main() -> None:
    import sys

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if len(sys.argv) < 3:
        print("Usage:")
        print("  python scripts/search.py search <query>")
        print("  python scripts/search.py readme <package-or-github-url>")
        print("  python scripts/search.py health <package-or-github-url>")
        print("  python scripts/search.py scrape <url>")
        raise SystemExit(1)

    command = sys.argv[1].strip().lower()
    query = " ".join(sys.argv[2:]).strip()

    print("=" * 70)
    if command == "health":
        success, result = get_package_health_report(query)
        print(result)
        raise SystemExit(0 if success else 1)
    if command == "readme":
        success, result = scrape_readme_smart(query)
        print(result)
        raise SystemExit(0 if success else 1)
    if command == "scrape":
        print(scrape_webpage_smart(query))
        raise SystemExit(0)
    # default: search
    success, result = perform_web_search(query)
    print(result)
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
