"""Core utilities and domain logic"""

from blog_generator.core.models import Topic, ResearchStrategy
from blog_generator.core.paths import (
    BASE_DIR,
    BLOG_POSTS_DIR,
    API_DIR,
    DATA_DIR,
    BASE_ASSETS_DIR,
    COVERAGE_FILE,
)
from blog_generator.core.utils import (
    select_next_topic,
    detect_topic_type,
    generate_image_queries,
    ensure_blog_assets_topic_specific,
    build_jekyll_post,
    save_post,
    record_coverage,
    slugify,
)
from blog_generator.core.validation import (
    validate_python_code,
    validate_all_code_blocks,
)
from blog_generator.core.text_cleaning import (
    clean_content,
    clean_llm_output,
    extract_task_output,
)

__all__ = [
    # Models
    "Topic",
    "ResearchStrategy",
    # Paths
    "BASE_DIR",
    "BLOG_POSTS_DIR",
    "API_DIR",
    "DATA_DIR",
    "BASE_ASSETS_DIR",
    "COVERAGE_FILE",
    # Utils
    "select_next_topic",
    "detect_topic_type",
    "generate_image_queries",
    "ensure_blog_assets_topic_specific",
    "build_jekyll_post",
    "save_post",
    "record_coverage",
    "slugify",
    # Validation
    "validate_python_code",
    "validate_all_code_blocks",
    # Text cleaning
    "clean_content",
    "clean_llm_output",
    "extract_task_output",
]