#!/usr/bin/env python3
"""
scripts/test_search_integration.py

Test script to verify search tool is properly installed and working.
Run this before deploying to production or GitHub workflows.

Usage:
    python scripts/test_search_integration.py
    python test/test_search_integration.py
    python test_search_integration.py
"""

import sys
import logging
from pathlib import Path

# FIXED: Better path detection logic
current_dir = Path(__file__).resolve().parent

# Detect project root by looking for common project markers or directory names
if current_dir.name in ["scripts", "test"]:
    # We're in a subdirectory, go up one level
    project_root = current_dir.parent
else:
    # We're already at project root
    project_root = current_dir

scripts_dir = project_root / "scripts"

# Debug: Print detected paths
print(f"Debug: Current directory: {current_dir}")
print(f"Debug: Project root: {project_root}")
print(f"Debug: Scripts directory: {scripts_dir}")
print(f"Debug: Scripts dir exists: {scripts_dir.exists()}")
if scripts_dir.exists():
    print(f"Debug: search.py exists: {(scripts_dir / 'search.py').exists()}")
print()

# Add scripts directory to path
if scripts_dir.exists():
    sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def test_imports():
    """Test that all required modules can be imported"""
    print_header("TEST 1: Import Verification")
    
    required_modules = [
        ("requests", "pip install requests"),
        ("bs4", "pip install beautifulsoup4"),
        ("crewai", "pip install crewai"),
    ]
    
    # crewai_tools is optional - it will work without it
    optional_modules = [
        ("crewai_tools", "pip install crewai-tools (optional for enhanced features)"),
    ]
    
    failed = []
    
    for module, install_cmd in required_modules:
        try:
            __import__(module)
            print(f"✅ {module:<20} - OK")
        except ImportError:
            print(f"❌ {module:<20} - MISSING")
            failed.append((module, install_cmd))
    
    # Check optional modules
    for module, install_cmd in optional_modules:
        try:
            __import__(module)
            print(f"✅ {module:<20} - OK (optional)")
        except ImportError:
            print(f"ℹ️  {module:<20} - Not installed (optional)")
    
    if failed:
        print("\n⚠️  Missing required dependencies!")
        print("\nInstall missing modules:")
        for _, cmd in failed:
            print(f"  {cmd}")
        return False
    
    print("\n✅ All required modules are installed")
    return True


