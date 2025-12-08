"""
Blog Generator - Multi-Agent Blog Generation System v4.2

Architecture:
- Optimized: Split-crew (5GB RAM)  ✅ Default
- Standard:  Monolithic (9GB RAM)

Usage:
    from blog_generator import run_optimized_pipeline, run_standard_pipeline
    run_optimized_pipeline()  # Recommended
"""

__version__ = "4.2.0"
__author__ = "Ruslanmv"


def get_version():
    """Get package version"""
    return __version__


# Lazy pipeline imports
def run_standard_pipeline():
    """Standard pipeline (9GB RAM)"""
    from blog_generator.workflow.pipeline_standard import run_standard_pipeline as _run
    return _run()


def run_optimized_pipeline():
    """Optimized pipeline (5GB RAM) - RECOMMENDED"""
    from blog_generator.workflow.pipeline_optimized import run_optimized_pipeline as _run
    return _run()


# Export models on demand
def get_topic_class():
    """Get Topic class"""
    from blog_generator.core.models import Topic
    return Topic


def get_research_strategy_class():
    """Get ResearchStrategy class"""
    from blog_generator.core.models import ResearchStrategy
    return ResearchStrategy


__all__ = [
    "__version__",
    "get_version",
    "run_standard_pipeline",
    "run_optimized_pipeline",
    "get_topic_class",
    "get_research_strategy_class",
]