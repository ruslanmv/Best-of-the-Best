#!/usr/bin/env python3
"""
scripts/generate_daily_blog.py

PRODUCTION v4.2 - Memory-Optimized Blog Generator

Single-file, production-ready wrapper with robust error handling.
Defaults to memory-optimized split-crew pipeline (5GB RAM vs 9GB).

Environment Variables:
    USE_MEMORY_OPTIMIZED: "true" (default) or "false"
    NEWS_LLM_MODEL: LLM model identifier
    OLLAMA_HOST: Ollama server URL
"""

import os
import sys
from pathlib import Path

# ============================================================================
# SETUP
# ============================================================================
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))


# ============================================================================
# MAIN
# ============================================================================
def main():
    """Main entry point"""
    
    # Get configuration
    use_optimized = os.getenv("USE_MEMORY_OPTIMIZED", "true").lower() not in ("false", "no", "0")
    llm_model = os.getenv("NEWS_LLM_MODEL", "not set")
    ollama_host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    
    # Print header
    print("=" * 70)
    print("Best-of-the-Best Blog Generator v4.2")
    print(f"Mode: {'Memory-Optimized' if use_optimized else 'Standard'}")
    print("=" * 70)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"LLM Model: {llm_model}")
    print(f"Ollama Host: {ollama_host}")
    print("")
    
    if use_optimized:
        print("🧠 Memory-Optimized Pipeline")
        print("   • Split-crew: Phase 1 (5 agents) + Phase 2 (6 agents)")
        print("   • Peak RAM: ~5GB (44% reduction)")
        print("   • GitHub-safe")
    else:
        print("⚡ Standard Pipeline")
        print("   • Monolithic: All 11 agents")
        print("   • Peak RAM: ~9GB")
        print("   • Requires high-memory system")
    
    print("")
    
    try:
        # Import and run
        if use_optimized:
            from blog_generator.workflow.pipeline_optimized import run_optimized_pipeline
            run_optimized_pipeline()
        else:
            from blog_generator.workflow.pipeline_standard import run_standard_pipeline
            run_standard_pipeline()
        
        print("")
        print("=" * 70)
        print("✅ SUCCESS")
        print("=" * 70)
        return 0
        
    except ImportError as e:
        print("")
        print("=" * 70)
        print("❌ IMPORT ERROR")
        print("=" * 70)
        print(f"Error: {e}")
        print("")
        print("Required package structure:")
        print("  blog_generator/")
        print("  ├── __init__.py")
        print("  ├── config.py")
        print("  ├── core/")
        print("  │   ├── __init__.py")
        print("  │   ├── models.py")
        print("  │   ├── paths.py")
        print("  │   ├── utils.py")
        print("  │   ├── validation.py")
        print("  │   └── text_cleaning.py")
        print("  ├── agents/")
        print("  │   ├── __init__.py")
        print("  │   ├── research_agents.py")
        print("  │   ├── writing_agents.py")
        print("  │   ├── research_tasks.py")
        print("  │   └── writing_tasks.py")
        print("  └── workflow/")
        print("      ├── __init__.py")
        print("      ├── crew_builder.py")
        print("      ├── pipeline_optimized.py")
        print("      └── pipeline_standard.py")
        print("")
        return 1
        
    except Exception as e:
        print("")
        print("=" * 70)
        print("❌ GENERATION FAILED")
        print("=" * 70)
        print(f"Error: {e}")
        print("")
        
        log_dir = PROJECT_ROOT / "logs"
        if log_dir.exists():
            print("Check logs:")
            print(f"  • {log_dir}/blog_generation_advanced.log")
            print("")
        
        import traceback
        print("Traceback:")
        print("-" * 70)
        traceback.print_exc()
        print("-" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())