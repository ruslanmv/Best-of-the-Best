#!/usr/bin/env python3
"""
Configuration - Environment, logging, and legacy imports
"""
import os
import sys
import logging
from pathlib import Path

# ============================================================================
# PATHS
# ============================================================================
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Ensure scripts directory is importable (for search.py, finder.py, etc.)
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# ============================================================================
# ENVIRONMENT
# ============================================================================
try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:
    pass


def is_ollama_llm() -> bool:
    """Check if using Ollama."""
    return "ollama" in os.getenv("NEWS_LLM_MODEL", "").lower()


def use_memory_optimized() -> bool:
    """Check if memory-optimized mode enabled."""
    return os.getenv("USE_MEMORY_OPTIMIZED", "true").lower() == "true"


# ============================================================================
# LOGGING
# ============================================================================
logger = logging.getLogger("blog_generator")
if not logger.handlers:
    logger.setLevel(logging.INFO)

    # File
    fh = logging.FileHandler(LOG_DIR / "blog_generation_advanced.log", mode="a")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

    # Console
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(sh)

# ============================================================================
# LLM CLIENT
# ============================================================================
try:
    from llm_client import llm  # type: ignore

    logger.info("✅ LLM client imported")
except ImportError as e:
    logger.error(f"❌ LLM client import failed: {e}")
    raise

# ============================================================================
# SEARCH / README / HEALTH TOOLS (search.py)
# ============================================================================
try:
    from search import (  # type: ignore
        search_web,
        scrape_webpage,
        scrape_readme,
        get_package_health,
    )

    SEARCH_TOOLS_AVAILABLE = True
    README_TOOLS_AVAILABLE = True
    logger.info("✅ Search tools imported")
except ImportError as e:
    logger.warning(f"⚠️  Search tools not available: {e}")
    SEARCH_TOOLS_AVAILABLE = False
    README_TOOLS_AVAILABLE = False
    search_web = None
    scrape_webpage = None
    scrape_readme = None
    get_package_health = None

# ============================================================================
# DEEP DOCUMENTATION FINDER (finder.py)
# ============================================================================
DEEP_FIND_TOOLS_AVAILABLE = False
deep_find_documentation = None

try:
    # finder.py lives in SCRIPTS_DIR, which is already on sys.path
    from finder import deep_find_documentation as _deep_find_documentation  # type: ignore

    deep_find_documentation = _deep_find_documentation
    DEEP_FIND_TOOLS_AVAILABLE = True
    logger.info("✅ Deep documentation finder imported")
except ImportError as e:
    logger.warning(f"⚠️  Deep documentation finder not available: {e}")
    deep_find_documentation = None
    DEEP_FIND_TOOLS_AVAILABLE = False

# ============================================================================
# IMAGE TOOLS
# ============================================================================
try:
    from image_tools import (  # type: ignore
        ImageTools,
        set_blog_context,
        get_blog_assets_dir,
    )

    IMAGE_TOOLS_AVAILABLE = True
    logger.info("✅ Image tools imported")
except ImportError as e:
    logger.warning(f"⚠️  Image tools not available: {e}")
    IMAGE_TOOLS_AVAILABLE = False

    class ImageTools:  # type: ignore
        @staticmethod
        def get_stock_photo(*args, **kwargs):
            return None

    def set_blog_context(*args, **kwargs):
        return PROJECT_ROOT / "assets" / "images"

    def get_blog_assets_dir():
        return PROJECT_ROOT / "assets" / "images"


# ============================================================================
# EXPORTS
# ============================================================================
__all__ = [
    # Paths
    "PACKAGE_ROOT",
    "PROJECT_ROOT",
    "SCRIPTS_DIR",
    "LOG_DIR",
    # Environment functions
    "is_ollama_llm",
    "use_memory_optimized",
    # Logging
    "logger",
    # LLM
    "llm",
    # Search tools
    "SEARCH_TOOLS_AVAILABLE",
    "README_TOOLS_AVAILABLE",
    "search_web",
    "scrape_webpage",
    "scrape_readme",
    "get_package_health",
    # Deep finder
    "DEEP_FIND_TOOLS_AVAILABLE",
    "deep_find_documentation",
    # Image tools
    "IMAGE_TOOLS_AVAILABLE",
    "ImageTools",
    "set_blog_context",
    "get_blog_assets_dir",
]