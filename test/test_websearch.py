import sys
import os
import logging
from pathlib import Path

# ============================================================================
# PATH SETUP (CRITICAL FIX)
# ============================================================================
# Get the absolute path of this file: .../Best-of-the-Best/test/test_websearch.py
current_file = Path(__file__).resolve()

# Calculate project root:
# 1. .parent  -> .../Best-of-the-Best/test
# 2. .parent  -> .../Best-of-the-Best (ROOT)
project_root = current_file.parent.parent

# Add root to sys.path so we can import 'scripts'
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# ============================================================================
# IMPORTS & SETUP
# ============================================================================

logging.basicConfig(level=logging.INFO, format="%(message)s")

try:
    # Now this import will work because we added project_root to sys.path
    from scripts.search import search_duckduckgo_html, perform_web_search
except ImportError as e:
    print("❌ CRITICAL: Could not import scripts.search.")
    print(f"   Error: {e}")
    print(f"   Debug: Project Root detected as: {project_root}")
    sys.exit(1)

def print_separator():
    print("\n" + "="*60 + "\n")

# ============================================================================
# TESTS
# ============================================================================

def test_low_level_scraper(query):
    """Directly tests the HTML scraper (the part that was broken)."""
    print_separator()
    print(f"🔍 TEST 1: Low-Level Scraper (search_duckduckgo_html)")
    print(f"   Query: '{query}'")
    print("   ... Requesting data (waiting for random delay) ...")
    
    results = search_duckduckgo_html(query)
    
    if results:
        print(f"   ✅ SUCCESS: Found {len(results)} raw results.")
        print("   --- Top 3 Results ---")
        for i, res in enumerate(results[:3], 1):
            print(f"   {i}. [{res.get('source', 'unknown')}] {res['title']}")
            print(f"      🔗 {res['url']}")
        return True
    else:
        print(f"   ❌ FAILURE: Returned 0 results.")
        # Check if debug file exists
        cache_dir = project_root / "data" / "search_cache"
        debug_files = list(cache_dir.glob("ddg_fail_*.html"))
        if debug_files:
            latest = max(debug_files, key=os.path.getctime)
            print(f"   💡 Debug hint: Check the snapshot file: {latest}")
        return False

def test_high_level_tool(query):
    """Tests the full tool chain (Cache -> HTML -> API -> Fallback)."""
    print_separator()
    print(f"🔍 TEST 2: High-Level Tool (perform_web_search)")
    print(f"   Query: '{query}'")
    
    success, output = perform_web_search(query)
    
    if success and "No results" not in output and "⚠️" not in output:
        print(f"   ✅ SUCCESS: Tool returned formatted output.")
        
        # Verify specific content
        lines = output.split('\n')
        url_count = sum(1 for line in lines if "**URL:**" in line)
        print(f"   📊 Parsed {url_count} URLs in the final report.")
        
        # Print a snippet
        print("   --- Report Snippet ---")
        print('\n'.join(lines[:10]))
        print("   ...")
        return True
    else:
        print(f"   ❌ FAILURE: Tool returned error message.")
        print("   --- Output received ---")
        print(output)
        return False

def verify_langgraph_fix():
    """Specific check for the error you saw earlier."""
    print_separator()
    print(f"🔍 TEST 3: Verifying 'langgraph' specific fix")
    query = "langgraph official documentation"
    
    results = search_duckduckgo_html(query)
    
    found_correct_url = False
    if results:
        for res in results:
            # We are looking for the correct langchain docs or github
            url = res['url'].lower()
            if "langchain" in url or "langgraph" in url:
                if "404" not in res['title']:
                    found_correct_url = True
                    print(f"   ✅ Found relevant link: {url}")
                    break
    
    if not found_correct_url:
        print("   ⚠️ WARNING: Did not find the official LangGraph docs in top results.")
    else:
        print("   ✅ Fix confirmed: Search is finding relevant LangGraph links.")

if __name__ == "__main__":
    print(f"🚀 RUNNING DIAGNOSTICS FROM: {current_file}")
    print(f"📂 PROJECT ROOT: {project_root}")
    
    # 1. Test basic functionality
    t1 = test_low_level_scraper("python requests library tutorial")
    
    # 2. Test the specific failure case from your logs
    if t1:
        verify_langgraph_fix()
    
    # 3. Test the full tool integration
    test_high_level_tool("xgboost python examples")
    
    print_separator()
    print("🏁 DIAGNOSTICS COMPLETE")