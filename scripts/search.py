#!/usr/bin/env python3
"""
scripts/search.py - ENHANCED VERSION with README scraping

Web Search Tool for CrewAI Researcher Agent

Features:
- Multiple search providers (DuckDuckGo, SerpAPI, Brave)
- Automatic fallback between providers
- Rate limiting and caching
- README scraping for PyPI packages and GitHub repos
- GitHub workflow compatible
- Structured output for LLMs
- Error handling and logging

Usage:
    from search import search_web, scrape_webpage, scrape_readme
    
    # In your agent
    researcher = Agent(
        role="Research Specialist",
        tools=[search_web, scrape_webpage, scrape_readme],
        ...
    )
"""

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

# Try to import CrewAI tool decorator - with fallback for compatibility
try:
    from crewai.tools import tool
    CREWAI_TOOLS_AVAILABLE = True
except ImportError:
    try:
        from crewai_tools import tool
        CREWAI_TOOLS_AVAILABLE = True
    except ImportError:
        CREWAI_TOOLS_AVAILABLE = False
        def tool(description: str):
            """Fallback tool decorator"""
            def decorator(func):
                func.name = func.__name__
                func.description = description
                return func
            return decorator

# ============================================================================
# CONFIGURATION
# ============================================================================

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "search_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_DURATION_HOURS = int(os.getenv("SEARCH_CACHE_HOURS", "24"))
MAX_RESULTS_PER_SEARCH = int(os.getenv("SEARCH_MAX_RESULTS", "5"))
REQUEST_TIMEOUT = int(os.getenv("SEARCH_TIMEOUT", "10"))
RATE_LIMIT = int(os.getenv("SEARCH_RATE_LIMIT", "10"))

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

logger = logging.getLogger(__name__)


# ============================================================================
# RATE LIMITING
# ============================================================================

