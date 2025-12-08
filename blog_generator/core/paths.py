"""Path constants"""
from pathlib import Path

from blog_generator.config import PROJECT_ROOT

# Directory structure
BASE_DIR = PROJECT_ROOT
BLOG_POSTS_DIR = BASE_DIR / "blog" / "posts"
API_DIR = BASE_DIR / "blog" / "api"
DATA_DIR = BASE_DIR / "data"
BASE_ASSETS_DIR = BASE_DIR / "assets" / "images"
COVERAGE_FILE = DATA_DIR / "blog_coverage.json"
LOG_DIR = BASE_DIR / "logs"

# Ensure directories exist
for directory in [LOG_DIR, DATA_DIR, BLOG_POSTS_DIR, BASE_ASSETS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)