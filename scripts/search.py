#!/usr/bin/env python3
"""
scripts/search.py - ENHANCED VERSION with README scraping and Package Health Checks

Web Search Tool for CrewAI Researcher Agent

Features:
- Multiple search providers (DuckDuckGo, SerpAPI, Brave)
- Automatic fallback between providers
- Rate limiting and caching
- README scraping for PyPI packages and GitHub repos
- Package metadata extraction (version, status, deprecations)
- Code example extraction from README
- Deprecation detection
- GitHub repository health metrics
- Comprehensive package health reports
- GitHub workflow compatible
- Structured output for LLMs
- Error handling and logging

Usage:
    from search import search_web, scrape_webpage, scrape_readme, get_package_health
    
    # In your agent
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
# PACKAGE METADATA & VALIDATION - NEW FEATURES
# ============================================================================

def get_pypi_metadata(package_name: str) -> Optional[Dict[str, Any]]:
    """
    Get comprehensive metadata from PyPI including version, status, and deprecation info
    
    Args:
        package_name: Name of the PyPI package
    
    Returns:
        Dictionary with metadata or None on error
    """
    try:
        api_url = f"https://pypi.org/pypi/{package_name}/json"
        headers = {"User-Agent": USER_AGENT}
        
        response = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        info = data.get("info", {})
        releases = data.get("releases", {})
        
        # Get latest version
        latest_version = info.get("version", "unknown")
        
        # Get all versions sorted
        all_versions = sorted(releases.keys(), reverse=True) if releases else []
        
        # Get Python version requirements
        python_requires = info.get("requires_python", "Not specified")
        
        # Get dependencies
        requires_dist = info.get("requires_dist", [])
        
        # Get package status
        classifiers = info.get("classifiers", [])
        development_status = [c for c in classifiers if "Development Status" in c]
        
        # Check for deprecation warnings in description
        description = info.get("description", "").lower()
        is_deprecated = any(word in description for word in [
            "deprecated", "no longer maintained", "unmaintained", 
            "use instead", "migrated to", "superseded by"
        ])
        
        # Get upload dates for recent versions
        recent_versions = {}
        for version in all_versions[:5]:  # Last 5 versions
            if version in releases and releases[version]:
                upload_time = releases[version][0].get("upload_time", "")
                recent_versions[version] = upload_time
        
        # Calculate if actively maintained (release in last 2 years)
        last_release_date = None
        is_actively_maintained = None
        if recent_versions:
            latest_upload = list(recent_versions.values())[0]
            if latest_upload:
                try:
                    last_release_date = datetime.fromisoformat(latest_upload.replace("Z", "+00:00"))
                    days_since_release = (datetime.now(last_release_date.tzinfo) - last_release_date).days
                    is_actively_maintained = days_since_release < 730  # 2 years
                except:
                    is_actively_maintained = None
        
        metadata = {
            "package_name": package_name,
            "latest_version": latest_version,
            "python_requires": python_requires,
            "all_versions": all_versions[:10],  # Last 10 versions
            "recent_versions": recent_versions,
            "development_status": development_status,
            "is_deprecated": is_deprecated,
            "is_actively_maintained": is_actively_maintained,
            "dependencies": requires_dist[:20] if requires_dist else [],
            "homepage": info.get("home_page"),
            "docs_url": info.get("docs_url") or info.get("project_urls", {}).get("Documentation"),
            "repository": info.get("project_urls", {}).get("Source") or info.get("project_urls", {}).get("Repository"),
            "license": info.get("license"),
            "author": info.get("author"),
            "summary": info.get("summary"),
        }
        
        logger.info(f"📊 PyPI Metadata: {package_name} v{latest_version}")
        return metadata
        
    except Exception as e:
        logger.warning(f"Failed to get PyPI metadata for {package_name}: {e}")
        return None


def extract_code_examples_from_readme(readme_content: str, language: str = "python") -> List[Dict[str, str]]:
    """
    Extract code examples from README markdown
    
    Args:
        readme_content: README text content
        language: Programming language to extract (default: python)
    
    Returns:
        List of code examples with context
    """
    examples = []
    
    # Pattern to match code blocks
    # Supports: ```python, ```py, ``` (no language specified)
    pattern = r'```(?:' + language + r'|py)?\n(.*?)```'
    
    matches = re.finditer(pattern, readme_content, re.DOTALL)
    
    for i, match in enumerate(matches, 1):
        code = match.group(1).strip()
        
        # Skip empty code blocks
        if not code:
            continue
        
        # Get context (text before code block)
        start_pos = match.start()
        context_start = max(0, start_pos - 200)
        context = readme_content[context_start:start_pos].strip()
        
        # Extract heading if available
        heading_match = re.search(r'#{1,6}\s+(.+?)(?:\n|$)', context)
        heading = heading_match.group(1) if heading_match else f"Example {i}"
        
        examples.append({
            "index": i,
            "heading": heading,
            "code": code,
            "context": context[-150:] if len(context) > 150 else context,
            "lines": len(code.split('\n'))
        })
    
    logger.info(f"📝 Extracted {len(examples)} code examples from README")
    return examples


def detect_deprecated_features(readme_content: str, package_name: str) -> Dict[str, Any]:
    """
    Detect deprecated features, datasets, or APIs mentioned in README.
    
    Refactored to check ALL known libraries, not just the target package.
    """
    readme_lower = readme_content.lower()
    
    # Common deprecation patterns
    deprecation_keywords = [
        "deprecated", "deprecation", "no longer supported", 
        "removed in version", "will be removed", "legacy",
        "obsolete", "superseded", "replaced by", "use instead"
    ]
    
    # Find sections with deprecation warnings
    deprecation_sections = []
    lines = readme_content.split('\n')
    
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in deprecation_keywords):
            # Get context
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            context = '\n'.join(lines[start:end])
            
            deprecation_sections.append({
                "line_number": i + 1,
                "text": line.strip(),
                "context": context
            })
    
    # Specific deprecated items for popular packages
    known_deprecations = {
        "scikit-learn": ["load_boston", "fetch_mldata", "sklearn.cross_validation"],
        "pandas": ["append", "ix", "Panel"],
        "tensorflow": ["tf.Session", "tf.placeholder", "tf.contrib"],
        "numpy": ["np.matrix", "np.asmatrix"],
        "xgboost": ["predict_proba (use predict)", "get_fscore"]
    }
    
    detected_deprecated_items = []
    
    # [CRITICAL FIX] Check ALL libraries, not just the package being analyzed.
    # Code examples often use multiple libraries (e.g. sklearn data in xgboost tutorial).
    for lib, items in known_deprecations.items():
        for item in items:
            # Check for strict word boundary or exact match to avoid false positives
            if item.lower() in readme_lower:
                detected_deprecated_items.append(f"{lib}: {item}")
    
    has_deprecations = len(deprecation_sections) > 0 or len(detected_deprecated_items) > 0
    
    return {
        "has_deprecation_warnings": has_deprecations,
        "deprecation_count": len(deprecation_sections),
        "deprecation_sections": deprecation_sections[:5],
        "known_deprecated_items": detected_deprecated_items,
        "recommendation": "Review deprecation warnings before using code examples" if has_deprecations else "No major deprecation warnings found"
    }


def get_github_metadata(repo_url: str) -> Optional[Dict[str, Any]]:
    """
    Get GitHub repository metadata including stars, activity, and health
    
    Args:
        repo_url: GitHub repository URL
    
    Returns:
        Dictionary with repo metadata or None
    """
    try:
        # Extract owner and repo
        match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            return None
        
        owner, repo = match.groups()
        repo = repo.replace('.git', '')
        
        # Use GitHub API
        github_token = os.getenv("GITHUB_TOKEN")
        headers = {"User-Agent": USER_AGENT}
        if github_token:
            headers["Authorization"] = f"token {github_token}"
        
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        response = requests.get(api_url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        
        # Get recent commits
        commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        commits_response = requests.get(commits_url, headers=headers, params={"per_page": 1}, timeout=REQUEST_TIMEOUT)
        
        last_commit_date = None
        if commits_response.status_code == 200:
            commits_data = commits_response.json()
            if commits_data:
                last_commit_date = commits_data[0].get("commit", {}).get("author", {}).get("date")
        
        # Calculate activity
        is_active = False
        if last_commit_date:
            try:
                commit_date = datetime.fromisoformat(last_commit_date.replace("Z", "+00:00"))
                days_since_commit = (datetime.now(commit_date.tzinfo) - commit_date).days
                is_active = days_since_commit < 180  # Active if commit in last 6 months
            except:
                pass
        
        metadata = {
            "repo_name": f"{owner}/{repo}",
            "description": data.get("description"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "open_issues": data.get("open_issues_count", 0),
            "watchers": data.get("watchers_count", 0),
            "language": data.get("language"),
            "license": data.get("license", {}).get("name") if data.get("license") else None,
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "last_commit_date": last_commit_date,
            "is_active": is_active,
            "default_branch": data.get("default_branch", "main"),
            "homepage": data.get("homepage"),
            "topics": data.get("topics", []),
            "archived": data.get("archived", False),
            "disabled": data.get("disabled", False),
        }
        
        logger.info(f"🐙 GitHub Metadata: {owner}/{repo} - {metadata['stars']} stars")
        return metadata
        
    except Exception as e:
        logger.warning(f"Failed to get GitHub metadata: {e}")
        return None


def get_package_health_report(package_or_url: str) -> Tuple[bool, str]:
    """
    Generate comprehensive health report for Python package or GitHub repo
    
    This is the MAIN function to use for blog generation - it combines all checks
    
    Args:
        package_or_url: Package name or GitHub URL
    
    Returns:
        Tuple of (success, report_text)
    """
    report_lines = []
    report_lines.append(f"# Package Health Report: {package_or_url}")
    report_lines.append("=" * 70)
    report_lines.append("")
    
    is_github = package_or_url.startswith(('http://', 'https://')) and 'github.com' in package_or_url.lower()
    
    # 1. Get README
    success, readme_result = scrape_readme_smart(package_or_url)
    
    if not success:
        return False, f"Failed to retrieve README for {package_or_url}"
    
    readme_content = readme_result.split("---\n\n", 1)[-1] if "---\n\n" in readme_result else readme_result
    
    # 2. Get metadata
    pypi_metadata = None
    github_metadata = None
    
    if not is_github:
        # It's a PyPI package
        pypi_metadata = get_pypi_metadata(package_or_url)
        
        if pypi_metadata:
            report_lines.append("## 📦 PyPI Package Information")
            report_lines.append(f"**Package:** {pypi_metadata['package_name']}")
            report_lines.append(f"**Latest Version:** {pypi_metadata['latest_version']}")
            report_lines.append(f"**Python Requirements:** {pypi_metadata['python_requires']}")
            report_lines.append(f"**License:** {pypi_metadata.get('license', 'Not specified')}")
            
            if pypi_metadata.get('is_deprecated'):
                report_lines.append("**⚠️ WARNING:** Package appears to be DEPRECATED")
            
            if pypi_metadata.get('is_actively_maintained') is False:
                report_lines.append("**⚠️ WARNING:** No releases in past 2 years - may be unmaintained")
            elif pypi_metadata.get('is_actively_maintained'):
                report_lines.append("**✅ Status:** Actively maintained")
            
            # Recent versions
            if pypi_metadata.get('recent_versions'):
                report_lines.append("\n**Recent Versions:**")
                for version, date in list(pypi_metadata['recent_versions'].items())[:3]:
                    report_lines.append(f"  - v{version}: {date.split('T')[0] if date else 'unknown'}")
            
            # Links
            if pypi_metadata.get('docs_url'):
                report_lines.append(f"\n**Documentation:** {pypi_metadata['docs_url']}")
            if pypi_metadata.get('repository'):
                report_lines.append(f"**Repository:** {pypi_metadata['repository']}")
                # Also get GitHub metadata if repo is GitHub
                if 'github.com' in pypi_metadata['repository']:
                    github_metadata = get_github_metadata(pypi_metadata['repository'])
            
            report_lines.append("")
    else:
        # It's a GitHub repo
        github_metadata = get_github_metadata(package_or_url)
    
    # 3. GitHub metadata
    if github_metadata:
        report_lines.append("## 🐙 GitHub Repository Information")
        report_lines.append(f"**Repository:** {github_metadata['repo_name']}")
        report_lines.append(f"**Stars:** ⭐ {github_metadata['stars']:,}")
        report_lines.append(f"**Language:** {github_metadata.get('language', 'Not specified')}")
        
        if github_metadata.get('archived'):
            report_lines.append("**⚠️ WARNING:** Repository is ARCHIVED (read-only)")
        
        if github_metadata.get('is_active'):
            report_lines.append("**✅ Status:** Active development (recent commits)")
        else:
            report_lines.append("**⚠️ WARNING:** No recent commits (may be inactive)")
        
        if github_metadata.get('last_commit_date'):
            commit_date = github_metadata['last_commit_date'].split('T')[0]
            report_lines.append(f"**Last Commit:** {commit_date}")
        
        report_lines.append("")
    
    # 4. Deprecation detection
    deprecation_info = detect_deprecated_features(readme_content, package_or_url)
    
    report_lines.append("## ⚠️ Deprecation Analysis")
    
    if deprecation_info['has_deprecation_warnings']:
        report_lines.append(f"**Found {deprecation_info['deprecation_count']} deprecation warnings in documentation**")
        
        if deprecation_info['known_deprecated_items']:
            report_lines.append("\n**Known Deprecated Items Found:**")
            for item in deprecation_info['known_deprecated_items']:
                report_lines.append(f"  - ❌ {item}")
            report_lines.append("\n**⚠️ ACTION REQUIRED:** Do NOT use these deprecated items in examples!")
        
        if deprecation_info['deprecation_sections']:
            report_lines.append("\n**Deprecation Warnings:**")
            for section in deprecation_info['deprecation_sections'][:3]:
                report_lines.append(f"  - Line {section['line_number']}: {section['text']}")
    else:
        report_lines.append("**✅ No major deprecation warnings detected**")
    
    report_lines.append("")
    
    # 5. Code examples
    examples = extract_code_examples_from_readme(readme_content)
    
    report_lines.append("## 💻 Code Examples Found in README")
    report_lines.append(f"**Total Examples:** {len(examples)}")
    
    if examples:
        report_lines.append("\n**Example Summaries:**")
        for ex in examples[:5]:  # Show first 5
            report_lines.append(f"\n{ex['index']}. **{ex['heading']}** ({ex['lines']} lines)")
            # Show first 3 lines of code
            code_preview = '\n'.join(ex['code'].split('\n')[:3])
            report_lines.append(f"```python\n{code_preview}\n...\n```")
    else:
        report_lines.append("**⚠️ WARNING:** No code examples found in README")
        report_lines.append("**Recommendation:** Check official documentation for examples")
    
    report_lines.append("")
    
    # 6. Recommendations
    report_lines.append("## 📋 Recommendations for Blog Post")
    
    recommendations = []
    
    if pypi_metadata:
        recommendations.append(f"✅ Use version {pypi_metadata['latest_version']} in all examples")
        recommendations.append(f"✅ Specify Python requirement: {pypi_metadata['python_requires']}")
    
    if deprecation_info['has_deprecation_warnings']:
        recommendations.append("⚠️ CRITICAL: Avoid all deprecated features listed above")
        recommendations.append("⚠️ Test all code examples to ensure they work with latest version")
    
    if examples and len(examples) > 0:
        recommendations.append(f"✅ {len(examples)} working examples available in README - use as reference")
    else:
        recommendations.append("⚠️ No examples in README - create original examples or cite documentation")
    
    if github_metadata and github_metadata.get('archived'):
        recommendations.append("⚠️ Repository is archived - mention this limitation in blog")
    
    if github_metadata and not github_metadata.get('is_active'):
        recommendations.append("⚠️ No recent development - verify examples still work")
    
    for rec in recommendations:
        report_lines.append(f"  {rec}")
    
    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append("**Use this report to create accurate, up-to-date blog content**")
    
    return True, '\n'.join(report_lines)


# ============================================================================
# README SCRAPING
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
    
    Refactored to handle "Stub" PyPI pages by forcing GitHub fallback.
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
    url_lower = url_or_name.lower()

    # 1. Try PyPI First (if it's a URL or just a name)
    if 'pypi.org' in url_lower or not url_or_name.startswith(('http', 'https')):
        package_name = url_or_name
        if 'pypi.org' in url_lower:
            match = re.search(r'pypi\.org/project/([^/]+)', url_lower)
            if match:
                package_name = match.group(1)
        
        readme_content = scrape_pypi_readme(package_name)
        source = "pypi"

        # [CRITICAL FIX] STUB DETECTION
        # If PyPI content is too short (likely just "See docs at..."), force fallback
        if readme_content and len(readme_content) < 1200:
            logger.warning(f"⚠️ PyPI README appears to be a stub ({len(readme_content)} chars). Force-attempting GitHub fallback...")
            readme_content = None # Set to None to trigger fallback logic below

    # 2. GitHub Fallback (If PyPI failed OR was a stub)
    if not readme_content:
        # If it was a direct GitHub URL
        if 'github.com' in url_lower:
            readme_content = scrape_github_readme(url_or_name)
            source = "github"
        
        # If it was a package name, guess the GitHub URL
        else:
            # Clean package name
            clean_name = url_or_name.split('/')[-1]
            
            # Try common repo patterns
            potential_repos = [
                f"{clean_name}/{clean_name}",           # e.g. xgboost/xgboost
                f"dmlc/{clean_name}",                    # e.g. dmlc/xgboost
                f"google/{clean_name}",                  # e.g. google/jax
                f"python-{clean_name}/{clean_name}",     # e.g. python-telegram-bot
            ]
            
            # If we have a previous "stub" content, try to extract a GitHub URL from it
            if source == "pypi":
                # Implementation detail: One could scrape the stub for links, 
                # but for now we rely on pattern matching
                pass

            for pattern in potential_repos:
                test_url = f"https://github.com/{pattern}"
                content = scrape_github_readme(test_url)
                if content:
                    readme_content = content
                    source = "github"
                    logger.info(f"✅ Found GitHub fallback: {pattern}")
                    break

    # 3. Generic Web Scrape Fallback
    if not readme_content and url_or_name.startswith(('http', 'https')):
         readme_content = scrape_webpage_content(url_or_name, max_chars=20000)
         source = "web"

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
# SEARCH PROVIDERS
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
    
    # Check cache
    for provider in ["duckduckgo-api", "duckduckgo", "serpapi", "brave"]:
        cached = get_cached_result(query, provider)
        if cached:
            return True, _format_results(cached, query)
    
    rate_limiter.wait_if_needed()
    
    # [CRITICAL FIX] Reordered Priority: API First, HTML Scraper Second
    # HTML scraping is brittle and causes "System Error" often.
    search_functions = [
        ("duckduckgo-api", search_duckduckgo_instant), # API is more reliable
        ("duckduckgo", search_duckduckgo),             # HTML Fallback
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

def _format_results_old(results: List[Dict[str, str]], query: str) -> str:
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
def _format_results(results: List[Dict[str, str]], query: str) -> str:
    output = f"# Search Results for: {query}\n\n"
    output += f"Found {len(results)} results:\n\n"
    
    for i, result in enumerate(results, 1):
        output += f"## Result {i}\n"
        output += f"**Title:** {result['title']}\n"
        output += f"**URL:** {result['url']}\n"
        output += f"**Summary:** {result['snippet']}\n"
        output += f"**Source:** {result['source']}\n\n"

    # NEW: markdown-ready resources list
    output += "## Resources (Markdown-ready)\n\n"
    for result in results:
        title = result["title"] or result["url"]
        url = result["url"]
        if url:
            output += f"- [{title}]({url})\n"
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


# Define the implementation function
def _get_package_health_impl(package_or_url: str) -> str:
    """Core implementation of package health report"""
    success, result = get_package_health_report(package_or_url)
    return result


@tool("Get comprehensive package health report with validation")
def get_package_health(package_or_url: str) -> str:
    """
    Get comprehensive health report for Python package or GitHub repository.
    
    **CRITICAL: Use this tool FIRST when writing about any Python package or GitHub repo**
    
    This tool provides:
    - Current version numbers (avoid using outdated versions!)
    - Deprecation warnings (avoid deprecated features!)
    - Working code examples from official README
    - Package maintenance status
    - Repository activity metrics
    
    **USE THIS TO PREVENT ERRORS:**
    - Outdated version numbers
    - Deprecated functions/datasets (e.g., load_boston)
    - Incomplete code examples
    - Unmaintained packages
    
    Args:
        package_or_url: PyPI package name (e.g., "xgboost") or 
                       GitHub URL (e.g., "https://github.com/dmlc/xgboost")
    
    Returns:
        str: Comprehensive health report with version info, deprecations, and recommendations
    
    Examples:
        >>> get_package_health("xgboost")
        >>> get_package_health("scikit-learn")
        >>> get_package_health("https://github.com/dmlc/xgboost")
    
    **AGENT INSTRUCTIONS:**
    1. ALWAYS call this tool BEFORE writing blog content about packages
    2. Use the latest version number from this report
    3. NEVER use deprecated features mentioned in warnings
    4. Base code examples on the working examples from README
    5. Mention if package is archived or unmaintained
    6. Verify all code is complete (no undefined variables)
    """
    return _get_package_health_impl(package_or_url)


# Expose the callable implementation for direct use (testing, etc.)
get_package_health.func = _get_package_health_impl

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
        print("  python search.py health <package>    - Get package health report")
        print("\nExamples:")
        print("  python search.py search 'Python FastAPI'")
        print("  python search.py readme fastapi")
        print("  python search.py readme https://github.com/tiangolo/fastapi")
        print("  python search.py health xgboost")
        sys.exit(1)
    
    command = sys.argv[1]
    query = " ".join(sys.argv[2:])
    
    print("="*70)
    
    if command == "health":
        print(f"Getting health report for: {query}")
        print("="*70)
        print()
        
        success, result = get_package_health_report(query)
        print(result)
        
        if success:
            print("\n" + "="*70)
            print("✅ Health report generated successfully")
        else:
            print("\n" + "="*70)
            print("❌ Health report generation failed")
            sys.exit(1)
    
    elif command == "readme":
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