class RateLimiter:
    """Simple rate limiter to avoid overwhelming APIs"""
    
    def __init__(self, calls_per_minute: int = RATE_LIMIT):
        self.calls_per_minute = calls_per_minute
        self.calls = []
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded"""
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
# CACHING
# ============================================================================

def get_cache_key(query: str, provider: str) -> str:
    """Generate cache key for a search query"""
    combined = f"{provider}:{query.lower().strip()}"
    return hashlib.md5(combined.encode()).hexdigest()


def get_cached_result(query: str, provider: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached search result if available and fresh"""
    cache_key = get_cache_key(query, provider)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    if not cache_file.exists():
        return None
    
    try:
        with cache_file.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
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
    """Cache search results"""
    cache_key = get_cache_key(query, provider)
    cache_file = CACHE_DIR / f"{cache_key}.json"
    
    try:
        data = {
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
# README SCRAPING - NEW FEATURE
# ============================================================================

def scrape_pypi_readme(package_name: str) -> Optional[str]:
    """
    Scrape README/description from PyPI package page
    
    Args:
        package_name: Name of the PyPI package
    
    Returns:
        README content or None on error
    """
    try:
        # Try PyPI JSON API first (more reliable)
        api_url = f"https://pypi.org/pypi/{package_name}/json"
        headers = {"User-Agent": USER_AGENT}
        
        response = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        # Get description (README content)
        description = data.get("info", {}).get("description", "")
        if description:
            logger.info(f"📦 PyPI API: Got README for {package_name} ({len(description)} chars)")
            return description
        
        # Fallback: scrape HTML page
        url = f"https://pypi.org/project/{package_name}/"
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find project description section
        desc_section = soup.find('div', class_='project-description')
        if not desc_section:
            desc_section = soup.find('div', id='description')
        
        if desc_section:
            # Extract text content
            text = desc_section.get_text(separator='\n', strip=True)
            logger.info(f"📦 PyPI HTML: Got README for {package_name} ({len(text)} chars)")
            return text
        
        logger.warning(f"PyPI: No description found for {package_name}")
        return None
        
    except Exception as e:
        logger.warning(f"PyPI README scraping failed for {package_name}: {e}")
        return None


def scrape_github_readme(repo_url: str) -> Optional[str]:
    """
    Scrape README from GitHub repository
    
    Args:
        repo_url: GitHub repository URL (e.g., https://github.com/user/repo)
    
    Returns:
        README content or None on error
    """
    try:
        # Extract owner and repo name from URL
        match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            logger.warning(f"Invalid GitHub URL: {repo_url}")
            return None
        
        owner, repo = match.groups()
        repo = repo.replace('.git', '')  # Remove .git suffix if present
        
        # Try GitHub API first (most reliable)
        github_token = os.getenv("GITHUB_TOKEN")
        headers = {"User-Agent": USER_AGENT}
        
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        # Try README endpoint
        api_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        response = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            # Get download URL for raw content
            download_url = data.get("download_url")
            if download_url:
                readme_response = requests.get(download_url, headers=headers, timeout=REQUEST_TIMEOUT)
                readme_response.raise_for_status()
                logger.info(f"🐙 GitHub API: Got README for {owner}/{repo} ({len(readme_response.text)} chars)")
                return readme_response.text
        
        # Fallback 1: Try raw.githubusercontent.com
        for readme_name in ['README.md', 'README.rst', 'README.txt', 'README']:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{readme_name}"
            response = requests.get(raw_url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                logger.info(f"🐙 GitHub Raw (main): Got {readme_name} for {owner}/{repo}")
                return response.text
            
            # Try master branch if main doesn't work
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{readme_name}"
            response = requests.get(raw_url, headers=headers, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                logger.info(f"🐙 GitHub Raw (master): Got {readme_name} for {owner}/{repo}")
                return response.text
        
        # Fallback 2: Scrape GitHub HTML page
        html_url = f"https://github.com/{owner}/{repo}"
        response = requests.get(html_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find README section
        readme_section = soup.find('article', class_='markdown-body')
        if not readme_section:
            readme_section = soup.find('div', id='readme')
        
        if readme_section:
            text = readme_section.get_text(separator='\n', strip=True)
            logger.info(f"🐙 GitHub HTML: Got README for {owner}/{repo} ({len(text)} chars)")
            return text
        
        logger.warning(f"GitHub: No README found for {owner}/{repo}")
        return None
        
    except Exception as e:
        logger.warning(f"GitHub README scraping failed for {repo_url}: {e}")
        return None


def scrape_readme_smart(url_or_name: str) -> Tuple[bool, str]:
    """
    Intelligently scrape README from PyPI package or GitHub repository
    
    Args:
        url_or_name: Package name (e.g., "fastapi") or URL (PyPI or GitHub)
    
    Returns:
        Tuple of (success, readme_content_or_error)
    """
    url_or_name = url_or_name.strip()
    
    # Check cache first
    cache_key = f"readme:{url_or_name}"
    cached = get_cached_result(cache_key, "readme")
    if cached:
        return True, cached[0]['content']
    
    # Rate limiting
    rate_limiter.wait_if_needed()
    
    readme_content = None
    source = None
    
    # Detect type and scrape
    if url_or_name.startswith(('http://', 'https://')):
        url_lower = url_or_name.lower()
        
        if 'github.com' in url_lower:
            # GitHub repository
            readme_content = scrape_github_readme(url_or_name)
            source = "github"
        elif 'pypi.org' in url_lower:
            # PyPI package URL - extract package name
            match = re.search(r'pypi\.org/project/([^/]+)', url_lower)
            if match:
                package_name = match.group(1)
                readme_content = scrape_pypi_readme(package_name)
                source = "pypi"
        else:
            # Try as generic webpage
            readme_content = scrape_webpage_content(url_or_name, max_chars=20000)
            source = "web"
    else:
        # Assume it's a PyPI package name
        readme_content = scrape_pypi_readme(url_or_name)
        source = "pypi"
        
        # If PyPI fails, try searching GitHub
        if not readme_content:
            github_url = f"https://github.com/search?q={url_or_name}&type=repositories"
            # Try common patterns
            for pattern in [f"{url_or_name}/{url_or_name}", f"python-{url_or_name}", url_or_name]:
                test_url = f"https://github.com/{pattern}"
                content = scrape_github_readme(test_url)
                if content:
                    readme_content = content
                    source = "github"
                    break
    
    if readme_content:
        # Cache the result
        cache_data = [{"content": readme_content, "source": source}]
        cache_result(cache_key, "readme", cache_data)
        
        # Format output
        output = f"# README for: {url_or_name}\n"
        output += f"**Source:** {source}\n"
        output += f"**Length:** {len(readme_content)} characters\n\n"
        output += "---\n\n"
        output += readme_content
        
        return True, output
    else:
        error_msg = f"Could not find README for: {url_or_name}"
        logger.error(error_msg)
        return False, error_msg


# ============================================================================
# SEARCH PROVIDERS (KEEPING EXISTING CODE)
# ============================================================================

def search_duckduckgo(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Optional[List[Dict[str, str]]]:
    """Search using DuckDuckGo Lite"""
    try:
        url = "https://lite.duckduckgo.com/lite/"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        data = {"q": query, "s": "0"}
        response = requests.post(url, headers=headers, data=data, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        for row in soup.find_all('tr'):
            links = row.find_all('a')
            if len(links) >= 1:
                link = links[0]
                href = link.get('href', '')
                title = link.get_text(strip=True)
                snippet_td = row.find('td', class_='result-snippet')
                snippet = snippet_td.get_text(strip=True) if snippet_td else ""
                
                if href and title and not href.startswith('//duckduckgo.com'):
                    results.append({
                        "title": title,
                        "snippet": snippet or title,
                        "url": href,
                        "source": "duckduckgo"
                    })
                    
                    if len(results) >= max_results:
                        break
        
        logger.info(f"🦆 DuckDuckGo: {len(results)} results")
        return results if results else None
        
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
        return search_duckduckgo_instant(query, max_results)


def search_duckduckgo_instant(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Optional[List[Dict[str, str]]]:
    """Fallback: Use DuckDuckGo Instant Answer API"""
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_redirect": "1",
            "no_html": "1",
            "skip_disambig": "1"
        }
        
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        results = []
        
        for item in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(item, dict) and "Text" in item:
                results.append({
                    "title": item.get("Text", "")[:100],
                    "snippet": item.get("Text", ""),
                    "url": item.get("FirstURL", ""),
                    "source": "duckduckgo-api"
                })
        
        if not results and data.get("Abstract"):
            results.append({
                "title": data.get("Heading", query),
                "snippet": data.get("Abstract", ""),
                "url": data.get("AbstractURL", ""),
                "source": "duckduckgo-api"
            })
        
        logger.info(f"🦆 DuckDuckGo API: {len(results)} results")
        return results if results else None
        
    except Exception as e:
        logger.warning(f"DuckDuckGo API search failed: {e}")
        return None


def search_serpapi(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Optional[List[Dict[str, str]]]:
    """Search using SerpAPI"""
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return None
    
    try:
        url = "https://serpapi.com/search"
        params = {
            "q": query,
            "api_key": api_key,
            "num": max_results,
            "engine": "google"
        }
        
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "url": item.get("link", ""),
                "source": "serpapi"
            })
        
        logger.info(f"🔍 SerpAPI: {len(results)} results")
        return results if results else None
        
    except Exception as e:
        logger.warning(f"SerpAPI search failed: {e}")
        return None


def search_brave(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Optional[List[Dict[str, str]]]:
    """Search using Brave Search API"""
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        return None
    
    try:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key
        }
        params = {
            "q": query,
            "count": max_results
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("web", {}).get("results", [])[:max_results]:
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("description", ""),
                "url": item.get("url", ""),
                "source": "brave"
            })
        
        logger.info(f"🦁 Brave: {len(results)} results")
        return results if results else None
        
    except Exception as e:
        logger.warning(f"Brave search failed: {e}")
        return None


# ============================================================================
# WEB SCRAPING
# ============================================================================

def scrape_webpage_content(url: str, max_chars: int = 5000) -> Optional[str]:
    """Scrape text content from a webpage"""
    try:
        headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) > max_chars:
            text = text[:max_chars] + "..."
        
        logger.info(f"📄 Scraped {len(text)} chars from {urlparse(url).netloc}")
        return text
        
    except Exception as e:
        logger.warning(f"Scraping failed for {url}: {e}")
        return None


# ============================================================================
# MAIN SEARCH FUNCTION
# ============================================================================

def perform_web_search(query: str, max_results: int = MAX_RESULTS_PER_SEARCH) -> Tuple[bool, str]:
    """Perform web search with automatic fallback between providers"""
    if not query or not query.strip():
        return False, "Error: Empty search query"
    
    logger.info(f"🔍 Searching: {query[:100]}...")
    
    for provider in ["duckduckgo", "duckduckgo-api", "serpapi", "brave"]:
        cached = get_cached_result(query, provider)
        if cached:
            return True, _format_results(cached, query)
    
    rate_limiter.wait_if_needed()
    
    search_functions = [
        ("duckduckgo", search_duckduckgo),
        ("duckduckgo-api", search_duckduckgo_instant),
        ("serpapi", search_serpapi),
        ("brave", search_brave),
    ]
    
    for provider_name, search_func in search_functions:
        try:
            results = search_func(query, max_results)
            
            if results and len(results) > 0:
                cache_result(query, provider_name, results)
                return True, _format_results(results, query)
                
        except Exception as e:
            logger.warning(f"{provider_name} failed: {e}")
            continue
    
    error_msg = f"All search providers failed for query: {query}"
    logger.error(error_msg)
    return False, error_msg


def _format_results(results: List[Dict[str, str]], query: str) -> str:
    """Format search results for LLM consumption"""
    output = f"# Search Results for: {query}\n\n"
    output += f"Found {len(results)} results:\n\n"
    
    for i, result in enumerate(results, 1):
        output += f"## Result {i}\n"
        output += f"**Title:** {result['title']}\n"
        output += f"**URL:** {result['url']}\n"
        output += f"**Summary:** {result['snippet']}\n"
        output += f"**Source:** {result['source']}\n\n"
    
    output += "\n---\n"
    output += "Use these search results to provide accurate, up-to-date information.\n"
    output += "Always cite sources by mentioning the title and URL.\n"
    
    return output


# ============================================================================
# CREWAI TOOLS
# ============================================================================

@tool("Search the web for information")
def search_web(query: str) -> str:
    """
    Search the web for information about a topic.
    
    Use this when you need current information, official documentation,
    or real-world examples.
    
    Args:
        query (str): Search query (e.g., "Python FastAPI tutorial")
    
    Returns:
        str: Formatted search results with titles, URLs, and summaries
    """
    success, result = perform_web_search(query, max_results=MAX_RESULTS_PER_SEARCH)
    return result


@tool("Scrape and extract content from a specific webpage")
def scrape_webpage(url: str) -> str:
    """
    Scrape and extract text content from a specific webpage.
    
    Use this when you have a specific URL and need its full content.
    
    Args:
        url (str): Full URL to scrape (must start with http:// or https://)
    
    Returns:
        str: Extracted text content from the webpage
    """
    if not url or not url.startswith(("http://", "https://")):
        return f"Error: Invalid URL '{url}'. Must start with http:// or https://"
    
    rate_limiter.wait_if_needed()
    content = scrape_webpage_content(url, max_chars=5000)
    
    if content:
        return f"# Content from {url}\n\n{content}"
    else:
        return f"Error: Could not scrape content from {url}"


@tool("Get README from PyPI package or GitHub repository")
def scrape_readme(package_or_url: str) -> str:
    """
    Extract README/documentation from PyPI packages or GitHub repositories.
    
    This is the authoritative source for Python packages and GitHub projects.
    Use this when researching:
    - Python packages from PyPI
    - GitHub repositories
    - Project documentation
    
    Args:
        package_or_url (str): PyPI package name (e.g., "fastapi") or 
                              GitHub URL (e.g., "https://github.com/user/repo")
    
    Returns:
        str: README content with metadata
    
    Examples:
        >>> scrape_readme("fastapi")
        >>> scrape_readme("https://github.com/tiangolo/fastapi")
        >>> scrape_readme("requests")
    """
    success, result = scrape_readme_smart(package_or_url)
    return result


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def search_multiple_queries(queries: List[str]) -> Dict[str, str]:
    """Search multiple queries and return combined results"""
    results = {}
    
    for query in queries:
        success, result = perform_web_search(query, max_results=3)
        results[query] = result
        
        if len(queries) > 1:
            time.sleep(1)
    
    return results


# ============================================================================
# STANDALONE TESTING
# ============================================================================

def main():
    """Test the search functionality"""
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python search.py search <query>      - Web search")
        print("  python search.py readme <package>    - Get README")
        print("\nExamples:")
        print("  python search.py search 'Python FastAPI'")
        print("  python search.py readme fastapi")
        print("  python search.py readme https://github.com/tiangolo/fastapi")
        sys.exit(1)
    
    command = sys.argv[1]
    query = " ".join(sys.argv[2:])
    
    print("="*70)
    
    if command == "readme":
        print(f"Getting README for: {query}")
        print("="*70)
        print()
        
        success, result = scrape_readme_smart(query)
        print(result)
        
        if success:
            print("\n" + "="*70)
            print("✅ README retrieved successfully")
        else:
            print("\n" + "="*70)
            print("❌ README retrieval failed")
            sys.exit(1)
    
    else:  # default to search
        print(f"Testing Web Search Tool")
        print("="*70)
        print(f"Query: {query}\n")
        
        success, results = perform_web_search(query)
        print(results)
        print("\n" + "="*70)
        
        if success:
            print("✅ Search completed successfully")
        else:
            print("❌ Search failed")
            sys.exit(1)


if __name__ == "__main__":
    main()