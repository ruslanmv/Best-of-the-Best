"""
blog_generator/core/utils.py

Utility functions for blog generation - Production v4.2

Provides:
- Topic selection from JSON data
- Jekyll post building
- Image asset management
- Coverage tracking
- File operations
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from blog_generator.config import (
    logger,
    IMAGE_TOOLS_AVAILABLE,
    ImageTools,
    set_blog_context,
    get_blog_assets_dir,
)
from blog_generator.core.models import Topic
from blog_generator.core.paths import (
    BASE_DIR,
    BLOG_POSTS_DIR,
    API_DIR,
    DATA_DIR,
    BASE_ASSETS_DIR,
    COVERAGE_FILE,
)


# ============================================================================
# STRING UTILITIES
# ============================================================================

def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug.
    
    Args:
        text: Input text
        
    Returns:
        URL-safe slug
        
    Example:
        >>> slugify("Hello World!")
        'hello-world'
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "topic"


# ============================================================================
# JSON FILE OPERATIONS
# ============================================================================

def load_json(path: Path) -> Optional[Any]:
    """
    Load JSON file safely with error handling.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Parsed JSON data or None if error
    """
    if not path.exists():
        return None
    
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path.name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading {path.name}: {e}")
        return None


def load_coverage() -> List[Dict[str, Any]]:
    """
    Load blog coverage history.
    
    Returns:
        List of coverage entries
    """
    if not COVERAGE_FILE.exists():
        return []
    
    try:
        with COVERAGE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading coverage: {e}")
        return []


def save_coverage(entries: List[Dict[str, Any]]) -> None:
    """
    Save blog coverage history.
    
    Args:
        entries: List of coverage entries
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        with COVERAGE_FILE.open("w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
        logger.debug(f"Saved {len(entries)} coverage entries")
    except Exception as e:
        logger.error(f"Error saving coverage: {e}")


def max_version_for(coverage: List[Dict[str, Any]], kind: str, id_: str) -> int:
    """
    Get maximum version number for a topic.
    
    Args:
        coverage: Coverage list
        kind: Topic kind (package, repo, etc)
        id_: Topic identifier
        
    Returns:
        Maximum version number (0 if not found)
    """
    versions = [
        e["version"] 
        for e in coverage 
        if e.get("kind") == kind and e.get("id") == id_
    ]
    return max(versions) if versions else 0


# ============================================================================
# TOPIC SELECTION
# ============================================================================

def select_next_topic() -> Topic:
    """
    Select next blog topic from JSON data files.
    
    Priority order:
    1. Uncovered packages
    2. Uncovered repos
    3. Uncovered papers
    4. Uncovered tutorials
    5. Version updates for existing packages
    
    Returns:
        Topic object
        
    Raises:
        SystemExit: If no content available
    """
    logger.info("📊 Selecting next topic from JSON files...")
    
    # Load all data sources
    packages_data = load_json(API_DIR / "packages.json") or {}
    repos_data = load_json(API_DIR / "repositories.json") or {}
    papers_data = load_json(API_DIR / "papers.json") or {}
    tutorials_data = load_json(API_DIR / "tutorials.json") or {}
    
    coverage = load_coverage()
    
    # Extract lists (handle multiple JSON structures)
    packages = (
        packages_data.get("packages") or 
        packages_data.get("top_packages") or 
        []
    )
    repos = (
        repos_data.get("repositories") or 
        repos_data.get("top_repositories") or 
        []
    )
    papers = (
        papers_data.get("papers") or 
        papers_data.get("most_cited") or 
        []
    )
    
    if isinstance(tutorials_data, list):
        tutorials = tutorials_data
    else:
        tutorials = tutorials_data.get("tutorials") or []
    
    logger.info(
        f"   Content: {len(packages)} packages, {len(repos)} repos, "
        f"{len(papers)} papers, {len(tutorials)} tutorials"
    )
    
    if not any([packages, repos, papers, tutorials]):
        logger.error("❌ No content in JSON files!")
        logger.error(f"   Check: {API_DIR}")
        sys.exit(1)
    
    def pick_uncovered(items: List[Dict[str, Any]], kind: str) -> Optional[Topic]:
        """Pick first uncovered item of given kind"""
        for item in items:
            # Extract metadata based on kind
            if kind == "package":
                id_ = item.get("name") or item.get("id")
                if not id_:
                    continue
                title = item.get("name") or id_
                summary = item.get("summary") or item.get("description") or f"Python package: {title}"
                tags = (item.get("tags") or ["python", "package"])[:6]
                url = item.get("url") or item.get("homepage")
                
            elif kind == "repo":
                id_ = item.get("full_name") or item.get("name")
                if not id_:
                    continue
                title = item.get("name") or id_.split("/")[-1] if "/" in str(id_) else id_
                summary = item.get("description") or f"GitHub repository: {title}"
                tags = (item.get("tags") or ["github", "repository"])[:6]
                url = item.get("url") or item.get("html_url")
                
            elif kind == "paper":
                id_ = item.get("title") or item.get("doi") or item.get("id")
                if not id_:
                    continue
                title = item.get("title") or id_
                summary = item.get("abstract") or item.get("summary") or f"Research: {title}"
                tags = (item.get("tags") or ["research", "paper"])[:6]
                url = item.get("url") or item.get("link")
                
            else:  # tutorial
                title = item.get("title")
                if not title:
                    continue
                id_ = item.get("id") or item.get("slug") or slugify(title)
                summary = item.get("excerpt") or item.get("description") or f"Tutorial: {title}"
                tags = (item.get("tags") or ["tutorial"])[:6]
                url = item.get("url") or item.get("link")
            
            # Check if uncovered
            if max_version_for(coverage, kind, id_) == 0:
                logger.info(f"✅ Selected: {kind.upper()} - {title}")
                return Topic(kind, id_, title, url, summary, tags, 1)
        
        return None
    
    # Try each kind in priority order
    for kind, items in [
        ("package", packages),
        ("repo", repos),
        ("paper", papers),
        ("tutorial", tutorials),
    ]:
        if items:
            topic = pick_uncovered(items, kind)
            if topic:
                return topic
    
    # All topics covered - do version update
    logger.info("📝 All topics covered, creating version update...")
    
    if packages:
        item = packages[0]
        id_ = item.get("name") or item.get("id") or "unknown"
        title = item.get("name") or id_
        summary = item.get("summary") or f"Python package: {title}"
        tags = (item.get("tags") or ["python", "package"])[:6]
        url = item.get("url") or item.get("homepage")
        version = max_version_for(coverage, "package", id_) + 1
        
        logger.info(f"✅ Version update: {title} (v{version})")
        return Topic("package", id_, title, url, summary, tags, version)
    
    # Absolute fallback
    logger.warning("⚠️  No topics available, using fallback")
    return Topic(
        "package",
        "ai-technologies",
        "AI Technologies Update",
        None,
        "Latest developments in AI and Machine Learning",
        ["ai", "machine-learning"],
        1
    )


def detect_topic_type(topic: Topic) -> Tuple[str, str]:
    """
    Detect topic type and extract identifier.
    
    Args:
        topic: Topic object
        
    Returns:
        (type, identifier) tuple where type is 'package', 'repo', or 'general'
    """
    if topic.kind == "package":
        return ("package", topic.id)
    elif topic.kind == "repo":
        if topic.url and "github.com" in topic.url:
            return ("repo", topic.url)
        return ("repo", topic.id)
    elif topic.url and "github.com" in topic.url.lower():
        return ("repo", topic.url)
    else:
        return ("general", topic.title)


# ============================================================================
# IMAGE ASSET MANAGEMENT
# ============================================================================

def generate_image_queries(topic: Topic) -> Dict[str, str]:
    """
    Generate image search queries for blog assets.
    
    Args:
        topic: Topic object
        
    Returns:
        Dict mapping asset names to search queries
    """
    title_lower = topic.title.lower()
    tags_str = " ".join(topic.tags).lower()
    
    # Extract technical keywords
    tech_terms = [
        "python", "javascript", "java", "rust", "go",
        "machine", "learning", "ai", "neural", "deep",
        "data", "science", "analytics", "visualization",
        "cloud", "kubernetes", "docker", "devops",
        "web", "api", "rest", "graphql",
        "database", "sql", "nosql", "redis", "mongodb",
    ]
    
    keywords = [term for term in tech_terms if term in title_lower or term in tags_str]
    
    # Fallback to first significant words
    if not keywords:
        words = [w.lower() for w in topic.title.split() if len(w) > 3]
        keywords = words[:2]
    
    # Determine base context
    if topic.kind == "package":
        base = "programming code technology"
    elif topic.kind == "repo":
        base = "software development coding"
    elif topic.kind == "paper":
        base = "research science innovation"
    else:
        base = "technology digital innovation"
    
    # Build queries
    queries = {}
    
    if keywords:
        queries["header-primary"] = f"{' '.join(keywords[:2])} abstract technology"
        queries["teaser-main"] = f"{keywords[0]} modern innovation"
    else:
        queries["header-primary"] = f"{base} abstract"
        queries["teaser-main"] = f"{base} modern"
    
    if len(keywords) > 1:
        queries["header-secondary"] = f"{keywords[1]} digital visualization"
    else:
        queries["header-secondary"] = f"{base} visualization"
    
    queries["content-workspace"] = f"{keywords[0] if keywords else 'technology'} workspace"
    
    return queries


def ensure_blog_assets_topic_specific(
    topic: Topic,
    slug: str,
    date_str: str
) -> Path:
    """
    Ensure blog assets directory exists and contains images.
    
    Creates directory and downloads images using Pexels API if available.
    Falls back to placeholder creation if API unavailable.
    
    Args:
        topic: Topic object
        slug: URL slug
        date_str: Date string (YYYY-MM-DD)
        
    Returns:
        Path to blog assets directory
    """
    # Determine assets directory
    if IMAGE_TOOLS_AVAILABLE:
        blog_dir = get_blog_assets_dir()
    else:
        blog_dir = BASE_ASSETS_DIR / f"{date_str}-{slug}"
        blog_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📁 Assets directory: {blog_dir.relative_to(BASE_DIR)}")
    
    # Check if images already exist
    required_images = ["header-ai-abstract.jpg", "teaser-ai.jpg"]
    existing = [img for img in required_images if (blog_dir / img).exists()]
    
    if len(existing) == len(required_images):
        logger.info("✅ All assets already exist")
        return blog_dir
    
    # Try to download with Pexels
    api_key = os.getenv("PEXELS_API_KEY")
    
    if IMAGE_TOOLS_AVAILABLE and api_key:
        logger.info("📸 Downloading images from Pexels...")
        queries = generate_image_queries(topic)
        
        assets_to_create = [
            ("header", "ai-abstract", queries["header-primary"]),
            ("teaser", "ai", queries["teaser-main"]),
            ("header", "data-science", queries.get("header-secondary", "data science")),
            ("header", "cloud", queries.get("content-workspace", "cloud technology")),
        ]
        
        for asset_type, descriptor, search_query in assets_to_create:
            asset_name = f"{asset_type}-{descriptor}"
            asset_path = blog_dir / f"{asset_name}.jpg"
            
            if asset_path.exists():
                continue
            
            try:
                result = ImageTools.get_stock_photo(
                    search_query,
                    filename=f"{asset_name}.jpg",
                    asset_type=asset_type,
                )
                if result:
                    logger.info(f"   ✓ Downloaded: {asset_name}.jpg")
            except Exception as e:
                logger.warning(f"   ⚠️  Failed to download {asset_name}: {e}")
    
    else:
        if not api_key:
            logger.warning("⚠️  PEXELS_API_KEY not set, using placeholders")
        
        # Create placeholder images
        for img in required_images:
            img_path = blog_dir / img
            if not img_path.exists():
                img_path.write_text(f"# Placeholder: {img}\n")
                logger.info(f"   📝 Created placeholder: {img}")
    
    return blog_dir


# ============================================================================
# JEKYLL POST BUILDING
# ============================================================================

def build_jekyll_post(
    date: datetime,
    topic: Topic,
    body: str,
    meta: Dict[str, Any],
    blog_assets_dir: Path,
) -> Tuple[str, str]:
    """
    Build Jekyll post with front matter.
    
    Args:
        date: Publication date
        topic: Topic object
        body: Article body (Markdown)
        meta: Metadata dict (title, excerpt, tags)
        blog_assets_dir: Path to assets directory
        
    Returns:
        (filename, full_content) tuple
    """
    # Extract metadata
    title = meta.get("title", topic.title)
    excerpt = meta.get("excerpt", topic.summary or "")
    tags = (meta.get("tags") or topic.tags or ["ai"])[:8]
    
    # Date formatting
    date_iso = date.strftime("%Y-%m-%dT09:00:00+00:00")
    date_prefix = date.strftime("%Y-%m-%d")
    
    # Build filename
    version_suffix = f"-v{topic.version}" if topic.version > 1 else ""
    slug = f"{topic.kind}-{slugify(topic.title)}{version_suffix}"
    filename = f"{date_prefix}-{slug}.md"
    
    # Escape excerpt
    safe_excerpt = (excerpt or "").replace('"', "'")
    
    # Build tags YAML
    tag_lines = "\n  - " + "\n  - ".join(tags)
    
    # Image paths (relative to site root)
    assets_rel = blog_assets_dir.relative_to(BASE_DIR)
    header_image = f"/{assets_rel}/header-ai-abstract.jpg"
    teaser_image = f"/{assets_rel}/teaser-ai.jpg"
    
    # Smart header selection based on tags
    if "data" in " ".join(tags).lower():
        alt_header = blog_assets_dir / "header-data-science.jpg"
        if alt_header.exists():
            header_image = f"/{assets_rel}/header-data-science.jpg"
    elif "cloud" in " ".join(tags).lower():
        alt_header = blog_assets_dir / "header-cloud.jpg"
        if alt_header.exists():
            header_image = f"/{assets_rel}/header-cloud.jpg"
    
    # Build full content
    content = f"""---
title: "{title}"
date: {date_iso}
last_modified_at: {date_iso}
categories:
  - Engineering
  - AI
tags:{tag_lines}
excerpt: "{safe_excerpt}"
header:
  overlay_image: {header_image}
  overlay_filter: 0.5
  teaser: {teaser_image}
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "Ruslanmv"
sidebar:
  nav: "blog"
---

{body.strip()}

---

<small>Generated by Best-of-the-Best Blog Generator v4.2</small>
"""
    
    return filename, content


# ============================================================================
# FILE OPERATIONS
# ============================================================================

def save_post(filename: str, content: str) -> Path:
    """
    Save blog post to file with collision handling.
    
    Args:
        filename: Post filename
        content: Full post content
        
    Returns:
        Path to saved file
    """
    BLOG_POSTS_DIR.mkdir(parents=True, exist_ok=True)
    path = BLOG_POSTS_DIR / filename
    
    # Handle filename collisions
    if path.exists():
        timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
        filename = f"{path.stem}-{timestamp}{path.suffix}"
        path = BLOG_POSTS_DIR / filename
        logger.warning(f"⚠️  File exists, using: {filename}")
    
    # Write file
    with path.open("w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info(f"✅ Saved: {path.relative_to(BASE_DIR)}")
    return path


def record_coverage(topic: Topic, filename: str) -> None:
    """
    Record topic coverage in tracking file.
    
    Args:
        topic: Topic object
        filename: Generated filename
    """
    coverage = load_coverage()
    
    entry = {
        "kind": topic.kind,
        "id": topic.id,
        "version": topic.version,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "filename": filename,
    }
    
    coverage.append(entry)
    save_coverage(coverage)
    
    logger.info(f"📊 Recorded coverage: {topic.kind}/{topic.id} v{topic.version}")