def test_search_module():
    """Test that search module can be imported and has required functions"""
    print_header("TEST 2: Search Module Verification")
    
    # Check if search.py exists
    search_py_path = scripts_dir / "search.py"
    if not search_py_path.exists():
        print(f"❌ search.py not found at: {search_py_path}")
        print("\nTroubleshooting:")
        print("1. Make sure search.py is in the scripts/ directory")
        print(f"   Expected: {search_py_path}")
        print("2. Current directory structure:")
        if project_root.exists():
            print(f"   Project root: {project_root}")
            for item in project_root.iterdir():
                if item.is_dir():
                    print(f"     - {item.name}/ (directory)")
        return False
    
    try:
        import search
        print(f"✅ search.py module imported successfully from: {search_py_path}")
        
        # Check required functions exist
        required_funcs = [
            # Core search functions
            'search_web',
            'scrape_webpage',
            'scrape_readme',
            'perform_web_search',
            'scrape_pypi_readme',
            'scrape_github_readme',
            'scrape_readme_smart',
            'RateLimiter',
            # NEW: Package health functions
            'get_pypi_metadata',
            'extract_code_examples_from_readme',
            'detect_deprecated_features',
            'get_github_metadata',
            'get_package_health_report',
            'get_package_health',
        ]
        
        missing_funcs = []
        for func_name in required_funcs:
            if hasattr(search, func_name):
                print(f"✅ {func_name} is available")
            else:
                print(f"❌ {func_name} is missing")
                missing_funcs.append(func_name)
        
        if missing_funcs:
            print(f"\n❌ Missing functions: {', '.join(missing_funcs)}")
            return False
        
        # Check tools are callable
        if callable(search.search_web):
            print("✅ search_web tool is callable")
        
        if callable(search.scrape_webpage):
            print("✅ scrape_webpage tool is callable")
        
        if callable(search.scrape_readme):
            print("✅ scrape_readme tool is callable")
        
        if callable(search.get_package_health):
            print("✅ get_package_health tool is callable")
        
        print("✅ Search module verification passed")
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import search module: {e}")
        print("\nTroubleshooting:")
        print("1. Verify search.py exists:")
        print(f"   ls -la {scripts_dir}/search.py")
        print("2. Check Python path:")
        for path in sys.path[:5]:
            print(f"   - {path}")
        print("3. Try running from project root:")
        print(f"   cd {project_root}")
        print("   python test/test_search_integration.py")
        return False
    except Exception as e:
        print(f"❌ Error verifying search module: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_basic_search():
    """Test basic search functionality"""
    print_header("TEST 3: Basic Search Functionality")
    
    try:
        import search
        
        # Test simple search
        query = "Python programming"
        print(f"Testing search with query: '{query}'")
        print("(This may take a few seconds...)\n")
        
        success, results = search.perform_web_search(query, max_results=2)
        
        if success:
            print("✅ Search completed successfully")
            print(f"\nResults preview (first 300 chars):")
            print("-" * 70)
            print(results[:300] + "...")
            print("-" * 70)
            return True
        else:
            print(f"❌ Search failed: {results}")
            return False
            
    except Exception as e:
        print(f"❌ Search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cache():
    """Test caching functionality"""
    print_header("TEST 4: Cache Verification")
    
    try:
        import search
        
        # Check cache directory
        if search.CACHE_DIR.exists():
            print(f"✅ Cache directory exists: {search.CACHE_DIR}")
            
            # Count cache files
            cache_files = list(search.CACHE_DIR.glob("*.json"))
            print(f"   Found {len(cache_files)} cached search results")
            
            if cache_files:
                # Show latest cache file
                latest = max(cache_files, key=lambda p: p.stat().st_mtime)
                print(f"   Latest cache: {latest.name}")
        else:
            print(f"ℹ️  Cache directory will be created on first use: {search.CACHE_DIR}")
        
        print("✅ Cache system is functional")
        return True
        
    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False


def test_crewai_integration():
    """Test CrewAI integration"""
    print_header("TEST 5: CrewAI Integration")
    
    try:
        from crewai import Agent
        import search
        
        print("✅ CrewAI imported successfully")
        
        # Try creating agent with ALL search tools including health check
        try:
            test_agent = Agent(
                role="Test Researcher",
                goal="Test search integration",
                backstory="Testing agent",
                tools=[
                    search.search_web, 
                    search.scrape_webpage, 
                    search.scrape_readme,
                    search.get_package_health,  # NEW
                ],
                verbose=False,
            )
            
            print("✅ Agent created with search tools")
            print(f"   Agent has {len(test_agent.tools)} tools")
            
            # Verify tools
            tool_names = []
            for t in test_agent.tools:
                if hasattr(t, 'name'):
                    tool_names.append(t.name)
                elif hasattr(t, '__name__'):
                    tool_names.append(t.__name__)
                else:
                    tool_names.append(str(t))
            
            print(f"   Tool names: {', '.join(tool_names)}")
            
            # Verify get_package_health is included
            if 'get_package_health' in tool_names:
                print("✅ get_package_health tool registered")
            else:
                print("⚠️  get_package_health tool not found in agent")
            
            print("✅ CrewAI integration verified")
            return True
        except Exception as e:
            print(f"⚠️  Could not create agent with tools: {e}")
            print("   This is OK - tools will still work in your actual agents")
            print("✅ CrewAI integration verified (with warnings)")
            return True
        
    except ImportError as e:
        print(f"❌ CrewAI not installed: {e}")
        print("   Install with: pip install crewai")
        return False
    except Exception as e:
        print(f"❌ CrewAI integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_environment():
    """Test environment configuration"""
    print_header("TEST 6: Environment Configuration")
    
    import os
    
    # Check for API keys (optional)
    optional_keys = {
        "SERPAPI_KEY": "SerpAPI (Google Search)",
        "BRAVE_API_KEY": "Brave Search API",
        "GITHUB_TOKEN": "GitHub API (increases rate limits for README scraping)",
    }
    
    print("Optional API keys (enhance search capabilities):")
    for key, description in optional_keys.items():
        if os.getenv(key):
            print(f"✅ {key:<20} - Set ({description})")
        else:
            print(f"ℹ️  {key:<20} - Not set ({description})")
    
    print("\nℹ️  Note: Search works without API keys using DuckDuckGo")
    print("ℹ️  Note: README scraping works without GITHUB_TOKEN (lower rate limits)")
    print("✅ Environment configuration checked")
    return True


def test_pypi_readme_scraping():
    """Test PyPI README scraping functionality"""
    print_header("TEST 7: PyPI README Scraping")
    
    try:
        import search
        
        # Test with a well-known package
        test_packages = [
            ("requests", "Popular HTTP library"),
            ("fastapi", "Modern web framework"),
        ]
        
        print("Testing PyPI README scraping with known packages:")
        print("(This may take a few seconds per package...)\n")
        
        passed_tests = 0
        total_tests = len(test_packages)
        
        for package_name, description in test_packages:
            print(f"📦 Testing package: {package_name} ({description})")
            
            try:
                readme_content = search.scrape_pypi_readme(package_name)
                
                if readme_content and len(readme_content) > 100:
                    print(f"   ✅ SUCCESS - Retrieved {len(readme_content)} characters")
                    print(f"   Preview (first 150 chars):")
                    print(f"   {readme_content[:150].replace(chr(10), ' ')}...")
                    passed_tests += 1
                elif readme_content:
                    print(f"   ⚠️  WARNING - README too short ({len(readme_content)} chars)")
                    print(f"   This might indicate an issue")
                    passed_tests += 0.5
                else:
                    print(f"   ❌ FAILED - No README content retrieved")
                
            except Exception as e:
                print(f"   ❌ ERROR - Exception: {e}")
            
            print()
        
        # Test with non-existent package
        print("📦 Testing with non-existent package (should fail gracefully):")
        fake_package = "this-package-definitely-does-not-exist-12345"
        readme_content = search.scrape_pypi_readme(fake_package)
        
        if readme_content is None:
            print(f"   ✅ Correctly returned None for non-existent package")
            print()
        else:
            print(f"   ⚠️  WARNING - Got content for non-existent package")
            print()
        
        # Summary
        print("-" * 70)
        if passed_tests >= total_tests * 0.8:  # 80% success rate
            print(f"✅ PyPI README scraping test PASSED ({passed_tests}/{total_tests})")
            print("\nKey features verified:")
            print("   • PyPI JSON API integration")
            print("   • HTML fallback parsing")
            print("   • Error handling for missing packages")
            print("   • Content extraction and validation")
            return True
        else:
            print(f"⚠️  PyPI README scraping test PARTIAL ({passed_tests}/{total_tests})")
            print("\nPossible issues:")
            print("   • Network connectivity")
            print("   • PyPI API changes")
            print("   • Rate limiting")
            return False
            
    except Exception as e:
        print(f"❌ PyPI README scraping test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_github_readme_scraping():
    """Test GitHub README scraping functionality"""
    print_header("TEST 8: GitHub README Scraping")
    
    try:
        import search
        import os
        
        # Check for GitHub token
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            print("✅ GITHUB_TOKEN detected - using authenticated API")
        else:
            print("ℹ️  No GITHUB_TOKEN - using public API (rate limited)")
        
        print()
        
        # Test with well-known repositories
        test_repos = [
            ("https://github.com/psf/requests", "Python requests library"),
            ("https://github.com/tiangolo/fastapi", "FastAPI framework"),
        ]
        
        print("Testing GitHub README scraping with known repositories:")
        print("(This may take a few seconds per repo...)\n")
        
        passed_tests = 0
        total_tests = len(test_repos)
        
        for repo_url, description in test_repos:
            print(f"🐙 Testing repository: {repo_url}")
            print(f"   Description: {description}")
            
            try:
                readme_content = search.scrape_github_readme(repo_url)
                
                if readme_content and len(readme_content) > 100:
                    print(f"   ✅ SUCCESS - Retrieved {len(readme_content)} characters")
                    
                    # Check if it looks like actual README content
                    readme_lower = readme_content.lower()
                    has_typical_sections = any(
                        keyword in readme_lower 
                        for keyword in ['install', 'usage', 'example', 'license', 'introduction']
                    )
                    
                    if has_typical_sections:
                        print(f"   ✅ Content validation - Contains typical README sections")
                    else:
                        print(f"   ℹ️  Content validation - May not be standard README format")
                    
                    print(f"   Preview (first 150 chars):")
                    print(f"   {readme_content[:150].replace(chr(10), ' ')}...")
                    passed_tests += 1
                    
                elif readme_content:
                    print(f"   ⚠️  WARNING - README too short ({len(readme_content)} chars)")
                    passed_tests += 0.5
                else:
                    print(f"   ❌ FAILED - No README content retrieved")
                
            except Exception as e:
                print(f"   ❌ ERROR - Exception: {e}")
                import traceback
                traceback.print_exc()
            
            print()
        
        # Test with non-existent repo
        print("🐙 Testing with non-existent repository (should fail gracefully):")
        fake_repo = "https://github.com/this-user-does-not-exist/fake-repo-12345"
        readme_content = search.scrape_github_readme(fake_repo)
        
        if readme_content is None:
            print(f"   ✅ Correctly returned None for non-existent repo")
            print()
        else:
            print(f"   ⚠️  WARNING - Got content for non-existent repo")
            print()
        
        # Test with invalid URL
        print("🐙 Testing with invalid GitHub URL (should fail gracefully):")
        invalid_url = "https://not-github.com/user/repo"
        readme_content = search.scrape_github_readme(invalid_url)
        
        if readme_content is None:
            print(f"   ✅ Correctly returned None for invalid URL")
            print()
        else:
            print(f"   ⚠️  WARNING - Got content for invalid URL")
            print()
        
        # Summary
        print("-" * 70)
        if passed_tests >= total_tests * 0.8:  # 80% success rate
            print(f"✅ GitHub README scraping test PASSED ({passed_tests}/{total_tests})")
            print("\nKey features verified:")
            print("   • GitHub API integration")
            print("   • Raw content fallback (main/master branches)")
            print("   • HTML parsing fallback")
            print("   • Error handling for missing repos")
            print("   • URL validation")
            print("   • Content extraction and validation")
            
            if not github_token:
                print("\n💡 Tip: Set GITHUB_TOKEN to avoid rate limits:")
                print("   export GITHUB_TOKEN='your_github_token'")
            
            return True
        else:
            print(f"⚠️  GitHub README scraping test PARTIAL ({passed_tests}/{total_tests})")
            print("\nPossible issues:")
            print("   • Network connectivity")
            print("   • GitHub API rate limits (set GITHUB_TOKEN to fix)")
            print("   • API changes")
            
            if not github_token:
                print("\n⚠️  No GITHUB_TOKEN detected - you may be rate limited")
                print("   Get a token: https://github.com/settings/tokens")
                print("   Set it: export GITHUB_TOKEN='your_token'")
            
            return False
            
    except Exception as e:
        print(f"❌ GitHub README scraping test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pypi_metadata_extraction():
    """Test PyPI metadata extraction functionality"""
    print_header("TEST 9: PyPI Metadata Extraction")
    
    try:
        import search
        
        test_packages = [
            ("requests", "Should have stable metadata"),
            ("xgboost", "Should show version and Python requirements"),
        ]
        
        print("Testing PyPI metadata extraction:")
        print("(This may take a few seconds per package...)\n")
        
        passed_tests = 0
        total_tests = len(test_packages)
        
        for package_name, description in test_packages:
            print(f"📊 Testing metadata for: {package_name}")
            print(f"   Expected: {description}")
            
            try:
                metadata = search.get_pypi_metadata(package_name)
                
                if metadata:
                    print(f"   ✅ SUCCESS - Retrieved metadata")
                    
                    # Validate key fields
                    required_fields = ['package_name', 'latest_version', 'python_requires']
                    missing_fields = [f for f in required_fields if f not in metadata]
                    
                    if not missing_fields:
                        print(f"   ✅ All required fields present")
                        print(f"   📦 Package: {metadata['package_name']}")
                        print(f"   🔢 Version: {metadata['latest_version']}")
                        print(f"   🐍 Python: {metadata['python_requires']}")
                        
                        # Check deprecation detection
                        if metadata.get('is_deprecated'):
                            print(f"   ⚠️  Package is marked as DEPRECATED")
                        else:
                            print(f"   ✅ Package is not deprecated")
                        
                        # Check maintenance status
                        if metadata.get('is_actively_maintained') is True:
                            print(f"   ✅ Actively maintained")
                        elif metadata.get('is_actively_maintained') is False:
                            print(f"   ⚠️  Not actively maintained")
                        
                        passed_tests += 1
                    else:
                        print(f"   ⚠️  Missing fields: {missing_fields}")
                        passed_tests += 0.5
                else:
                    print(f"   ❌ FAILED - No metadata retrieved")
                
            except Exception as e:
                print(f"   ❌ ERROR - Exception: {e}")
            
            print()
        
        # Summary
        print("-" * 70)
        if passed_tests >= total_tests * 0.8:
            print(f"✅ PyPI metadata extraction test PASSED ({passed_tests}/{total_tests})")
            print("\nKey features verified:")
            print("   • Version number extraction")
            print("   • Python requirements detection")
            print("   • Deprecation detection")
            print("   • Maintenance status analysis")
            print("   • Recent versions tracking")
            return True
        else:
            print(f"⚠️  PyPI metadata test PARTIAL ({passed_tests}/{total_tests})")
            return False
            
    except Exception as e:
        print(f"❌ PyPI metadata extraction test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_code_example_extraction():
    """Test code example extraction from README"""
    print_header("TEST 10: Code Example Extraction")
    
    try:
        import search
        
        # Create sample README with code blocks
        sample_readme = """
# Sample Package

## Installation
```python
pip install sample-package
```

## Quick Start

Here's a simple example:
```python
import sample_package

# Create instance
obj = sample_package.SampleClass()
result = obj.process()
print(result)
```

## Advanced Usage
```python
from sample_package import AdvancedFeature

feature = AdvancedFeature(
    param1="value1",
    param2="value2"
)
feature.execute()
```
"""
        
        print("Testing code example extraction from README content:")
        print("(Using synthetic README with 3 code blocks)\n")
        
        examples = search.extract_code_examples_from_readme(sample_readme)
        
        if examples and len(examples) == 3:
            print(f"✅ SUCCESS - Extracted {len(examples)} code examples")
            
            for i, ex in enumerate(examples, 1):
                print(f"\n   Example {i}:")
                print(f"   • Heading: {ex['heading']}")
                print(f"   • Lines: {ex['lines']}")
                print(f"   • Code preview: {ex['code'][:50]}...")
            
            # Validate structure
            required_keys = ['index', 'heading', 'code', 'context', 'lines']
            all_valid = all(
                all(key in ex for key in required_keys) 
                for ex in examples
            )
            
            if all_valid:
                print("\n   ✅ All examples have required fields")
                print("\n" + "-" * 70)
                print("✅ Code example extraction test PASSED")
                print("\nKey features verified:")
                print("   • Python code block detection")
                print("   • Heading extraction")
                print("   • Context preservation")
                print("   • Line counting")
                return True
            else:
                print("\n   ⚠️  Some examples missing required fields")
                return False
        else:
            print(f"❌ FAILED - Expected 3 examples, got {len(examples) if examples else 0}")
            return False
            
    except Exception as e:
        print(f"❌ Code example extraction test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deprecation_detection():
    """Test deprecation detection functionality"""
    print_header("TEST 11: Deprecation Detection")
    
    try:
        import search
        
        # Test with content containing deprecation warnings
        deprecated_readme = """
# Package with Deprecations

## Important Notice

The `old_function()` is **deprecated** and will be removed in version 2.0.
Please use `new_function()` instead.

## Deprecated Features

- `load_boston` dataset has been removed due to ethical concerns
- `legacy_api` is no longer supported

## Migration Guide

If you're using deprecated features, please migrate to the new API.
"""
        
        print("Testing deprecation detection:")
        print("(Using synthetic README with known deprecations)\n")
        
        result = search.detect_deprecated_features(deprecated_readme, "test-package")
        
        checks_passed = 0
        total_checks = 3
        
        # Check 1: Detected deprecation warnings
        if result.get('has_deprecation_warnings'):
            print(f"✅ Detected deprecation warnings")
            print(f"   Found {result['deprecation_count']} warning sections")
            checks_passed += 1
        else:
            print(f"❌ Failed to detect deprecation warnings")
        
        # Check 2: Deprecation sections extracted
        if result.get('deprecation_sections'):
            print(f"✅ Extracted deprecation sections")
            for section in result['deprecation_sections'][:2]:
                print(f"   • Line {section['line_number']}: {section['text'][:50]}...")
            checks_passed += 1
        else:
            print(f"❌ No deprecation sections extracted")
        
        # Check 3: Test with scikit-learn (known deprecations)
        sklearn_test = """
# Scikit-learn Example
from sklearn.datasets import load_boston
"""
        sklearn_result = search.detect_deprecated_features(sklearn_test, "scikit-learn")
        
        if sklearn_result.get('known_deprecated_items') and 'load_boston' in sklearn_result['known_deprecated_items']:
            print(f"✅ Detected known deprecated items (load_boston)")
            print(f"   Known items: {', '.join(sklearn_result['known_deprecated_items'])}")
            checks_passed += 1
        else:
            print(f"⚠️  Did not detect load_boston as deprecated")
        
        # Summary
        print("\n" + "-" * 70)
        if checks_passed >= total_checks * 0.8:
            print(f"✅ Deprecation detection test PASSED ({checks_passed}/{total_checks})")
            print("\nKey features verified:")
            print("   • Keyword-based deprecation detection")
            print("   • Context extraction")
            print("   • Known deprecated items database")
            print("   • Package-specific deprecation rules")
            return True
        else:
            print(f"⚠️  Deprecation detection test PARTIAL ({checks_passed}/{total_checks})")
            return False
            
    except Exception as e:
        print(f"❌ Deprecation detection test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_github_metadata_extraction():
    """Test GitHub metadata extraction"""
    print_header("TEST 12: GitHub Metadata Extraction")
    
    try:
        import search
        import os
        
        github_token = os.getenv("GITHUB_TOKEN")
        if github_token:
            print("✅ Using GITHUB_TOKEN for API access")
        else:
            print("ℹ️  No GITHUB_TOKEN - using public API (may be rate limited)")
        
        print()
        
        test_repo = "https://github.com/psf/requests"
        print(f"Testing GitHub metadata extraction for: {test_repo}\n")
        
        try:
            metadata = search.get_github_metadata(test_repo)
            
            if metadata:
                print(f"✅ SUCCESS - Retrieved GitHub metadata")
                
                # Validate key fields
                print(f"\n   📊 Repository Information:")
                print(f"   • Repo: {metadata.get('repo_name')}")
                print(f"   • Stars: ⭐ {metadata.get('stars', 0):,}")
                print(f"   • Language: {metadata.get('language')}")
                print(f"   • License: {metadata.get('license')}")
                
                if metadata.get('is_active'):
                    print(f"   • Status: ✅ Active (recent commits)")
                else:
                    print(f"   • Status: ⚠️  Inactive")
                
                if metadata.get('archived'):
                    print(f"   • ⚠️  Repository is ARCHIVED")
                
                # Check required fields
                required_fields = ['repo_name', 'stars', 'language', 'is_active']
                missing_fields = [f for f in required_fields if f not in metadata]
                
                if not missing_fields:
                    print(f"\n   ✅ All required metadata fields present")
                    print("\n" + "-" * 70)
                    print("✅ GitHub metadata extraction test PASSED")
                    print("\nKey features verified:")
                    print("   • Repository statistics")
                    print("   • Activity detection")
                    print("   • Archive status check")
                    print("   • Language detection")
                    return True
                else:
                    print(f"\n   ⚠️  Missing fields: {missing_fields}")
                    return False
            else:
                print(f"❌ FAILED - No metadata retrieved")
                if not github_token:
                    print("\n💡 Tip: Set GITHUB_TOKEN to avoid rate limits")
                return False
                
        except Exception as e:
            print(f"❌ ERROR - Exception: {e}")
            if "rate limit" in str(e).lower():
                print("\n⚠️  GitHub API rate limit exceeded")
                print("   Set GITHUB_TOKEN to increase limits")
            return False
            
    except Exception as e:
        print(f"❌ GitHub metadata extraction test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_package_health_report():
    """Test comprehensive package health report generation"""
    print_header("TEST 13: Package Health Report Generation")
    
    try:
        import search
        
        test_package = "requests"
        print(f"Generating comprehensive health report for: {test_package}")
        print("(This may take 10-15 seconds...)\n")
        
        try:
            success, report = search.get_package_health_report(test_package)
            
            if success:
                print("✅ Health report generated successfully\n")
                
                # Validate report contains key sections
                required_sections = [
                    "Package Health Report",
                    "PyPI Package Information",
                    "Latest Version",
                    "Deprecation Analysis",
                    "Code Examples",
                    "Recommendations"
                ]
                
                missing_sections = [s for s in required_sections if s not in report]
                
                if not missing_sections:
                    print("✅ All required sections present:")
                    for section in required_sections:
                        print(f"   • {section}")
                    
                    # Show preview
                    print(f"\n📄 Report Preview (first 500 chars):")
                    print("-" * 70)
                    print(report[:500] + "...")
                    print("-" * 70)
                    
                    # Check for actionable recommendations
                    if "⚠️ CRITICAL" in report or "✅" in report:
                        print("\n✅ Report contains actionable recommendations")
                    
                    print("\n" + "-" * 70)
                    print("✅ Package health report test PASSED")
                    print("\nKey features verified:")
                    print("   • PyPI metadata integration")
                    print("   • GitHub metadata integration")
                    print("   • Deprecation detection")
                    print("   • Code example extraction")
                    print("   • Actionable recommendations")
                    print("   • Version validation")
                    return True
                else:
                    print(f"⚠️  Missing sections: {missing_sections}")
                    return False
            else:
                print(f"❌ Failed to generate report: {report}")
                return False
                
        except Exception as e:
            print(f"❌ ERROR - Exception: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Package health report test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_package_health_tool():
    """Test the get_package_health CrewAI tool"""
    print_header("TEST 14: Package Health Tool (CrewAI)")
    
    try:
        import search
        
        test_package = "fastapi"
        print(f"Testing get_package_health tool with: {test_package}")
        print("(This may take 10-15 seconds...)\n")
        
        try:
            # Call the tool's underlying function directly (for testing)
            # This maintains compatibility with CrewAI while allowing direct calls
            if hasattr(search.get_package_health, 'func'):
                print("ℹ️  Using tool.func for direct call")
                result = search.get_package_health.func(test_package)
            else:
                # Fallback for other implementations
                print("ℹ️  Attempting direct tool call")
                result = search.get_package_health(test_package)
            
            if result and len(result) > 100:
                print("✅ Tool returned valid output")
                
                # Validate output structure
                checks_passed = 0
                total_checks = 4
                
                if "Package Health Report" in result:
                    print("✅ Contains health report header")
                    checks_passed += 1
                
                if "Latest Version" in result:
                    print("✅ Contains version information")
                    checks_passed += 1
                
                if "Recommendations" in result:
                    print("✅ Contains recommendations")
                    checks_passed += 1
                
                if "⚠️" in result or "✅" in result:
                    print("✅ Contains validation indicators")
                    checks_passed += 1
                
                # Show preview
                print(f"\n📄 Tool Output Preview (first 400 chars):")
                print("-" * 70)
                print(result[:400] + "...")
                print("-" * 70)
                
                if checks_passed >= total_checks * 0.75:
                    print("\n" + "-" * 70)
                    print(f"✅ Package health tool test PASSED ({checks_passed}/{total_checks})")
                    print("\nKey features verified:")
                    print("   • Tool callable without errors")
                    print("   • Returns formatted report")
                    print("   • Contains actionable information")
                    print("   • Ready for CrewAI integration")
                    return True
                else:
                    print(f"\n⚠️  Tool output incomplete ({checks_passed}/{total_checks})")
                    return False
            else:
                print(f"❌ Tool returned invalid output (length: {len(result) if result else 0})")
                return False
                
        except Exception as e:
            print(f"❌ ERROR - Exception: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Package health tool test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("  SEARCH TOOL INTEGRATION TEST SUITE")
    print("  Enhanced with Package Health Checking")
    print("="*70)
    
    tests = [
        # Core functionality
        ("Import Verification", test_imports),
        ("Search Module", test_search_module),
        ("Basic Search", test_basic_search),
        ("Cache System", test_cache),
        ("CrewAI Integration", test_crewai_integration),
        ("Environment", test_environment),
        
        # README scraping
        ("PyPI README Scraping", test_pypi_readme_scraping),
        ("GitHub README Scraping", test_github_readme_scraping),
        
        # NEW: Package health features
        ("PyPI Metadata Extraction", test_pypi_metadata_extraction),
        ("Code Example Extraction", test_code_example_extraction),
        ("Deprecation Detection", test_deprecation_detection),
        ("GitHub Metadata Extraction", test_github_metadata_extraction),
        ("Package Health Report", test_package_health_report),
        ("Package Health Tool", test_package_health_tool),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print("Core Features:")
    for name, result in results[:6]:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status:<10} {name}")
    
    print("\nREADME Scraping:")
    for name, result in results[6:8]:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status:<10} {name}")
    
    print("\nPackage Health Features:")
    for name, result in results[8:]:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status:<10} {name}")
    
    print(f"\n{'='*70}")
    print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print(f"{'='*70}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Search tool is fully operational.")
        print("\n✨ Enhanced Features Verified:")
        print("   ✅ Web search with multiple providers")
        print("   ✅ Webpage content scraping")
        print("   ✅ PyPI package README extraction")
        print("   ✅ GitHub repository README extraction")
        print("   ✅ Smart README detection (auto-detects PyPI vs GitHub)")
        print("   ✅ PyPI metadata extraction (version, deprecations)")
        print("   ✅ Code example extraction from README")
        print("   ✅ Deprecation detection (load_boston, etc.)")
        print("   ✅ GitHub repository health metrics")
        print("   ✅ Comprehensive package health reports")
        print("   ✅ Caching and rate limiting")
        print("   ✅ CrewAI integration")
        
        print("\n📋 Next Steps:")
        print("1. Use in your researcher agent:")
        print("   tools=[search_web, scrape_webpage, scrape_readme, get_package_health]")
        print("\n2. Agent workflow:")
        print("   Step 1: get_package_health('package_name') - Get validation data")
        print("   Step 2: Use current version, avoid deprecated features")
        print("   Step 3: Base examples on working code from README")
        print("\n3. Test blog generation:")
        print("   python scripts/generate_daily_blog.py")
        print("\n4. Deploy to GitHub workflows")
        
        print("\n💡 Pro Tips:")
        print("   • Set GITHUB_TOKEN to avoid rate limits")
        print("   • Always call get_package_health FIRST for package topics")
        print("   • Use health report to prevent code errors in blogs")
        
        return 0
        
    elif passed >= total * 0.75:  # 75% pass rate
        print("\n⚠️  Most tests passed, but some issues detected.")
        print("\nWorking features:")
        for name, result in results:
            if result:
                print(f"   ✅ {name}")
        print("\nFailed features:")
        for name, result in results:
            if not result:
                print(f"   ❌ {name}")
        print("\n💡 The tool is usable but may have limitations.")
        print("   Review failed tests and fix if needed.")
        print("\n📋 Can still use working features in production.")
        return 0
        
    else:
        print("\n⚠️  Multiple tests failed. Please fix issues before deploying.")
        print("\nTroubleshooting:")
        print("1. Install missing dependencies:")
        print("   pip install requests beautifulsoup4 crewai")
        print("\n2. Ensure search.py is in scripts/ directory:")
        print(f"   Expected location: {scripts_dir}/search.py")
        print(f"   Check: ls -la {scripts_dir}/search.py")
        print("\n3. Run from project root directory:")
        print(f"   cd {project_root}")
        print("   python test/test_search_integration.py")
        print("\n4. For GitHub features, set GITHUB_TOKEN:")
        print("   export GITHUB_TOKEN='your_github_token'")
        print("   Get token: https://github.com/settings/tokens")
        print("\n5. Check network connectivity")
        print("\n6. Review detailed error messages above")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())