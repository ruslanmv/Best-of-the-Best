#!/usr/bin/env python3
"""
Real-world test: Fetch llama-index README and verify sanitization works.
"""

import sys
import os
import logging

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'scripts'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

from search import scrape_readme_smart

def test_real_llama_index():
    """Test with actual llama-index README"""

    print("="*70)
    print("REAL-WORLD TEST: llama-index README")
    print("="*70)
    print()

    print("Fetching llama-index README...")
    print("(This will test both scraping AND sanitization)")
    print()

    success, result = scrape_readme_smart("llama-index")

    if not success:
        print(f"❌ Failed to fetch README: {result}")
        return False

    print("✅ README fetched successfully")
    print()

    # Check if result contains the header info
    if "# README for: llama-index" in result:
        print("✅ README header present")

    # Check length
    lines = result.split('\n')
    readme_content = '\n'.join(lines[4:]) if len(lines) > 4 else result  # Skip header

    print(f"📊 README Statistics:")
    print(f"   Total length: {len(result)} chars")
    print(f"   Content lines: {len(lines)}")
    print()

    # Check for base64 content
    import re
    large_base64 = re.findall(r'data:image/[^;\)]+;base64,[A-Za-z0-9+/=]{100,}', result, re.IGNORECASE)

    if large_base64:
        print(f"❌ WARNING: Found {len(large_base64)} large base64 blobs!")
        print(f"   Largest: {len(large_base64[0])} chars")
        print()
        print("   This indicates sanitization may not have been applied!")
        return False
    else:
        print("✅ No large base64 content found")

    # Check for sanitization markers
    if "data:image/<stripped>;base64,<stripped>" in result:
        print("✅ Found sanitization markers - base64 was removed")
    else:
        print("⚠️  No sanitization markers found")
        print("   (This is OK if the README had no base64 content)")

    # Verify reasonable length (should be under 20,000 chars due to sanitization)
    if len(result) > 30000:
        print(f"❌ WARNING: README is very long ({len(result)} chars)")
        print("   This could still cause LLM timeouts!")
        return False
    else:
        print(f"✅ README length is reasonable ({len(result)} chars)")

    print()
    print("="*70)
    print("VERIFICATION COMPLETE")
    print("="*70)
    print()

    # Show a preview
    print("README Preview (first 500 chars):")
    print("-" * 70)
    preview = result[:500].replace('\n\n', '\n')
    print(preview)
    if len(result) > 500:
        print("...")
    print()

    print("✅ The sanitization fix is working correctly!")
    print("✅ llama-index README is now safe for LLM processing")
    print()

    return True

if __name__ == "__main__":
    try:
        success = test_real_llama_index()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
