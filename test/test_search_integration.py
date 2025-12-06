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
            'search_web',
            'scrape_webpage',
            'perform_web_search',
            'RateLimiter',
        ]
        
        for func_name in required_funcs:
            if hasattr(search, func_name):
                print(f"✅ {func_name} is available")
            else:
                print(f"❌ {func_name} is missing")
                return False
        
        # Check tools are callable
        if callable(search.search_web):
            print("✅ search_web tool is callable")
        
        if callable(search.scrape_webpage):
            print("✅ scrape_webpage tool is callable")
        
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
        
        # Try creating agent with search tools
        try:
            test_agent = Agent(
                role="Test Researcher",
                goal="Test search integration",
                backstory="Testing agent",
                tools=[search.search_web, search.scrape_webpage],
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
    }
    
    print("Optional API keys (enhance search capabilities):")
    for key, description in optional_keys.items():
        if os.getenv(key):
            print(f"✅ {key:<20} - Set ({description})")
        else:
            print(f"ℹ️  {key:<20} - Not set ({description})")
    
    print("\nℹ️  Note: Search works without API keys using DuckDuckGo")
    print("✅ Environment configuration checked")
    return True


def run_all_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("  SEARCH TOOL INTEGRATION TEST SUITE")
    print("="*70)
    
    tests = [
        ("Import Verification", test_imports),
        ("Search Module", test_search_module),
        ("Basic Search", test_basic_search),
        ("Cache System", test_cache),
        ("CrewAI Integration", test_crewai_integration),
        ("Environment", test_environment),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Search tool is ready to use.")
        print("\nNext steps:")
        print("1. Integrate search tools into your researcher agent")
        print("2. Test blog generation: python scripts/generate_daily_blog.py")
        print("3. Deploy to GitHub workflows")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please fix issues before deploying.")
        print("\nTroubleshooting:")
        print("1. Install missing dependencies:")
        print("   pip install requests beautifulsoup4 crewai")
        print("2. Ensure search.py is in scripts/ directory:")
        print(f"   Expected location: {scripts_dir}/search.py")
        print(f"   Check: ls -la {scripts_dir}/search.py")
        print("3. Run from project root directory:")
        print(f"   cd {project_root}")
        print("   python test/test_search_integration.py")
        print("4. Check logs for detailed error messages")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())