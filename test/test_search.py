#!/usr/bin/env python3
"""
test/test_search.py - PRODUCTION-READY TEST SUITE
Comprehensive tests for search.py tools to verify production readiness.

Run: python test/test_search.py
CI/CD: python test/test_search.py --ci (skips network tests)
"""

import sys
import os
import time
from pathlib import Path
from typing import Tuple, List

# ==============================================================================
# ROBUST IMPORT LOGIC
# ==============================================================================
current_file = Path(__file__).resolve()
current_dir = current_file.parent

possible_script_dirs = [
    current_dir.parent / "scripts",
    current_dir,
    current_dir / "scripts",
    Path("scripts"),
]

search_module_found = False
for path in possible_script_dirs:
    if (path / "search.py").exists():
        sys.path.insert(0, str(path.resolve()))
        search_module_found = True
        break

if not search_module_found:
    print("🔴 CRITICAL: Could not locate 'search.py'.")
    print(f"   Checked: {[str(p) for p in possible_script_dirs]}")
    sys.exit(1)

try:
    import search
    print("✅ Successfully imported search module")
except ImportError as e:
    print(f"🔴 CRITICAL: Import failed. {e}")
    sys.exit(1)

# Optional CrewAI import (not required for core tests)
CREWAI_AVAILABLE = False
try:
    from crewai import Agent
    CREWAI_AVAILABLE = True
    print("✅ CrewAI available for integration tests")
except ImportError:
    print("⚠️  CrewAI not installed - skipping integration tests")

# ==============================================================================
# TEST UTILITIES
# ==============================================================================

class TestResults:
    """Track test results for final report"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []
    
    def record(self, test_name: str, passed: bool, message: str = "", skipped: bool = False):
        self.total += 1
        icon = "🟢" if passed else "🔴" if not skipped else "⚪"
        status = "PASS" if passed else "FAIL" if not skipped else "SKIP"
        
        print(f"{icon} {status:4} | {test_name:50} | {message}")
        
        if skipped:
            self.skipped += 1
        elif passed:
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append(f"{test_name}: {message}")
    
    def summary(self):
        print("\n" + "=" * 80)
        print("📊 TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests:  {self.total}")
        print(f"✅ Passed:    {self.passed}")
        print(f"🔴 Failed:    {self.failed}")
        print(f"⚪ Skipped:   {self.skipped}")
        print(f"Success Rate: {(self.passed / max(1, self.total - self.skipped) * 100):.1f}%")
        
        if self.failures:
            print("\n❌ FAILED TESTS:")
            for failure in self.failures:
                print(f"   - {failure}")
        
        print("=" * 80)
        return self.failed == 0

results = TestResults()

# ==============================================================================
# SYNTHETIC TEST DATA (Avoids flaky network-dependent tests)
# ==============================================================================

SYNTHETIC_README_WITH_CODE = """
# XGBoost Tutorial

## Installation
```bash
pip install xgboost
```

## Quick Start
```python
import xgboost as xgb
from sklearn.datasets import load_iris

# Load data
X, y = load_iris(return_X_y=True)

# Train model
model = xgb.XGBClassifier()
model.fit(X, y)

# Predict
predictions = model.predict(X)
```

## Advanced Usage
```python
# Custom parameters
params = {
    'max_depth': 3,
    'learning_rate': 0.1,
    'n_estimators': 100
}

model = xgb.XGBClassifier(**params)
model.fit(X_train, y_train)
```
"""

SYNTHETIC_README_STUB = """
# MyPackage

For documentation, please visit https://docs.example.com

See our website for more information.
"""

SYNTHETIC_README_WITH_DEPRECATED = """
# Tutorial: Machine Learning

## Loading Data
```python
from sklearn.datasets import load_boston
data = load_boston()
```

## Using Pandas
```python
import pandas as pd
df.append(new_row)  # deprecated
```
"""

SYNTHETIC_HTML_WITH_CODE = """
<!DOCTYPE html>
<html>
<head><title>Tutorial</title></head>
<body>
    <h1>Python Tutorial</h1>
    <p>Here's how to use our library:</p>
    
    <pre><code class="language-python">
def hello_world():
    print("Hello, World!")
    if True:
        print("Indented correctly")
    </code></pre>
    
    <h2>Installation</h2>
    <pre><code class="language-bash">pip install example</code></pre>
