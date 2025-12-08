"""Configuration - Environment, logging, and legacy imports"""
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

sys.path.insert(0, str(SCRIPTS_DIR))

# ============================================================================
# ENVIRONMENT
# ============================================================================
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env", override=False)
except ImportError:
    pass


def is_ollama_llm():
    """Check if using Ollama"""
    return "ollama" in os.getenv("NEWS_LLM_MODEL", "").lower()


def use_memory_optimized():
    """Check if memory-optimized mode enabled"""
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
# LEGACY IMPORTS
# ============================================================================
try:
    from llm_client import llm
    logger.info("✅ LLM client imported")
except ImportError as e:
    logger.error(f"❌ LLM client import failed: {e}")
    raise

try:
    from search import search_web, scrape_webpage, scrape_readme, get_package_health
    SEARCH_TOOLS_AVAILABLE = True
    README_TOOLS_AVAILABLE = True
    logger.info("✅ Search tools imported")
except ImportError:
    logger.warning("⚠️  Search tools not available")
    SEARCH_TOOLS_AVAILABLE = False
    README_TOOLS_AVAILABLE = False
    search_web = scrape_webpage = scrape_readme = get_package_health = None

try:
    from image_tools import ImageTools, set_blog_context, get_blog_assets_dir
    IMAGE_TOOLS_AVAILABLE = True
    logger.info("✅ Image tools imported")
except ImportError:
    logger.warning("⚠️  Image tools not available")
    IMAGE_TOOLS_AVAILABLE = False
    
    class ImageTools:
        @staticmethod
        def get_stock_photo(*args, **kwargs):
            return None
    
    def set_blog_context(*args, **kwargs):
        return PROJECT_ROOT / "assets" / "images"
    
    def get_blog_assets_dir():
        return PROJECT_ROOT / "assets" / "images"