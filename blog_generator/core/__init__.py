"""Core utilities - Lazy imports for production"""

__all__ = [
    "Topic",
    "ResearchStrategy",
    "BASE_DIR",
    "BLOG_POSTS_DIR",
    "select_next_topic",
    "build_jekyll_post",
    "save_post",
    "validate_all_code_blocks",
    "extract_task_output",
]


def __getattr__(name):
    """Lazy import on attribute access"""
    
    # Models
    if name == "Topic":
        from blog_generator.core.models import Topic
        return Topic
    elif name == "ResearchStrategy":
        from blog_generator.core.models import ResearchStrategy
        return ResearchStrategy
    
    # Paths
    elif name in ("BASE_DIR", "BLOG_POSTS_DIR", "API_DIR", "DATA_DIR", "BASE_ASSETS_DIR", "COVERAGE_FILE"):
        from blog_generator.core.paths import (
            BASE_DIR, BLOG_POSTS_DIR, API_DIR, DATA_DIR, BASE_ASSETS_DIR, COVERAGE_FILE
        )
        return locals()[name]
    
    # Utils
    elif name in ("select_next_topic", "build_jekyll_post", "save_post", "slugify",
                  "ensure_blog_assets_topic_specific", "record_coverage", "detect_topic_type"):
        from blog_generator.core.utils import (
            select_next_topic, build_jekyll_post, save_post, slugify,
            ensure_blog_assets_topic_specific, record_coverage, detect_topic_type
        )
        return locals()[name]
    
    # Validation
    elif name in ("validate_python_code", "validate_all_code_blocks"):
        from blog_generator.core.validation import validate_python_code, validate_all_code_blocks
        return locals()[name]
    
    # Text cleaning
    elif name in ("clean_content", "clean_llm_output", "extract_task_output"):
        from blog_generator.core.text_cleaning import clean_content, clean_llm_output, extract_task_output
        return locals()[name]
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")