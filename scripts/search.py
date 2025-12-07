#!/usr/bin/env python3
"""
scripts/search.py - PRODUCTION READY v3.1
Enhanced Web Search & Package Analysis Tool for CrewAI Blog Generation

🔧 CRITICAL FIXES IMPLEMENTED:
  - Issue #1: Robust regex with whitespace tolerance + multi-language support
  - Issue #2: Smart stub detection via content analysis (not length)
  - Issue #3: Preserves code indentation during HTML scraping
  - Infinite loop fix: Smart retry (no 404 retries)
  - Thread-safe rate limiting
  - SSRF protection
  - Optimized GitHub pattern checking

📦 Dependencies:
    pip install requests beautifulsoup4 crewai-tools tenacity

🚀 Usage:
    from search import search_web, scrape_webpage, scrape_readme, get_package_health
    
    researcher = Agent(
        role="Research Specialist",
        tools=[search_web, scrape_webpage, scrape_readme, get_package_health],
        ...
    )
"""

import hashlib
import json
import logging
import os
import re
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception
)

# CrewAI Tool Decorator (Compatible with latest versions)
try:
    from crewai.tools import tool
    CREWAI_AVAILABLE = True
except ImportError:
    try:
        from crewai_tools import tool
        CREWAI_AVAILABLE = True
    except ImportError:
        CREWAI_AVAILABLE = False
        def tool(func_or_description):
            """Fallback tool decorator that handles both @tool and @tool('desc') syntax"""
            def decorator(func):
                func.name = func.__name__
                func.description = getattr(func, '__doc__', '') or 'No description'
                return func
            
            # Handle @tool syntax (function passed directly)
            if callable(func_or_description):
                return decorator(func_or_description)
            # Handle @tool('description') syntax
            else:
                return decorator

# ============================================================================
# CONFIGURATION
# ============================================================================

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "search_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_VERSION = "v3.1"  # Increment when changing scraping logic
CACHE_DURATION_HOURS = int(os.getenv("SEARCH_CACHE_HOURS", "24"))
MAX_RESULTS_PER_SEARCH = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
REQUEST_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "15"))
RATE_LIMIT = int(os.getenv("SEARCH_RATE_LIMIT", "10"))
MAX_README_SIZE = int(os.getenv("MAX_README_SIZE", "1048576"))  # 1MB

# CRITICAL FIX: Reduced limits to prevent infinite loops
MAX_GITHUB_PATTERNS = int(os.getenv("MAX_GITHUB_PATTERNS", "5"))
GITHUB_PATTERN_TIMEOUT = int(os.getenv("GITHUB_PATTERN_TIMEOUT", "20"))  # 20s total
MAX_BRANCH_TRIES = 2  # Only try main and master

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Security: Allowed domains for URL fetching (SSRF protection)
ALLOWED_DOMAINS = {
    'github.com',
    'raw.githubusercontent.com',
    'pypi.org',
    'files.pythonhosted.org',
    'readthedocs.io',
    'readthedocs.org',
    'githubusercontent.com',
    'docs.python.org',
}

logger = logging.getLogger(__name__)


# ============================================================================
# SMART RETRY LOGIC - CRITICAL FIX FOR INFINITE LOOP
# ============================================================================

def should_retry_request(exception) -> bool:
    """
    CRITICAL FIX: Only retry transient errors, NOT client errors (404, 403, etc.)
    
    Retry on:
    - Network timeouts
    - Connection errors
    - Server errors (500-599)
    - Rate limits (429)
    
    DON'T retry on:
    - 404 Not Found (will NEVER succeed)
    - 403 Forbidden
    - 400 Bad Request
    - Any other 4xx errors
    """
    # Timeout errors - always retry
    if isinstance(exception, (requests.Timeout, requests.ConnectTimeout, requests.ReadTimeout)):
        return True
    
    # Connection errors - always retry
    if isinstance(exception, requests.ConnectionError):
        return True
    
    # HTTP errors - only retry server errors
    if isinstance(exception, requests.HTTPError):
        if hasattr(exception, 'response') and exception.response is not None:
            status_code = exception.response.status_code
            # Only retry 5xx (server errors) and 429 (rate limit)
            return status_code >= 500 or status_code == 429
        return False
    
    # Don't retry other exceptions
    return False


@retry(
    retry=retry_if_exception(should_retry_request),
    stop=stop_after_attempt(2),  # Reduced from 3 to 2 attempts
    wait=wait_exponential(multiplier=1, min=1, max=5),  # Faster backoff
    reraise=True
)
def fetch_url_with_retry(url: str, headers: Dict[str, str] = None) -> requests.Response:
    """Fetch URL with smart retry on transient errors only"""
    if headers is None:
        headers = {"User-Agent": USER_AGENT}
    
    response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response


def fetch_url(url: str, validate: bool = True) -> Optional[requests.Response]:
    """
    Safe URL fetching with validation and smart retry
    
    CRITICAL FIX: Returns None on 404 immediately (no retry spam in logs)
    """
    if validate:
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            logger.debug(f"URL validation failed: {error_msg}")
            return None
    
    try:
        return fetch_url_with_retry(url)
    except requests.HTTPError as e:
        # Log 404s at DEBUG level (expected for pattern matching)
        if e.response and e.response.status_code == 404:
            logger.debug(f"404: {url}")
        else:
            status = e.response.status_code if e.response else 'unknown'
            logger.warning(f"HTTP {status}: {url}")
        return None
    except requests.Timeout:
        logger.warning(f"Timeout: {url}")
        return None
    except requests.RequestException as e:
        logger.debug(f"Request failed: {url} - {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {url} - {e}")
        return None


# ============================================================================
# THREAD-SAFE RATE LIMITER
# ============================================================================

class RateLimiter:
    """Thread-safe rate limiter with sliding window"""
    
    def __init__(self, calls_per_minute: int = RATE_LIMIT):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded"""
        with self.lock:
            now = time.time()
            self.calls = [t for t in self.calls if now - t < 60]
            
            if len(self.calls) >= self.calls_per_minute:
                sleep_time = 60 - (now - self.calls[0]) + 1
                if sleep_time > 0:
                    logger.info(f"⏱️  Rate limit: waiting {sleep_time:.1f}s")
                    time.sleep(sleep_time)
            
            self.calls.append(now)


rate_limiter = RateLimiter()


# ============================================================================
# CACHING WITH VERSIONING
# ============================================================================

def get_cache_key(query: str, provider: str) -> str:
    """Generate cache key with version prefix"""
    combined = f"{CACHE_VERSION}:{provider}:{query.lower().strip()}"
    return hashlib.sha256(combined.encode()).hexdigest()


def get_cached_result(query: str, provider: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached result if available and fresh"""
    cache_key = get_cache_key(query, provider)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with cache_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check version
        if data.get("version") != CACHE_VERSION:
            cache_file.unlink()
            return None
        
        cached_time = datetime.fromisoformat(data.get("timestamp", ""))
        if datetime.now() - cached_time < timedelta(hours=CACHE_DURATION_HOURS):
            logger.info(f"💾 Cache hit: {query[:50]}...")
            return data.get("results")
        else:
            cache_file.unlink()
            
    except Exception as e:
        logger.warning(f"Cache read error: {e}")
    
    return None