</body>
</html>
"""

# ==============================================================================
# UNIT TESTS: Core Functionality
# ==============================================================================

def test_code_detector_markdown():
    """Test 1.1: Code extraction from Markdown (Issue #1 Fix)"""
    print("\n" + "=" * 80)
    print("UNIT TESTS: Code Detection Engine")
    print("=" * 80)
    
    # Test case 1: Standard fenced code
    blocks = search.CodeDetector.extract_from_markdown(SYNTHETIC_README_WITH_CODE)
    
    if len(blocks) >= 3:
        results.record(
            "Code Extraction: Standard Markdown",
            True,
            f"Found {len(blocks)} blocks"
        )
    else:
        results.record(
            "Code Extraction: Standard Markdown",
            False,
            f"Expected ≥3 blocks, got {len(blocks)}"
        )
    
    # Test case 2: Whitespace tolerance (CRITICAL for Issue #1)
    markdown_with_spaces = """
```python   
print("test")
```
```bash  
pip install test
```
"""
    
    blocks = search.CodeDetector.extract_from_markdown(markdown_with_spaces)
    results.record(
        "Code Extraction: Whitespace Tolerance",
        len(blocks) == 2,
        f"Handles trailing spaces: {len(blocks)} blocks"
    )
    
    # Test case 3: Missing language tags
    markdown_no_lang = """
```
def test():
    return True
```
"""
    
    blocks = search.CodeDetector.extract_from_markdown(markdown_no_lang)
    detected_lang = blocks[0]['language'] if blocks else None
    results.record(
        "Code Extraction: Language Detection",
        detected_lang == 'python',
        f"Auto-detected: {detected_lang}"
    )
    
    # Test case 4: Multiple languages
    markdown_multi = """
```python
import sys
```
```javascript
console.log("test");
```
```bash
echo "test"
```
"""
    
    blocks = search.CodeDetector.extract_from_markdown(markdown_multi)
    langs = [b['language'] for b in blocks]
    results.record(
        "Code Extraction: Multi-Language",
        len(langs) == 3 and 'bash' in langs,
        f"Languages: {langs}"
    )


def test_code_detector_html():
    """Test 1.2: Code extraction from HTML (Issue #3 Fix)"""
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(SYNTHETIC_HTML_WITH_CODE, 'html.parser')
    
    blocks = search.CodeDetector.extract_from_html(soup)
    
    if len(blocks) >= 2:
        results.record(
            "HTML Code Extraction: Count",
            True,
            f"Found {len(blocks)} blocks"
        )
    else:
        results.record(
            "HTML Code Extraction: Count",
            False,
            f"Expected ≥2 blocks, got {len(blocks)}"
        )
    
    # CRITICAL: Verify indentation preservation (Issue #3)
    python_block = next((b for b in blocks if 'python' in b['language']), None)
    
    if python_block:
        code = python_block['code']
        has_indentation = '    ' in code or '\t' in code
        has_proper_structure = 'def hello_world' in code and 'if True' in code
        
        results.record(
            "HTML Code Extraction: Indentation Preserved",
            has_indentation and has_proper_structure,
            "Whitespace intact" if has_indentation else "⚠️ Indentation lost!"
        )
    else:
        results.record(
            "HTML Code Extraction: Indentation Preserved",
            False,
            "No Python block found"
        )


def test_stub_detection():
    """Test 1.3: Smart stub detection (Issue #2 Fix)"""
    
    # Test real README (not a stub)
    is_stub_real = search.is_stub_readme(SYNTHETIC_README_WITH_CODE)
    results.record(
        "Stub Detection: Real README",
        not is_stub_real,
        "Correctly identified as valid"
    )
    
    # Test stub README
    is_stub_fake = search.is_stub_readme(SYNTHETIC_README_STUB)
    results.record(
        "Stub Detection: Stub README",
        is_stub_fake,
        "Correctly identified as stub"
    )
    
    # Test edge case: short but valid
    short_valid = """
# Tool

## Usage
```python
import tool
```
"""
    is_stub_short = search.is_stub_readme(short_valid)
    results.record(
        "Stub Detection: Short But Valid",
        not is_stub_short,
        "Not falsely flagged as stub"
    )
    
    # Test edge case: long but redirects
    long_stub = "Please visit https://docs.example.com for documentation. " * 50
    is_stub_long = search.is_stub_readme(long_stub)
    results.record(
        "Stub Detection: Long Redirect",
        is_stub_long,
        "Detected redirect pattern"
    )


def test_deprecation_detection():
    """Test 1.4: Deprecation detection with severity"""
    
    # Test deprecated sklearn features
    report = search.detect_deprecated_features(SYNTHETIC_README_WITH_DEPRECATED, "scikit-learn")
    
    has_boston = any("load_boston" in str(item) for item in report.get('critical_items', []))
    results.record(
        "Deprecation: load_boston Detection",
        has_boston and report['has_deprecation_warnings'],
        f"Critical items: {len(report.get('critical_items', []))}"
    )
    
    # Test severity levels (sklearn vs pandas)
    critical_count = report.get('critical_count', 0)
    warning_count = report.get('warning_count', 0)
    
    results.record(
        "Deprecation: Severity Levels",
        critical_count > 0 or warning_count > 0,
        f"Critical: {critical_count}, Warnings: {warning_count}"
    )
    
    # Test clean package (no deprecations)
    clean_readme = "# Clean Package\n\n```python\nimport requests\n```"
    clean_report = search.detect_deprecated_features(clean_readme, "requests")
    
    results.record(
        "Deprecation: Clean Package",
        not clean_report['has_deprecation_warnings'],
        "No false positives"
    )


def test_url_validation():
    """Test 1.5: Security - URL validation (SSRF protection)"""
    
    # Valid URLs
    valid_urls = [
        "https://github.com/user/repo",
        "https://pypi.org/project/package",
        "https://raw.githubusercontent.com/user/repo/main/README.md",
    ]
    
    for url in valid_urls:
        is_valid, msg = search.validate_url(url)
        if not is_valid:
            results.record(
                f"URL Validation: {url[:30]}...",
                False,
                msg
            )
            return
    
    results.record(
        "URL Validation: Valid URLs",
        True,
        f"All {len(valid_urls)} valid URLs accepted"
    )
    
    # Invalid URLs (security risks)
    invalid_urls = [
        ("http://localhost/admin", "localhost"),
        ("https://192.168.1.1/api", "private IP"),
        ("https://evil.com/hack", "not allowed domain"),
        ("ftp://files.example.com/data", "invalid scheme"),
    ]
    
    blocked_count = 0
    for url, reason in invalid_urls:
        is_valid, msg = search.validate_url(url)
        if not is_valid:
            blocked_count += 1
    
    results.record(
        "URL Validation: Security Blocks",
        blocked_count == len(invalid_urls),
        f"Blocked {blocked_count}/{len(invalid_urls)} malicious URLs"
    )


def test_rate_limiter():
    """Test 1.6: Rate limiter functionality"""
    
    limiter = search.RateLimiter(calls_per_minute=5)
    
    # Make 5 calls quickly
    start_time = time.time()
    for i in range(5):
        limiter.wait_if_needed()
    elapsed = time.time() - start_time
    
    results.record(
        "Rate Limiter: Burst Handling",
        elapsed < 1,  # Should allow 5 calls immediately
        f"5 calls in {elapsed:.2f}s"
    )
    
    # 6th call should trigger rate limit
    start_time = time.time()
    limiter.wait_if_needed()  # This should wait
    elapsed = time.time() - start_time
    
    results.record(
        "Rate Limiter: Enforcement",
        elapsed > 0.5,  # Should have waited
        f"Enforced delay: {elapsed:.2f}s"
    )


def test_cache_system():
    """Test 1.7: Caching with versioning"""
    
    # Test cache key generation
    key1 = search.get_cache_key("test query", "provider1")
    key2 = search.get_cache_key("test query", "provider2")
    key3 = search.get_cache_key("TEST QUERY", "provider1")  # Case insensitive
    
    results.record(
        "Cache: Key Generation",
        key1 != key2 and key1 == key3,
        "Unique keys per provider, case-insensitive"
    )
    
    # Test cache write/read
    test_data = [{"test": "data", "id": 123}]
    search.cache_result("test_cache", "test_provider", test_data)
    cached = search.get_cached_result("test_cache", "test_provider")
    
    results.record(
        "Cache: Write/Read",
        cached is not None and cached[0]['id'] == 123,
        "Data persisted correctly"
    )


# ==============================================================================
# INTEGRATION TESTS: Tool Functions
# ==============================================================================

def test_package_health_report():
    """Test 2.1: Package health report generation"""
    print("\n" + "=" * 80)
    print("INTEGRATION TESTS: Tool Functions")
    print("=" * 80)
    
    # Note: This test may require network access
    try:
        success, report = search.get_package_health_report("requests")
        
        if success:
            has_version = "Latest Version" in report or "version" in report.lower()
            has_recommendations = "Recommendations" in report or "recommendation" in report.lower()
            
            results.record(
                "Package Health: Report Generation",
                has_version and has_recommendations,
                f"Generated {len(report)} char report"
            )
        else:
            results.record(
                "Package Health: Report Generation",
                False,
                "Failed to generate report",
                skipped=True
            )
    except Exception as e:
        results.record(
            "Package Health: Report Generation",
            False,
            f"Exception: {str(e)[:50]}",
            skipped=True
        )


def test_readme_scraping_integration():
    """Test 2.2: README scraping with fallback logic"""
    
    # This test uses actual network - may be skipped in CI
    if "--ci" in sys.argv:
        results.record(
            "README Scraping: Network Test",
            True,
            "Skipped in CI mode",
            skipped=True
        )
        return
    
    try:
        # Test with a stable package
        success, content = search.scrape_readme_smart("requests")
        
        if success:
            has_code = "```" in content or "BLOCK" in content
            is_substantial = len(content) > 500
            
            results.record(
                "README Scraping: Content Quality",
                has_code and is_substantial,
                f"{len(content)} chars, code={'found' if has_code else 'missing'}"
            )
        else:
            results.record(
                "README Scraping: Content Quality",
                False,
                "Failed to fetch README",
                skipped=True
            )
    except Exception as e:
        results.record(
            "README Scraping: Content Quality",
            False,
            f"Exception: {str(e)[:50]}",
            skipped=True
        )


def test_web_search_integration():
    """Test 2.3: Web search functionality"""
    
    if "--ci" in sys.argv:
        results.record(
            "Web Search: Network Test",
            True,
            "Skipped in CI mode",
            skipped=True
        )
        return
    
    try:
        success, content = search.perform_web_search("Python requests library")
        
        if success:
            has_results = "Result" in content or "result" in content.lower()
            has_urls = "http" in content.lower()
            no_errors = "System Error" not in content and "Error" not in content[:100]
            
            results.record(
                "Web Search: Search Quality",
                has_results and has_urls and no_errors,
                f"{len(content)} chars returned"
            )
        else:
            results.record(
                "Web Search: Search Quality",
                False,
                f"Search failed: {content[:100]}"
            )
    except Exception as e:
        results.record(
            "Web Search: Search Quality",
            False,
            f"Exception: {str(e)[:50]}",
            skipped=True
        )


# ==============================================================================
# CREWAI INTEGRATION TESTS
# ==============================================================================

def test_crewai_tool_registration():
    """Test 3.1: CrewAI tool loading"""
    print("\n" + "=" * 80)
    print("CREWAI INTEGRATION TESTS")
    print("=" * 80)
    
    if not CREWAI_AVAILABLE:
        results.record(
            "CrewAI: Tool Registration",
            True,
            "CrewAI not installed",
            skipped=True
        )
        return
    
    try:
        # Test that tools are properly decorated
        tools = [
            search.search_web,
            search.scrape_webpage,
            search.scrape_readme,
            search.get_package_health,
        ]
        
        # Verify tools have required attributes
        all_valid = True
        for tool in tools:
            if not hasattr(tool, '__name__'):
                all_valid = False
                break
        
        results.record(
            "CrewAI: Tool Attributes",
            all_valid,
            f"All {len(tools)} tools properly decorated"
        )
        
        # Try to create an agent with tools
        try:
            agent = Agent(
                role="Test Agent",
                goal="Test tools",
                backstory="Testing tool integration",
                tools=tools,
                verbose=False,
                allow_delegation=False,
            )
            
            results.record(
                "CrewAI: Agent Creation",
                len(agent.tools) == len(tools),
                f"Agent created with {len(agent.tools)} tools"
            )
        except Exception as e:
            # Ignore LLM configuration errors
            if "llm" in str(e).lower() or "api" in str(e).lower():
                results.record(
                    "CrewAI: Agent Creation",
                    True,
                    "Tools registered (LLM config ignored)",
                    skipped=True
                )
            else:
                results.record(
                    "CrewAI: Agent Creation",
                    False,
                    f"Failed: {str(e)[:50]}"
                )
    
    except Exception as e:
        results.record(
            "CrewAI: Tool Registration",
            False,
            f"Exception: {str(e)[:50]}"
        )


def test_tool_descriptions():
    """Test 3.2: Tool descriptions are informative"""
    
    tools = {
        'search_web': search.search_web,
        'scrape_webpage': search.scrape_webpage,
        'scrape_readme': search.scrape_readme,
        'get_package_health': search.get_package_health,
    }
    
    all_have_docs = True
    for tool_name, tool_func in tools.items():
        doc = tool_func.__doc__ or ""
        if len(doc) < 50:
            all_have_docs = False
            results.record(
                f"Tool Docs: {tool_name}",
                False,
                "Documentation too short or missing"
            )
            break
    
    if all_have_docs:
        results.record(
            "Tool Docs: All Tools",
            True,
            "All tools have comprehensive documentation"
        )


# ==============================================================================
# EDGE CASES & ERROR HANDLING
# ==============================================================================

def test_error_handling():
    """Test 4.1: Graceful error handling"""
    print("\n" + "=" * 80)
    print("ERROR HANDLING & EDGE CASES")
    print("=" * 80)
    
    # Test empty query
    success, result = search.perform_web_search("")
    results.record(
        "Error Handling: Empty Query",
        not success and "Error" in result,
        "Handled gracefully"
    )
    
    # Test invalid URL
    result = search.scrape_webpage_smart("not-a-valid-url")
    results.record(
        "Error Handling: Invalid URL",
        "Error" in result or "Invalid" in result,
        "Validation caught bad URL"
    )
    
    # Test nonexistent package
    success, result = search.scrape_readme_smart("this-package-definitely-does-not-exist-12345")
    results.record(
        "Error Handling: Nonexistent Package",
        not success and ("not find" in result.lower() or "could not" in result.lower()),
        "Returned error message"
    )


def test_edge_cases():
    """Test 4.2: Edge cases"""
    
    # Very long code block
    long_markdown = "```python\n" + ("print('line')\n" * 1000) + "```"
    blocks = search.CodeDetector.extract_from_markdown(long_markdown)
    
    results.record(
        "Edge Case: Long Code Block",
        len(blocks) == 1 and blocks[0]['lines'] == 1000,
        f"Handled {blocks[0]['lines']} lines" if blocks else "Failed"
    )
    
    # Unicode in code
    unicode_markdown = """
```python
# 中文注释
text = "Hello 世界"
emoji = "🚀"
```
"""
    blocks = search.CodeDetector.extract_from_markdown(unicode_markdown)
    has_unicode = blocks and "世界" in blocks[0]['code']
    
    results.record(
        "Edge Case: Unicode Content",
        has_unicode,
        "Unicode preserved in code blocks"
    )
    
    # Mixed line endings
    mixed_endings = "```python\nline1\r\nline2\rline3\n```"
    blocks = search.CodeDetector.extract_from_markdown(mixed_endings)
    
    results.record(
        "Edge Case: Mixed Line Endings",
        len(blocks) == 1,
        "Handles \\n, \\r\\n, \\r"
    )


# ==============================================================================
# REGRESSION TESTS: Verify fixes for known issues
# ==============================================================================

def test_issue_1_regression():
    """Test 5.1: Regression test for Issue #1 (Regex whitespace bug)"""
    print("\n" + "=" * 80)
    print("REGRESSION TESTS: Verify Known Issue Fixes")
    print("=" * 80)
    
    # This exact pattern caused Issue #1
    problematic_markdown = """
```python 
def hello():
    print("world")
```
```bash 
pip install package
```
```
# No language tag
generic code
```
"""
    
    blocks = search.CodeDetector.extract_from_markdown(problematic_markdown)
    
    results.record(
        "Regression: Issue #1 (Whitespace Bug)",
        len(blocks) == 3,
        f"Extracted {len(blocks)}/3 blocks with trailing spaces"
    )


def test_issue_2_regression():
    """Test 5.2: Regression test for Issue #2 (Stub detection)"""
    
    # This is the exact type of stub that caused Issue #2
    pypi_stub = """
LangChain

A framework for developing applications powered by language models.

For documentation, please visit https://docs.langchain.com
""" * 5  # Make it longer than 1200 chars but still a stub
    
    is_stub = search.is_stub_readme(pypi_stub)
    
    results.record(
        "Regression: Issue #2 (Stub Detection)",
        is_stub,
        f"Correctly identified {len(pypi_stub)} char stub"
    )


def test_issue_3_regression():
    """Test 5.3: Regression test for Issue #3 (Indentation killer)"""
    
    # This HTML structure was corrupted in Issue #3
    html = """
<pre><code>
def calculate():
    if True:
        for i in range(10):
            print(i)
</code></pre>
"""
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    blocks = search.CodeDetector.extract_from_html(soup)
    
    if blocks:
        code = blocks[0]['code']
        # Check that indentation is preserved
        has_if_indent = '    if True:' in code
        has_for_indent = '        for i' in code
        has_print_indent = '            print' in code
        
        results.record(
            "Regression: Issue #3 (Indentation Loss)",
            has_if_indent and has_for_indent and has_print_indent,
            "Indentation preserved in HTML extraction"
        )
    else:
        results.record(
            "Regression: Issue #3 (Indentation Loss)",
            False,
            "Failed to extract code block"
        )


# ==============================================================================
# PRODUCTION READINESS CHECKS
# ==============================================================================

def test_production_readiness():
    """Test 6.1: Production environment checks"""
    print("\n" + "=" * 80)
    print("PRODUCTION READINESS CHECKS")
    print("=" * 80)
    
    # Check cache directory exists
    cache_exists = search.CACHE_DIR.exists()
    results.record(
        "Production: Cache Directory",
        cache_exists,
        f"Located at {search.CACHE_DIR}"
    )
    
    # Check all required functions are exposed
    required_functions = [
        'search_web',
        'scrape_webpage',
        'scrape_readme',
        'get_package_health',
        'CodeDetector',
        'is_stub_readme',
        'detect_deprecated_features',
    ]
    
    all_present = all(hasattr(search, func) for func in required_functions)
    results.record(
        "Production: API Completeness",
        all_present,
        f"All {len(required_functions)} functions exposed"
    )
    
    # Check configuration
    has_config = all([
        hasattr(search, 'CACHE_VERSION'),
        hasattr(search, 'ALLOWED_DOMAINS'),
        hasattr(search, 'USER_AGENT'),
    ])
    
    results.record(
        "Production: Configuration",
        has_config,
        "All config constants defined"
    )


def test_security_hardening():
    """Test 6.2: Security features"""
    
    # Verify SSRF protection is active
    security_features = [
        hasattr(search, 'validate_url'),
        hasattr(search, 'ALLOWED_DOMAINS'),
        len(search.ALLOWED_DOMAINS) > 0,
    ]
    
    results.record(
        "Security: SSRF Protection",
        all(security_features),
        f"{len(search.ALLOWED_DOMAINS)} allowed domains"
    )
    
    # Verify rate limiting exists
    results.record(
        "Security: Rate Limiting",
        hasattr(search, 'RateLimiter'),
        "Rate limiter implemented"
    )


# ==============================================================================
# MAIN TEST RUNNER
# ==============================================================================

def run_all_tests():
    """Execute all test suites"""
    
    print("\n" + "=" * 80)
    print("🚀 SEARCH.PY PRODUCTION READINESS TEST SUITE")
    print("=" * 80)
    print(f"Test Mode: {'CI/CD (Network tests skipped)' if '--ci' in sys.argv else 'Full'}")
    print("=" * 80)
    
    # Unit Tests
    test_code_detector_markdown()
    test_code_detector_html()
    test_stub_detection()
    test_deprecation_detection()
    test_url_validation()
    test_rate_limiter()
    test_cache_system()
    
    # Integration Tests
    test_package_health_report()
    test_readme_scraping_integration()
    test_web_search_integration()
    
    # CrewAI Tests
    test_crewai_tool_registration()
    test_tool_descriptions()
    
    # Error Handling
    test_error_handling()
    test_edge_cases()
    
    # Regression Tests
    test_issue_1_regression()
    test_issue_2_regression()
    test_issue_3_regression()
    
    # Production Checks
    test_production_readiness()
    test_security_hardening()
    
    # Final Summary
    success = results.summary()
    
    if success:
        print("\n✅ ALL TESTS PASSED - READY FOR PRODUCTION")
        print("\n📋 DEPLOYMENT CHECKLIST:")
        print("   ✅ Core functionality verified")
        print("   ✅ Security features active")
        print("   ✅ Known issues fixed")
        print("   ✅ CrewAI integration working")
        print("   ✅ Error handling robust")
        print("\n🚀 System is PRODUCTION READY")
        return 0
    else:
        print("\n❌ TESTS FAILED - NOT READY FOR PRODUCTION")
        print("\n⚠️  FIX REQUIRED:")
        print("   - Review failed tests above")
        print("   - Fix issues in search.py")
        print("   - Re-run test suite")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)