def cache_result(query: str, provider: str, results: List[Dict[str, Any]]) -> None:
    """Cache search results with version"""
    cache_key = get_cache_key(query, provider)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    try:
        data = {
            "version": CACHE_VERSION,
            "query": query,
            "provider": provider,
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        with cache_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
    except Exception as e:
        logger.warning(f"Cache write error: {e}")


# ============================================================================
# SECURITY: URL VALIDATION
# ============================================================================

def validate_url(url: str, allow_private: bool = False) -> Tuple[bool, str]:
    """
    Validate URL to prevent SSRF attacks
    
    Args:
        url: URL to validate
        allow_private: If False, reject private/internal IPs
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme not in ['http', 'https']:
            return False, f"Invalid scheme: {parsed.scheme}"
        
        # Check domain whitelist
        if parsed.netloc not in ALLOWED_DOMAINS:
            # Allow subdomains of allowed domains
            is_allowed = any(
                parsed.netloc.endswith(f'.{domain}') 
                for domain in ALLOWED_DOMAINS
            )
            if not is_allowed:
                return False, f"Domain not allowed: {parsed.netloc}"
        
        # Check for private IPs (basic check)
        if not allow_private:
            hostname = parsed.hostname
            if hostname:
                # Block localhost and private ranges
                private_patterns = [
                    r'^localhost$',
                    r'^127\.',
                    r'^10\.',
                    r'^172\.(1[6-9]|2[0-9]|3[01])\.',
                    r'^192\.168\.',
                    r'^169\.254\.',
                ]
                for pattern in private_patterns:
                    if re.match(pattern, hostname):
                        return False, f"Private IP not allowed: {hostname}"
        
        return True, ""
        
    except Exception as e:
        return False, f"URL validation error: {e}"


# ============================================================================
# 🧠 CORE ENGINE: SEMANTIC CODE DETECTOR (FIX FOR ISSUE #1 & #3)
# ============================================================================

class CodeDetector:
    """
    Advanced code extraction that fixes:
    - Issue #1: Whitespace-tolerant regex with multi-language support
    - Issue #3: Preserves indentation during HTML scraping
    """
    
    # Comprehensive language tags for code blocks
    CODE_LANGUAGES = {
        'python', 'py', 'python3', 'py3',
        'bash', 'sh', 'shell', 'console', 'terminal',
        'javascript', 'js', 'typescript', 'ts',
        'java', 'c', 'cpp', 'c++', 'csharp', 'c#',
        'ruby', 'rb', 'go', 'rust', 'php',
        'sql', 'json', 'yaml', 'yml', 'xml', 'html', 'css',
        'r', 'matlab', 'julia', 'scala', 'kotlin',
        'text', 'txt', 'plaintext', 'output'
    }
    
    @staticmethod
    def extract_from_markdown(text: str, min_lines: int = 1) -> List[Dict[str, str]]:
        """
        FIX FOR ISSUE #1: Robustly extracts code with whitespace tolerance
        
        Handles:
        - ```python with/without spaces
        - ~~~ fences
        - \r\n line endings
        - Missing language tags
        - Installation commands (bash/console)
        """
        code_blocks = []
        
        # Pattern breakdown:
        # (?P<fence>```|~~~)     - Capture fence type
        # (?P<lang>[\w\+\-\#\.]*) - Optional language (allows python, c++, c#, etc.)
        # \s*                     - CRITICAL: Tolerates trailing whitespace after lang tag
        # (?:\r?\n|\r)            - Handles Windows (\r\n), Unix (\n), or Mac (\r)
        # (?P<code>.*?)           - Non-greedy code content
        # (?:\r?\n|\r)            - Line ending before closing fence
        # \s*(?P=fence)           - Closing fence (with optional leading whitespace)
        
        pattern = r'(?P<fence>```|~~~)(?P<lang>[\w\+\-\#\.]*)?\s*(?:\r?\n|\r)(?P<code>.*?)(?:\r?\n|\r)\s*(?P=fence)'
        
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for i, match in enumerate(matches, 1):
            lang = (match.group('lang') or '').strip().lower()
            code = match.group('code')
            
            # Skip empty blocks
            if not code.strip():
                continue
            
            # Filter by minimum lines
            if len(code.split('\n')) < min_lines:
                continue
            
            # Smart language detection for untagged blocks
            if not lang or lang not in CodeDetector.CODE_LANGUAGES:
                lang = CodeDetector._detect_language(code)
            
            code_blocks.append({
                "index": i,
                "language": lang,
                "code": code,  # Preserves original indentation
                "lines": len(code.split('\n')),
                "source": "markdown_fence"
            })
        
        logger.info(f"📝 Extracted {len(code_blocks)} code blocks from markdown")
        return code_blocks
    
    @staticmethod
    def _detect_language(code: str) -> str:
        """Heuristically detect programming language"""
        code_lower = code.lower()
        
        # Python indicators
        if any(k in code for k in ['def ', 'import ', 'from ', 'class ', 'print(', 'self.']):
            return 'python'
        
        # Bash/Shell indicators
        if any(k in code for k in ['#!/bin/bash', '#!/bin/sh', 'sudo ', 'apt-get', 'pip install', 'npm install']):
            return 'bash'
        
        # JavaScript indicators
        if any(k in code for k in ['function ', 'const ', 'let ', 'var ', '=>', 'console.log']):
            return 'javascript'
        
        # Installation commands (often untagged)
        if re.match(r'^(pip|npm|yarn|cargo|go get|composer)', code.strip(), re.MULTILINE):
            return 'console'
        
        return 'text'
    
    @staticmethod
    def extract_from_html(soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        FIX FOR ISSUE #3: Preserves code indentation during HTML extraction
        
        Uses get_text() WITHOUT collapsing whitespace
        """
        code_blocks = []
        index = 1
        
        # Strategy 1: <pre><code> blocks (standard for syntax highlighting)
        for pre in soup.find_all('pre'):
            code_elem = pre.find('code')
            text_elem = code_elem if code_elem else pre
            
            # CRITICAL FIX: separator='\n' preserves line structure
            # strip=False preserves leading/trailing whitespace (indentation)
            code_text = text_elem.get_text(separator='\n', strip=False)
            
            if not code_text.strip():
                continue
            
            # Detect language from class attributes
            lang = CodeDetector._extract_language_from_classes(pre, code_elem)
            
            code_blocks.append({
                "index": index,
                "language": lang,
                "code": code_text,  # Indentation preserved!
                "lines": len(code_text.split('\n')),
                "source": "html_pre"
            })
            index += 1
        
        # Strategy 2: Standalone <code> (inline code, usually skip but include if multi-line)
        for code in soup.find_all('code'):
            # Skip if already processed in <pre>
            if code.find_parent('pre'):
                continue
            
            code_text = code.get_text(separator='\n', strip=False)
            
            # Only include multi-line code blocks
            if '\n' in code_text and len(code_text.strip()) > 20:
                lang = CodeDetector._extract_language_from_classes(None, code)
                
                code_blocks.append({
                    "index": index,
                    "language": lang,
                    "code": code_text,
                    "lines": len(code_text.split('\n')),
                    "source": "html_code"
                })
                index += 1
        
        logger.info(f"🔍 Extracted {len(code_blocks)} code blocks from HTML")
        return code_blocks
    
    @staticmethod
    def _extract_language_from_classes(pre_elem, code_elem) -> str:
        """Extract language from HTML class attributes"""
        classes = []
        if pre_elem:
            classes.extend(pre_elem.get('class', []))
        if code_elem:
            classes.extend(code_elem.get('class', []))
        
        for cls in classes:
            cls_lower = str(cls).lower()
            # Matches: language-python, lang-py, highlight-python, python, etc.
            if 'lang' in cls_lower or 'highlight' in cls_lower:
                parts = re.split(r'[-_]', cls_lower)
                for part in parts:
                    if part in CodeDetector.CODE_LANGUAGES:
                        return part
            elif cls_lower in CodeDetector.CODE_LANGUAGES:
                return cls_lower
        
        return 'text'
    
    @staticmethod
    def format_for_llm(context_text: str, code_blocks: List[Dict], source_url: str = "") -> str:
        """
        Format output to make code blocks highly visible to LLM
        Prevents hallucination by explicit code presence signaling
        """
        output = []
        
        if source_url:
            output.append(f"# Content from: {source_url}")
            output.append("")
        
        if not code_blocks:
            output.append("⚠️ [SYSTEM: NO CODE BLOCKS DETECTED IN SOURCE]")
            output.append("=" * 70)
            output.append("")
            output.append("[DOCUMENT CONTEXT]")
            # Still provide context, but flag lack of code
            clean_text = re.sub(r'\n{3,}', '\n\n', context_text)
            output.append(clean_text[:4000])
            return "\n".join(output)
        
        # CODE BLOCKS FOUND - Present them prominently
        output.append(f"✅ **FOUND {len(code_blocks)} CODE BLOCKS IN SOURCE**")
        output.append("=" * 70)
        output.append("")
        
        # Categorize by type
        python_blocks = [b for b in code_blocks if 'python' in b['language'] or 'py' in b['language']]
        install_blocks = [b for b in code_blocks if b['language'] in ['bash', 'console', 'shell']]
        other_blocks = [b for b in code_blocks if b not in python_blocks and b not in install_blocks]
        
        # Present Python code first (highest priority for blog)
        if python_blocks:
            output.append("## 🐍 Python Code Examples")
            for block in python_blocks:
                output.append(f"\n### Block {block['index']} ({block['lines']} lines)")
                output.append(f"```python\n{block['code']}\n```")
                output.append("")
        
        # Installation/Setup commands
        if install_blocks:
            output.append("## 📦 Installation/Setup Commands")
            for block in install_blocks:
                output.append(f"\n### Block {block['index']}")
                output.append(f"```bash\n{block['code']}\n```")
                output.append("")
        
        # Other code
        if other_blocks:
            output.append("## 📝 Other Code/Examples")
            for block in other_blocks:
                output.append(f"\n### Block {block['index']} ({block['language']})")
                output.append(f"```{block['language']}\n{block['code']}\n```")
                output.append("")
        
        # Context (truncated)
        output.append("=" * 70)
        output.append("[DOCUMENT CONTEXT - Prose/Explanations]")
        clean_text = re.sub(r'\n{3,}', '\n\n', context_text)
        output.append(clean_text[:3000])  # Reduced since code is already extracted
        
        return "\n".join(output)


# ============================================================================
# SMART STUB DETECTION (FIX FOR ISSUE #2)
# ============================================================================

def is_stub_readme(content: str) -> bool:
    """
    FIX FOR ISSUE #2: Intelligent stub detection via content analysis
    
    A README is considered a "stub" if:
    1. Very short (<300 chars) OR
    2. Lacks structural headers AND code blocks AND contains stub indicators
    
    This replaces the naive length-only check.
    """
    if not content or len(content.strip()) < 100:
        return True
    
    content_lower = content.lower()
    
    # Stub indicators (redirects to external docs)
    stub_phrases = [
        'see documentation at',
        'please visit',
        'for more information, visit',
        'full documentation at',
        'readme available at',
        'documentation can be found',
        'refer to the official',
        'visit our website',
        'check out the docs',
    ]
    
    has_stub_phrase = any(phrase in content_lower for phrase in stub_phrases)
    
    # Structural headers indicate real documentation
    has_structure = bool(re.search(
        r'#{1,6}\s*(usage|example|install|quick\s*start|getting\s*started|tutorial|api|features|overview)',
        content,
        re.IGNORECASE
    ))
    
    # Code blocks indicate real documentation
    has_code = bool(re.search(r'```|~~~', content))
    
    # FIXED: Decision logic with better thresholds
    content_len = len(content)
    
    # Very short - always stub unless it has code
    if content_len < 300:
        return not has_code
    
    # Short (300-800) - stub if no structure AND no code
    if content_len < 800:
        # If it has either structure OR code, it's valid
        if has_structure or has_code:
            return False
        # If it has stub phrases and nothing useful, it's a stub
        if has_stub_phrase:
            return True
        # No structure, no code, but also no redirect - could be minimal but valid
        return not any(word in content_lower for word in ['install', 'usage', 'import', 'example'])
    
    # Medium length (800-1500) - stub if has redirect phrase but no code
    if content_len < 1500:
        if has_code:
            return False
        if has_stub_phrase and not has_structure:
            return True
        return False
    
    # Long content - never a stub
    return False


# ============================================================================
# PYPI & GITHUB METADATA
# ============================================================================

def get_pypi_metadata(package_name: str) -> Optional[Dict[str, Any]]:
    """Get comprehensive PyPI package metadata"""
    try:
        api_url = f"https://pypi.org/pypi/{package_name}/json"
        response = fetch_url(api_url)
        
        if not response:
            return None
        
        data = response.json()
        info = data.get("info", {})
        releases = data.get("releases", {})
        
        latest_version = info.get("version", "unknown")
        all_versions = sorted(releases.keys(), reverse=True) if releases else []
        
        # Get upload dates
        recent_versions = {}
        for version in all_versions[:5]:
            if version in releases and releases[version]:
                upload_time = releases[version][0].get("upload_time", "")
                recent_versions[version] = upload_time
        
        # Check if actively maintained
        last_release_date = None
        is_actively_maintained = None
        if recent_versions:
            latest_upload = list(recent_versions.values())[0]
            if latest_upload:
                try:
                    last_release_date = datetime.fromisoformat(latest_upload.replace("Z", "+00:00"))
                    days_since_release = (datetime.now(last_release_date.tzinfo) - last_release_date).days
                    is_actively_maintained = days_since_release < 730
                except:
                    pass
        
        # Check for deprecation
        description = info.get("description", "").lower()
        is_deprecated = any(word in description for word in [
            "deprecated", "no longer maintained", "unmaintained",
            "use instead", "migrated to", "superseded by"
        ])
        
        metadata = {
            "package_name": package_name,
            "latest_version": latest_version,
            "python_requires": info.get("requires_python", "Not specified"),
            "all_versions": all_versions[:10],
            "recent_versions": recent_versions,
            "is_deprecated": is_deprecated,
            "is_actively_maintained": is_actively_maintained,
            "homepage": info.get("home_page"),
            "docs_url": info.get("docs_url") or info.get("project_urls", {}).get("Documentation"),
            "repository": info.get("project_urls", {}).get("Source") or info.get("project_urls", {}).get("Repository"),
            "license": info.get("license"),
            "author": info.get("author"),
            "summary": info.get("summary"),
        }
        
        logger.info(f"📊 PyPI: {package_name} v{latest_version}")
        return metadata
        
    except Exception as e:
        logger.warning(f"PyPI metadata failed for {package_name}: {e}")
        return None


def get_github_metadata(repo_url: str) -> Optional[Dict[str, Any]]:
    """Get GitHub repository health metrics"""
    try:
        match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            return None
        
        owner, repo = match.groups()
        repo = repo.replace('.git', '')
        
        github_token = os.getenv("GITHUB_TOKEN")
        headers = {"User-Agent": USER_AGENT}
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = fetch_url_with_retry(api_url, headers=headers)
        data = response.json()
        
        # Get recent commits
        commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        commits_response = fetch_url_with_retry(commits_url + "?per_page=1", headers=headers)
        
        last_commit_date = None
        is_active = False
        if commits_response.status_code == 200:
            commits_data = commits_response.json()
            if commits_data:
                last_commit_date = commits_data[0].get("commit", {}).get("author", {}).get("date")
                if last_commit_date:
                    try:
                        commit_date = datetime.fromisoformat(last_commit_date.replace("Z", "+00:00"))
                        days_since_commit = (datetime.now(commit_date.tzinfo) - commit_date).days
                        is_active = days_since_commit < 180
                    except:
                        pass
        
        metadata = {
            "repo_name": f"{owner}/{repo}",
            "description": data.get("description"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "language": data.get("language"),
            "license": data.get("license", {}).get("name") if data.get("license") else None,
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "last_commit_date": last_commit_date,
            "is_active": is_active,
            "default_branch": data.get("default_branch", "main"),
            "archived": data.get("archived", False),
            "disabled": data.get("disabled", False),
        }
        
        logger.info(f"🐙 GitHub: {owner}/{repo} - {metadata['stars']} stars")
        return metadata
        
    except Exception as e:
        logger.warning(f"GitHub metadata failed: {e}")
        return None


# ============================================================================
# README SCRAPING - CRITICAL FIX FOR INFINITE LOOP
# ============================================================================

def scrape_pypi_readme(package_name: str) -> Optional[str]:
    """Scrape README from PyPI"""
    try:
        api_url = f"https://pypi.org/pypi/{package_name}/json"
        response = fetch_url(api_url)
        
        if not response:
            return None
        
        data = response.json()
        description = data.get("info", {}).get("description", "")
        
        if description and len(description) > 100:
            logger.info(f"📦 PyPI: Got README for {package_name} ({len(description)} chars)")
            return description
        
        return None
        
    except Exception as e:
        logger.debug(f"PyPI README failed for {package_name}: {e}")
        return None


def scrape_github_readme(repo_url: str) -> Optional[str]:
    """
    Scrape README from GitHub with MINIMAL attempts
    
    CRITICAL FIX: Only tries main/master + README.md to prevent infinite loops
    """
    try:
        match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            return None
        
        owner, repo = match.groups()
        repo = repo.replace('.git', '')
        
        github_token = os.getenv("GITHUB_TOKEN")
        headers = {"User-Agent": USER_AGENT}
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        # Strategy 1: GitHub API (most reliable)
        api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        response = fetch_url(api_url)
        
        if response and response.status_code == 200:
            data = response.json()
            download_url = data.get("download_url")
            if download_url:
                readme_response = fetch_url(download_url)
                if readme_response:
                    logger.info(f"🐙 GitHub API: Got README for {owner}/{repo}")
                    return readme_response.text
        
        # Strategy 2: Raw URLs (ONLY main/master + README.md)
        # CRITICAL FIX: Limited to 4 attempts total (2 branches × 2 files)
        attempts = [
            ('main', 'README.md'),
            ('master', 'README.md'),
            ('main', 'readme.md'),
            ('master', 'readme.md'),
        ]
        
        for branch, filename in attempts:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{filename}"
            response = fetch_url(raw_url)
            if response and response.status_code == 200:
                logger.info(f"🐙 GitHub Raw: Got {filename} from {branch}")
                return response.text
        
        # If still not found, repository likely doesn't have a README
        logger.debug(f"No README found for {owner}/{repo}")
        return None
        
    except Exception as e:
        logger.debug(f"GitHub README failed for {repo_url}: {e}")
        return None


def try_github_patterns(package_name: str) -> Optional[str]:
    """
    CRITICAL FIX: Limited GitHub pattern checking with timeout
    
    Reduced from 10 patterns to 5, with 20-second timeout
    """
    clean_name = package_name.lower().strip()
    
    # CRITICAL FIX: Only 5 most common patterns
    patterns = [
        f"{clean_name}/{clean_name}",
        f"dmlc/{clean_name}",
        f"google/{clean_name}",
        f"python-{clean_name}/{clean_name}",
        f"{clean_name}-dev/{clean_name}",
    ][:MAX_GITHUB_PATTERNS]
    
    logger.info(f"🔍 Trying {len(patterns)} GitHub patterns for {package_name} (max {GITHUB_PATTERN_TIMEOUT}s)...")
    
    def try_pattern(pattern: str) -> Optional[Tuple[str, str]]:
        """Try a single pattern"""
        url = f"https://github.com/{pattern}"
        readme = scrape_github_readme(url)
        if readme:
            return (pattern, readme)
        return None
    
    # CRITICAL FIX: Parallel with timeout
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(try_pattern, pattern): pattern for pattern in patterns}
        
        try:
            for future in as_completed(futures, timeout=GITHUB_PATTERN_TIMEOUT):
                result = future.result()
                if result:
                    pattern, readme = result
                    logger.info(f"✅ Found GitHub README at: {pattern}")
                    # Cancel remaining
                    for f in futures:
                        f.cancel()
                    return readme
        except TimeoutError:
            logger.warning(f"⏱️  GitHub pattern search timed out after {GITHUB_PATTERN_TIMEOUT}s")
            for f in futures:
                f.cancel()
    
    return None


def scrape_readme_smart(package_or_url: str) -> Tuple[bool, str]:
    """
    Intelligently scrape README with fail-fast logic
    
    CRITICAL FIX: Better error handling, faster failures
    """
    package_or_url = package_or_url.strip()
    
    # Check cache
    cache_key = f"readme:{package_or_url}"
    cached = get_cached_result(cache_key, "readme")
    if cached:
        return True, cached[0]['content']
    
    rate_limiter.wait_if_needed()
    
    readme_content = None
    source = None
    
    is_github_url = 'github.com' in package_or_url.lower()
    is_pypi_url = 'pypi.org' in package_or_url.lower()
    
    if is_pypi_url:
        match = re.search(r'pypi\.org/project/([^/]+)', package_or_url.lower())
        package_name = match.group(1) if match else package_or_url
    else:
        package_name = package_or_url
    
    # Try PyPI first (for package names)
    if not is_github_url:
        readme_content = scrape_pypi_readme(package_name)
        source = "pypi"
        
        if readme_content and is_stub_readme(readme_content):
            logger.info(f"⚠️ PyPI README is a stub for {package_name}")
            readme_content = None
            source = None
    
    # Try GitHub (if URL or PyPI failed)
    if not readme_content:
        if is_github_url:
            readme_content = scrape_github_readme(package_or_url)
            source = "github_direct"
        else:
            # Try PyPI metadata for repo URL
            metadata = get_pypi_metadata(package_name)
            if metadata and metadata.get('repository'):
                repo_url = metadata['repository']
                logger.info(f"📍 Found repo in PyPI metadata: {repo_url}")
                readme_content = scrape_github_readme(repo_url)
                source = "github_from_pypi"
            
            # CRITICAL FIX: Only try patterns if metadata didn't work
            if not readme_content:
                readme_content = try_github_patterns(package_name)
                source = "github_pattern"
    
    # Format result
    if readme_content:
        if len(readme_content) > MAX_README_SIZE:
            readme_content = readme_content[:MAX_README_SIZE] + "\n\n[... truncated for size ...]"
        
        cache_data = [{"content": readme_content, "source": source}]
        cache_result(cache_key, "readme", cache_data)
        
        code_blocks = CodeDetector.extract_from_markdown(readme_content)
        
        output = f"# README for: {package_or_url}\n"
        output += f"**Source:** {source}\n"
        output += f"**Length:** {len(readme_content):,} characters\n"
        output += f"**Code Blocks Found:** {len(code_blocks)}\n\n"
        output += "---\n\n"
        output += CodeDetector.format_for_llm(readme_content, code_blocks)
        
        return True, output
    else:
        error_msg = f"❌ Could not find README for: {package_or_url}\n\n"
        error_msg += "**Suggestions:**\n"
        error_msg += f"1. Search web for: '{package_name} documentation'\n"
        error_msg += f"2. Check if package name is correct\n"
        error_msg += f"3. Use search_web tool to find tutorials\n"
        
        logger.info(f"README not found for {package_or_url}")
        return False, error_msg


# ============================================================================
# DEPRECATION DETECTION
# ============================================================================

def detect_deprecated_features(readme_content: str, package_name: str) -> Dict[str, Any]:
    """Detect deprecated features with severity levels"""
    readme_lower = readme_content.lower()
    
    known_deprecations = {
        "scikit-learn": ["load_boston", "fetch_mldata", "sklearn.cross_validation"],
        "pandas": ["append", "ix", "Panel", ".as_matrix"],
        "tensorflow": ["tf.Session", "tf.placeholder", "tf.contrib"],
        "numpy": ["np.matrix", "np.asmatrix"],
        "xgboost": ["predict_proba()", "get_fscore"],
        "keras": ["keras.layers.merge", "keras.engine"],
    }
    
    detected = []
    target_package_lower = package_name.lower().replace('-', '').replace('_', '')
    
    for lib, items in known_deprecations.items():
        lib_normalized = lib.lower().replace('-', '').replace('_', '')
        is_target = lib_normalized in target_package_lower or target_package_lower in lib_normalized
        
        for item in items:
            if item.lower() in readme_lower:
                detected.append({
                    "library": lib,
                    "item": item,
                    "severity": "CRITICAL" if is_target else "WARNING",
                    "message": f"{'Target package' if is_target else 'Dependency'} uses deprecated: {item}"
                })
    
    deprecation_sections = []
    lines = readme_content.split('\n')
    
    for i, line in enumerate(lines):
        if any(kw in line.lower() for kw in ['deprecated', 'deprecation', 'no longer supported', 'removed in']):
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            context = '\n'.join(lines[start:end])
            deprecation_sections.append({
                "line_number": i + 1,
                "text": line.strip(),
                "context": context
            })
    
    has_deprecations = len(deprecation_sections) > 0 or len(detected) > 0
    
    critical = [d for d in detected if d['severity'] == 'CRITICAL']
    warnings = [d for d in detected if d['severity'] == 'WARNING']
    
    return {
        "has_deprecation_warnings": has_deprecations,
        "critical_count": len(critical),
        "warning_count": len(warnings),
        "critical_items": critical,
        "warning_items": warnings,
        "deprecation_sections": deprecation_sections[:5],
        "recommendation": (
            "⚠️ CRITICAL: Avoid deprecated features in target package" if critical else
            "⚠️ WARNING: Examples use deprecated features from dependencies" if warnings else
            "✅ No major deprecation warnings found"
        )
    }


# ============================================================================
# PACKAGE HEALTH REPORT
# ============================================================================

import re
import logging
from typing import Tuple, Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# 🧹 SMART README CLEANER (Aggressive Fix)
# ============================================================================

def clean_readme_content(readme_content: str) -> str:
    """
    PRODUCTION FIX: Aggressively remove LICENSE, HISTORY, and LEGAL text.
    
    Specific Fixes for Pandas/Python/NumPy:
    - Removes "History of the Software" sections
    - Removes "Terms and Conditions" blocks
    - Handles indented copyright notices
    - Filters massive contributor lists
    """
    if not readme_content:
        return ""
    
    # 1. Fast Fail: If the content is purely a license file, return empty or summary
    content_lower = readme_content.lower()
    if "terms and conditions" in content_lower and "definitions" in content_lower:
        # High probability this is just a license file
        if len(readme_content) > 5000 and "usage" not in content_lower:
             return "⚠️ [Content removed: Detected as License File]"

    lines = readme_content.split('\n')
    cleaned_lines = []
    
    # State flags
    in_license_block = False
    in_legal_section = False
    consecutive_legal_lines = 0
    
    # Regex Patterns for "Kill Phrases" (Lines that trigger block removal)
    license_start_patterns = [
        r'^\s*#{1,6}\s*(license|licensing|copyright|copying)',  # Headers
        r'^\s*a\.\s*history\s*of\s*the\s*software',             # Python/Pandas specific
        r'^\s*b\.\s*terms\s*and\s*conditions',                  # Python/Pandas specific
        r'^\s*apache\s*license',                                # Apache header
        r'^\s*copyright\s*(?:\[.*?\]|\(c\)|©|\d{4})',           # Copyright lines
        r'^\s*permission\s*is\s*hereby\s*granted',              # MIT/BSD start
        r'^\s*redistribution\s*and\s*use\s*in\s*source',        # BSD start
        r'^\s*this\s*software\s*is\s*provided\s*by',            # Disclaimer
    ]
    
    # Phrases that indicate we are reading garbage/legal text
    boilerplate_phrases = [
        'warranties of merchantability',
        'fitness for a particular purpose',
        'in no event shall',
        'liable for any direct',
        'indirect, incidental, special',
        'exemplary, or consequential damages',
        'procurement of substitute goods',
        'business interruption',
        'negligence or otherwise',
        'arising in any way out of the use',
        'license agreement',
        'all rights reserved',
        'redistributions of source code',
    ]

    for line in lines:
        line_lower = line.lower().strip()
        
        # 1. CHECK: Entering a Legal Section?
        # Check against regex patterns
        if any(re.match(pat, line_lower) for pat in license_start_patterns):
            in_license_block = True
            in_legal_section = True
            continue

        # 2. CHECK: Leaving a Legal Section?
        # If we hit a Markdown Header that ISN'T legal, we are safe again.
        # e.g., "## Installation" or "## Usage"
        if in_legal_section and re.match(r'^\s*#{1,6}\s+[a-z]', line_lower):
            if not any(kw in line_lower for kw in ['license', 'copyright', 'warranty', 'history', 'terms']):
                in_license_block = False
                in_legal_section = False
                consecutive_legal_lines = 0
            
        # 3. FILTER: Boilerplate filtering
        # If we find legal keywords, mark line as trash
        is_boilerplate = any(phrase in line_lower for phrase in boilerplate_phrases)
        
        if is_boilerplate:
            in_license_block = True # Assume we are in a block now
            continue

        # 4. DECISION: Keep or Drop?
        if in_license_block or in_legal_section:
            continue
            
        cleaned_lines.append(line)

    cleaned_content = '\n'.join(cleaned_lines)
    
    # Final cleanup: Reduce multiple newlines
    cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
    
    return cleaned_content

# ============================================================================
# 📊 MAIN REPORT GENERATOR
# ============================================================================

def get_package_health_report(package_or_url: str) -> Tuple[bool, str]:
    """
    Generate comprehensive health report with FULL code examples.
    """
    # 1. Setup Report Header
    report = []
    report.append(f"# 📊 Package Health Report: {package_or_url}")
    report.append("=" * 70)
    report.append("")
    
    is_github = 'github.com' in package_or_url.lower()
    
    # 2. Scrape README
    success, readme_result = scrape_readme_smart(package_or_url)
    
    if not success:
        return False, f"❌ Failed to retrieve README for {package_or_url}\n\n{readme_result}"
    
    # 3. CLEANING STEP
    readme_content = readme_result.split("---\n\n", 1)[-1] if "---\n\n" in readme_result else readme_result
    readme_content = clean_readme_content(readme_content)
    
    # 4. Metadata Retrieval
    pypi_metadata = None
    github_metadata = None
    
    if not is_github:
        pypi_metadata = get_pypi_metadata(package_or_url)
        
        if pypi_metadata:
            report.append("## 📦 PyPI Package Information")
            report.append(f"**Package:** {pypi_metadata['package_name']}")
            report.append(f"**Latest Version:** {pypi_metadata['latest_version']}")
            report.append(f"**Python:** {pypi_metadata['python_requires']}")
            
            # --- FIX STARTS HERE ---
            # Use 'or' to handle cases where license is None OR missing
            lic = pypi_metadata.get('license') or 'Not specified'
            if len(lic) > 50: lic = lic[:50] + "..."
            report.append(f"**License:** {lic}")
            # --- FIX ENDS HERE ---
            
            if pypi_metadata.get('is_deprecated'):
                report.append("\n🚨 **CRITICAL WARNING:** Package is DEPRECATED")
            
            if pypi_metadata.get('is_actively_maintained'):
                report.append("\n✅ **Status:** Actively maintained")
            else:
                 report.append("\n⚠️ **Status:** Potentially unmaintained")

            if pypi_metadata.get('recent_versions'):
                report.append("\n**Recent Versions:**")
                for version, date in list(pypi_metadata['recent_versions'].items())[:3]:
                    report.append(f"  - v{version}: {date.split('T')[0] if date else 'unknown'}")
            
            if pypi_metadata.get('repository') and 'github.com' in pypi_metadata['repository']:
                github_metadata = get_github_metadata(pypi_metadata['repository'])
            
            report.append("")
    else:
        github_metadata = get_github_metadata(package_or_url)
    
    # 5. GitHub Metrics
    if github_metadata:
        report.append("## 🐙 GitHub Repository")
        report.append(f"**Repository:** {github_metadata['repo_name']}")
        report.append(f"**Stars:** ⭐ {github_metadata['stars']:,}")
        
        if github_metadata.get('archived'):
            report.append("\n🚨 **CRITICAL:** Repository is ARCHIVED (read-only)")
        
        report.append("")
    
    # 6. Code Analysis
    code_blocks = CodeDetector.extract_from_markdown(readme_content)
    
    report.append("## 💻 Code Examples (Ready to Use)")
    report.append(f"**Total Blocks Found:** {len(code_blocks)}")
    
    if code_blocks:
        # Filter blocks by language to prioritize Python
        python_blocks = [b for b in code_blocks if 'python' in b['language'] or 'py' in b['language']]
        install_blocks = [b for b in code_blocks if b['language'] in ['bash', 'console', 'shell', 'sh']]
        
        report.append(f"  - Python Code: {len(python_blocks)}")
        report.append(f"  - Install Cmds: {len(install_blocks)}")
        
        # Build a list of blocks to display
        display_blocks = []
        
        if install_blocks:
            display_blocks.append(install_blocks[0]) 
            
        if python_blocks:
            display_blocks.extend(python_blocks[:3]) 
        elif not install_blocks:
            display_blocks.extend(code_blocks[:3])

        report.append("\n### 🚀 Extracted Examples:")
        
        for block in display_blocks:
            report.append(f"\n**Example {block['index']} ({block['language'].upper()})**")
            
            # Output full code with truncation check for massive blocks
            code_lines = block['code'].split('\n')
            if len(code_lines) > 50:
                truncated_code = '\n'.join(code_lines[:50]) + "\n\n# ... [Truncated for length] ..."
                report.append(f"```{block['language']}\n{truncated_code}\n```")
            else:
                report.append(f"```{block['language']}\n{block['code']}\n```")
                
    else:
        report.append("\n⚠️ **WARNING:** No code examples found in README")
    
    report.append("")
    
    # 7. Deprecation Analysis
    deprecation_info = detect_deprecated_features(readme_content, package_or_url)
    
    report.append("## ⚠️ Deprecation Analysis")
    if deprecation_info['critical_items']:
        report.append("\n🚨 **CRITICAL DEPRECATIONS:**")
        for item in deprecation_info['critical_items']:
            report.append(f"  - ❌ {item['item']}")
    else:
        report.append("\n✅ No critical deprecations found.")
    
    report.append("")
    report.append("=" * 70)
    
    return True, '\n'.join(report)

# ============================================================================
# WEB SCRAPING (FIXED FOR ISSUE #3)
# ============================================================================

def scrape_webpage_smart(url: str) -> str:
    """
    FIX FOR ISSUE #3: Scrape webpage while preserving code blocks
    
    Previously: Collapsed all whitespace, destroying Python indentation
    Now: Extracts code blocks FIRST, preserves formatting
    
    Args:
        url: URL to scrape
    
    Returns:
        Formatted content with code blocks prominently displayed
    
    Example:
        result = scrape_webpage_smart("https://docs.python.org/3/library/pathlib.html")
    """
    # Validate URL first (SSRF protection)
    is_valid, error_msg = validate_url(url)
    if not is_valid:
        return f"Error: {error_msg}"
    
    # Fetch the URL
    response = fetch_url(url, validate=False)  # Already validated above
    if not response:
        return f"Error: Could not fetch {url}"
    
    # Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Remove noise elements
    for tag in soup(['script', 'style', 'nav', 'footer', 'iframe', 'svg', 'header']):
        tag.decompose()
    
    # CRITICAL FIX: Extract code blocks BEFORE flattening text
    # This preserves indentation (Issue #3)
    code_blocks = CodeDetector.extract_from_html(soup)
    
    # Now extract prose (can flatten this safely since code is already extracted)
    text = soup.get_text(separator='\n', strip=True)
    
    # Format with code blocks preserved and prominently displayed
    return CodeDetector.format_for_llm(text, code_blocks, source_url=url)
# ============================================================================
# WEB SEARCH - PRODUCTION ROBUST VERSION WITH FALLBACK
# ============================================================================

def search_duckduckgo_html(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Optional[List[Dict[str, str]]]:
    """
    Fallback: Scrape DuckDuckGo HTML (more reliable than API)
    
    PRODUCTION FIX: API often returns empty results, HTML scraping is more reliable
    """
    try:
        # Use HTML version which is more reliable
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        data = {"q": query}
        
        response = requests.post(url, headers=headers, data=data, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Find result links
        for result_div in soup.find_all('div', class_='result'):
            # Extract title link
            title_elem = result_div.find('a', class_='result__a')
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            url = title_elem.get('href', '')
            
            # Extract snippet
            snippet_elem = result_div.find('a', class_='result__snippet')
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else title
            
            if url and title:
                results.append({
                    "title": title,
                    "snippet": snippet,
                    "url": url,
                    "source": "duckduckgo-html"
                })
            
            if len(results) >= max_results:
                break
        
        logger.info(f"🦆 DuckDuckGo HTML: {len(results)} results")
        return results if results else None
        
    except Exception as e:
        logger.warning(f"DuckDuckGo HTML search failed: {e}")
        return None


def search_duckduckgo_api(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Optional[List[Dict[str, str]]]:
    """
    Primary: Try DuckDuckGo Instant Answer API
    
    Note: API often returns limited results, HTML fallback is more reliable
    """
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_redirect": "1",
            "no_html": "1",
            "skip_disambig": "1"
        }
        
        # Build URL with proper encoding
        param_str = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
        full_url = f"{url}?{param_str}"
        
        response = requests.get(full_url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        # Related topics
        for item in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(item, dict) and "Text" in item:
                url_value = item.get("FirstURL", "")
                if url_value:
                    results.append({
                        "title": item.get("Text", "")[:100],
                        "snippet": item.get("Text", ""),
                        "url": url_value,
                        "source": "duckduckgo-api"
                    })
        
        # Abstract
        if not results and data.get("Abstract"):
            abstract_url = data.get("AbstractURL", "")
            if abstract_url:
                results.append({
                    "title": data.get("Heading", query),
                    "snippet": data.get("Abstract", ""),
                    "url": abstract_url,
                    "source": "duckduckgo-api"
                })
        
        logger.info(f"🦆 DuckDuckGo API: {len(results)} results")
        return results if results else None
        
    except Exception as e:
        logger.debug(f"DuckDuckGo API failed (expected, using HTML fallback): {e}")
        return None


def perform_web_search(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Tuple[bool, str]:
    """
    PRODUCTION FIX: Multi-tier search with robust fallback
    
    Strategy:
    1. Try cache
    2. Try DuckDuckGo HTML (most reliable)
    3. Fallback to API
    4. Return helpful error with suggestions
    """
    if not query or not query.strip():
        return False, "Error: Empty search query"
    
    logger.info(f"🔍 Searching: {query[:100]}...")
    
    # Check cache
    cached = get_cached_result(query, "search")
    if cached:
        return True, _format_results(cached, query)
    
    rate_limiter.wait_if_needed()
    
    # PRODUCTION FIX: Try HTML first (more reliable than API)
    results = search_duckduckgo_html(query, max_results)
    
    # Fallback to API
    if not results:
        logger.info("HTML search empty, trying API...")
        results = search_duckduckgo_api(query, max_results)
    
    if results and len(results) > 0:
        cache_result(query, "search", results)
        return True, _format_results(results, query)
    
    # Graceful failure with helpful message
    error_msg = f"# Search Results: {query}\n\n"
    error_msg += "⚠️ No results found from search providers.\n\n"
    error_msg += "**Suggestions:**\n"
    error_msg += "1. Try more specific keywords\n"
    error_msg += "2. Check spelling\n"
    error_msg += "3. Use `scrape_readme()` for package documentation\n"
    error_msg += "4. Try different search terms\n\n"
    error_msg += f"**Original query:** {query}"
    
    logger.warning(f"No search results for: {query}")
    return True, error_msg  # Return True with helpful message instead of failing


def _format_results(results: List[Dict[str, str]], query: str) -> str:
    """Format search results for LLM consumption"""
    output = []
    output.append(f"# 🔍 Search Results: {query}")
    output.append("")
    output.append(f"Found {len(results)} results:")
    output.append("=" * 70)
    output.append("")
    
    for i, result in enumerate(results, 1):
        output.append(f"## Result {i}")
        output.append(f"**Title:** {result['title']}")
        output.append(f"**URL:** {result['url']}")
        output.append(f"**Summary:** {result['snippet']}")
        output.append("")
    
    # Markdown-ready citations
    output.append("---")
    output.append("## 📚 Resources (Citation Format)")
    output.append("")
    for result in results:
        title = result['title'] or result['url']
        url = result['url']
        if url:
            output.append(f"- [{title}]({url})")
    
    output.append("")
    output.append("---")
    output.append("💡 **Next Steps:** Use `scrape_webpage(url)` to get full content with code examples")
    
    return "\n".join(output)


# ============================================================================
# CREWAI TOOLS - PRODUCTION FIX FOR DECORATOR
# ============================================================================
# ============================================================================
# CREWAI TOOLS - PRODUCTION FIX FOR DECORATOR
# ============================================================================

def create_crewai_tool(func, tool_name: str, tool_description: str):
    """
    PRODUCTION FIX: Robust tool creation that guarantees required attributes
    
    Ensures compatibility with all CrewAI versions by:
    1. Setting attributes before decoration
    2. Preserving attributes after decoration
    3. Providing fallback if decorator fails
    
    Args:
        func: Function to convert to tool
        tool_name: Name of the tool
        tool_description: Description for LLM
    
    Returns:
        Tool function with guaranteed attributes
    """
    # Set attributes on original function FIRST
    func.__name__ = tool_name
    func.name = tool_name
    func.description = tool_description
    func.__doc__ = tool_description
    
    # Try to apply CrewAI decorator
    if CREWAI_AVAILABLE:
        try:
            decorated = tool(func)
            
            # CRITICAL: Preserve attributes after decoration
            # Some decorators create wrapper objects that lose attributes
            if not hasattr(decorated, '__name__'):
                decorated.__name__ = tool_name
            if not hasattr(decorated, 'name'):
                decorated.name = tool_name
            if not hasattr(decorated, 'description'):
                decorated.description = tool_description
            
            return decorated
            
        except Exception as e:
            logger.warning(f"CrewAI decorator failed for {tool_name}: {e}")
            # Fallback: return function with attributes
            return func
    
    # No CrewAI available - return function with attributes
    return func


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def search_web_impl(query: str) -> str:
    """
    Search the web for programming tutorials and documentation.
    
    Use this to find official documentation, tutorials, examples, and recent updates.
    
    Args:
        query: Search query (e.g., "Python FastAPI tutorial")
    
    Returns:
        Formatted search results with titles, URLs, and summaries
    
    Example:
        search_web("Python FastAPI tutorial")
    """
    success, result = perform_web_search(query)
    return result


def scrape_webpage_impl(url: str) -> str:
    """
    Scrape a webpage and extract all code examples with preserved formatting.
    
    **FIXED:** Now preserves Python indentation (Issue #3)
    
    Use this when you have a specific URL and need code examples with proper formatting.
    
    Args:
        url: Full URL (must be from allowed domains for security)
    
    Returns:
        Content with code blocks prominently displayed
    
    Example:
        scrape_webpage("https://docs.python.org/3/library/pathlib.html")
    """
    return scrape_webpage_smart(url)


def scrape_readme_impl(package_or_url: str) -> str:
    """
    Extract README from PyPI packages or GitHub repositories.
    
    **FIXED:** Smart stub detection (Issue #2) and code extraction (Issue #1)
    
    This is the authoritative source - always try this first!
    
    Args:
        package_or_url: PyPI package name OR GitHub URL
    
    Returns:
        README content with code blocks extracted and formatted
    
    Example:
        scrape_readme("fastapi")
        scrape_readme("https://github.com/tiangolo/fastapi")
    """
    success, result = scrape_readme_smart(package_or_url)
    return result


def get_package_health_impl(package_or_url: str) -> str:
    """
    Generate comprehensive health report for Python package or GitHub repo.
    
    🚨 **CRITICAL: Use this FIRST when writing about any package!**
    
    This tool prevents using outdated versions, deprecated features, and incomplete examples.
    
    Args:
        package_or_url: PyPI package name OR GitHub URL
    
    Returns:
        Detailed health report with version info, deprecations, and recommendations
    
    Example:
        get_package_health("xgboost")
        get_package_health("scikit-learn")
    """
    success, result = get_package_health_report(package_or_url)
    return result


# ============================================================================
# CREATE TOOLS WITH GUARANTEED ATTRIBUTES
# ============================================================================

# PRODUCTION FIX: Create tools with explicit names and descriptions
# This ensures __name__ attribute is always present for CrewAI

search_web = create_crewai_tool(
    func=search_web_impl,
    tool_name="search_web",
    tool_description="Search the web for programming tutorials and documentation. Returns formatted search results with titles, URLs, and summaries. Use this to find official docs, tutorials, and recent updates."
)

scrape_webpage = create_crewai_tool(
    func=scrape_webpage_impl,
    tool_name="scrape_webpage",
    tool_description="Scrape a webpage and extract code examples with preserved formatting. Fixes Issue #3 by preserving Python indentation. Returns content with code blocks prominently displayed."
)

scrape_readme = create_crewai_tool(
    func=scrape_readme_impl,
    tool_name="scrape_readme",
    tool_description="Extract README from PyPI packages or GitHub repositories. Smart stub detection with automatic fallback. Best for package documentation. Fixes Issues #1 and #2."
)

get_package_health = create_crewai_tool(
    func=get_package_health_impl,
    tool_name="get_package_health",
    tool_description="Generate comprehensive health report for Python packages. Detects deprecations, outdated versions, and provides recommendations. CRITICAL: Use this FIRST when writing about packages."
)


# ============================================================================
# VERIFICATION (Optional - for debugging)
# ============================================================================

def _verify_tool_attributes():
    """
    Internal verification that all tools have required attributes
    
    This helps catch issues during development
    """
    tools_to_check = [
        ('search_web', search_web),
        ('scrape_webpage', scrape_webpage),
        ('scrape_readme', scrape_readme),
        ('get_package_health', get_package_health),
    ]
    
    all_valid = True
    for name, tool_func in tools_to_check:
        checks = {
            '__name__': hasattr(tool_func, '__name__'),
            'name': hasattr(tool_func, 'name'),
            'description': hasattr(tool_func, 'description'),
        }
        
        if not all(checks.values()):
            logger.error(f"Tool {name} missing attributes: {[k for k, v in checks.items() if not v]}")
            all_valid = False
        else:
            logger.debug(f"Tool {name}: ✓ All attributes present")
    
    return all_valid



# ============================================================================
# MAIN
# ============================================================================

def main():
    """Test functionality"""
    import sys
    
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python search.py search <query>")
        print("  python search.py readme <package>")
        print("  python search.py health <package>")
        print("  python search.py scrape <url>")
        sys.exit(1)
    
    command = sys.argv[1]
    query = " ".join(sys.argv[2:])
    
    print("="*70)
    
    if command == "health":
        success, result = get_package_health_report(query)
        print(result)
        sys.exit(0 if success else 1)
    elif command == "readme":
        success, result = scrape_readme_smart(query)
        print(result)
        sys.exit(0 if success else 1)
    elif command == "scrape":
        result = scrape_webpage_smart(query)
        print(result)
        sys.exit(0)
    else:
        success, result = perform_web_search(query)
        print(result)
        sys.exit(0 if success else 1)

    # Run verification on module load (only in debug mode)
    if os.getenv("DEBUG_TOOLS"):
        _verify_tool_attributes()

if __name__ == "__main__":
    main()