#!/usr/bin/env python3
"""
scripts/generate_daily_blog.py

PRODUCTION v2.0 - Daily blog generator for ruslanmv.com/Best-of-the-Best

CRITICAL FIXES:
1. Path calculation: BASE_DIR = CURRENT_DIR.parent (was .parents[1])
2. Comprehensive logging with file output
3. Automatic backup before overwrites
4. Better error handling and recovery
5. Progress tracking and validation

Output:
- blog/posts/YYYY-MM-DD-<slug>.md (format: 2024-11-22-example-langchain.md)
- data/blog_coverage.json (tracking)
- logs/blog_generation.log (debugging)
"""

import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure we can import llm_client from the scripts directory
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

from crewai import Agent, Task, Crew, Process  # type: ignore
from llm_client import llm  # multi-provider LLM instance


# ============================================================================
# PATH CONFIGURATION - CRITICAL FIX!
# ============================================================================
# ❌ OLD BUG: BASE_DIR = CURRENT_DIR.parents[1]  # Goes TWO levels up!
# ✅ FIXED:    BASE_DIR = CURRENT_DIR.parent     # Goes ONE level up!
#
# Example: /project/scripts/generate_daily_blog.py
#   CURRENT_DIR = /project/scripts
#   CURRENT_DIR.parent = /project ✅
#   CURRENT_DIR.parents[1] = / (or parent of /project) ❌

BASE_DIR = CURRENT_DIR.parent
BLOG_POSTS_DIR = BASE_DIR / "blog" / "posts"
API_DIR = BASE_DIR / "blog" / "api"
DATA_DIR = BASE_DIR / "data"
COVERAGE_FILE = DATA_DIR / "blog_coverage.json"
LOG_DIR = BASE_DIR / "logs"

# Ensure critical directories exist
for directory in [LOG_DIR, DATA_DIR, BLOG_POSTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================================================
# LOGGING SETUP
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "blog_generation.log", mode='a'),
    ],
)
logger = logging.getLogger(__name__)


# ---------- Data structures ----------

@dataclass
class Topic:
    kind: str
    id: str
    title: str
    url: Optional[str]
    summary: Optional[str]
    tags: List[str]
    version: int


# ---------- Helper functions ----------

def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "topic"


def load_json(path: Path) -> Optional[Any]:
    """Safely load JSON file."""
    if not path.exists():
        logger.debug(f"File not found: {path}")
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error reading {path}: {e}")
        return None


def load_coverage() -> List[Dict[str, Any]]:
    """Load blog coverage tracking."""
    if not COVERAGE_FILE.exists():
        logger.info("No existing coverage file")
        return []
    try:
        with COVERAGE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"Loaded {len(data)} coverage entries")
            return data
    except Exception as e:
        logger.error(f"Error loading coverage: {e}")
        return []


def save_coverage(entries: List[Dict[str, Any]]) -> None:
    """Save coverage with automatic backup."""
    # Backup existing file
    if COVERAGE_FILE.exists():
        backup = DATA_DIR / f"blog_coverage.backup.{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            import shutil
            shutil.copy2(COVERAGE_FILE, backup)
            logger.debug(f"Created backup: {backup.name}")
        except Exception as e:
            logger.warning(f"Backup failed: {e}")
    
    # Save new data
    with COVERAGE_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    logger.info(f"Saved {len(entries)} coverage entries")


def max_version_for(coverage: List[Dict[str, Any]], kind: str, id_: str) -> int:
    """Get max version for a topic."""
    versions = [e["version"] for e in coverage if e["kind"] == kind and e["id"] == id_]
    return max(versions) if versions else 0


# ---------- Topic selection ----------

def select_next_topic() -> Topic:
    """
    Select next blog topic based on priority:
    1. Uncovered packages
    2. Uncovered repos
    3. Uncovered papers
    4. Uncovered tutorials
    5. Version updates (v2, v3, etc.)
    """
    logger.info("Selecting next topic...")
    
    # Load data sources
    packages_data = load_json(API_DIR / "packages.json") or {}
    repos_data = load_json(API_DIR / "repositories.json") or {}
    papers_data = load_json(API_DIR / "papers.json") or load_json(API_DIR / "research.json") or {}
    tutorials_data = load_json(API_DIR / "tutorials.json") or load_json(API_DIR / "data.json") or {}
    
    coverage = load_coverage()
    
    # Extract items
    packages = packages_data.get("packages") or packages_data.get("top_packages") or []
    repos = repos_data.get("repositories") or repos_data.get("top_repositories") or []
    papers = papers_data.get("papers") or papers_data.get("most_cited") or papers_data.get("research") or []
    
    if isinstance(tutorials_data, list):
        tutorials = tutorials_data
    else:
        tutorials = tutorials_data.get("tutorials") or tutorials_data.get("top_tutorials") or []
    
    logger.info(f"Data sources: {len(packages)} packages, {len(repos)} repos, {len(papers)} papers, {len(tutorials)} tutorials")
    
    def pick_uncovered(items: List[Dict], kind: str) -> Optional[Topic]:
        """Find first uncovered item of given kind."""
        for item in items:
            # Extract fields based on kind
            if kind == "package":
                id_ = item.get("name") or item.get("id", "unknown")
                title = item.get("name") or item.get("title", id_)
                summary = item.get("summary") or item.get("description", f"Python package: {title}")
            elif kind == "repo":
                id_ = item.get("full_name") or item.get("name") or item.get("id", "unknown")
                title = item.get("name") or item.get("full_name", id_)
                summary = item.get("description", f"GitHub repository: {title}")
            elif kind == "paper":
                id_ = item.get("title") or item.get("doi") or item.get("id", "unknown")
                title = item.get("title", id_)
                summary = item.get("abstract") or item.get("summary", f"Research: {title}")
            else:  # tutorial
                id_ = item.get("id") or item.get("slug") or item.get("title", "unknown")
                title = item.get("title", id_)
                summary = item.get("excerpt") or item.get("description", f"Tutorial: {title}")
            
            # Check if uncovered
            if max_version_for(coverage, kind, id_) == 0:
                url = item.get("url") or item.get("link") or item.get("homepage")
                tags = (item.get("tags") or [])[:6] if isinstance(item.get("tags"), list) else []
                logger.info(f"Selected new {kind}: {title}")
                return Topic(kind, id_, title, url, summary, tags, 1)
        return None
    
    # Try each kind in priority order
    for kind, items in [("package", packages), ("repo", repos), ("paper", papers), ("tutorial", tutorials)]:
        topic = pick_uncovered(items, kind)
        if topic:
            return topic
    
    # All have v1, select lowest version package for update
    if packages:
        candidates = []
        for item in packages:
            id_ = item.get("name") or item.get("id", "unknown")
            title = item.get("name") or item.get("title", id_)
            url = item.get("url") or item.get("link") or item.get("homepage")
            summary = item.get("summary") or item.get("description", f"Python package: {title}")
            tags = (item.get("tags") or [])[:6] if isinstance(item.get("tags"), list) else []
            current_v = max_version_for(coverage, "package", id_)
            candidates.append((current_v, Topic("package", id_, title, url, summary, tags, current_v + 1)))
        
        if candidates:
            candidates.sort(key=lambda x: x[0])
            logger.info(f"Selected version update: {candidates[0][1].title} (v{candidates[0][1].version})")
            return candidates[0][1]
    
    # Absolute fallback
    logger.warning("No topics found, using fallback")
    return Topic("package", "fallback", "AI Technologies Update", None, "Latest in AI/ML", ["ai"], 1)


# ---------- CrewAI pipeline ----------

def build_blog_crew(topic: Topic) -> Tuple[Crew, Tuple[Task, Task, Task]]:
    """Build 3-agent CrewAI pipeline: Strategist -> Writer -> Publisher."""
    
    strategist = Agent(
        role="AI Content Strategist",
        goal="Design an enterprise-focused blog outline",
        backstory="Expert at identifying impactful angles for technical audiences",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    writer = Agent(
        role="Senior Technical Writer",
        goal="Write detailed, practical blog posts with code examples",
        backstory="Creates content that balances technical depth with business value",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    publisher = Agent(
        role="Jekyll Metadata Curator",
        goal="Generate SEO-optimized metadata",
        backstory="Ensures consistent, searchable blog metadata",
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    topic_context = f"""Kind: {topic.kind}
ID: {topic.id}
Title: {topic.title}
URL: {topic.url or 'n/a'}
Summary: {topic.summary or 'n/a'}
Tags: {', '.join(topic.tags) if topic.tags else 'n/a'}
Version: v{topic.version}"""
    
    # Task 1: Outline
    t1 = Task(
        description=f"""Topic from Best-of-the-Best dashboard:

{topic_context}

Create a blog outline (800-1200 words target) with sections:
1. Executive Summary
2. What it is & why it matters
3. Technical Deep Dive
4. Example Implementation (Python/pseudo-code)
5. Business ROI / Use Cases
6. Limitations & Alternatives
7. Conclusion / Next Steps

{f"Include: What's new in v{topic.version}" if topic.version > 1 else ""}""",
        expected_output="Markdown outline with headings and bullets",
        agent=strategist,
    )
    
    # Task 2: Write article
    t2 = Task(
        description=f"""Write full blog article about: {topic.title}

Description: {topic.summary or 'n/a'}

Requirements:
- 800-1200 words minimum
- Multiple ## and ### headings from outline
- At least ONE ```python or ```pseudo code block
- NO YAML front matter
- NO title at top (start with content)
- NO meta comments
{f"- Include dedicated '## What's New in v{topic.version}' section" if topic.version > 1 else ""}""",
        expected_output="Complete markdown article body (no front matter)",
        agent=writer,
        context=[t1],
    )
    
    # Task 3: Metadata
    t3 = Task(
        description="""Generate metadata JSON from article.

Return only JSON:
{"title": "...", "excerpt": "...", "tags": ["tag1", "tag2", ...]}

Constraints:
- Title: ≤80 chars, no quotes
- Excerpt: 1-2 sentences, ≤220 chars
- Tags: 4-8 lowercase tags, hyphens only

JSON only, no other text.""",
        expected_output="JSON object with title, excerpt, tags",
        agent=publisher,
        context=[t1, t2],
    )
    
    crew = Crew(
        agents=[strategist, writer, publisher],
        tasks=[t1, t2, t3],
        process=Process.sequential,
        verbose=False,
    )
    
    return crew, (t1, t2, t3)


# ---------- Post building ----------

def build_jekyll_post(date: datetime, topic: Topic, body: str, meta: Dict) -> Tuple[str, str]:
    """Build Jekyll post with front matter."""
    title = meta.get("title", topic.title)
    excerpt = meta.get("excerpt", topic.summary or "")
    tags = (meta.get("tags") or topic.tags or ["ai"])[:8]
    
    date_iso = date.strftime("%Y-%m-%dT09:00:00-00:00")
    date_prefix = date.strftime("%Y-%m-%d")
    
    version_suffix = f"-v{topic.version}" if topic.version > 1 else ""
    slug = f"{topic.kind}-{slugify(topic.title)}{version_suffix}"
    filename = f"{date_prefix}-{slug}.md"
    
    safe_excerpt = (excerpt or "").replace('"', "'")
    tag_lines = "\n  - " + "\n  - ".join(tags)
    
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
  overlay_image: /assets/images/header-ai-abstract.jpg
  overlay_filter: 0.5
  teaser: /assets/images/teaser-ai.jpg
toc: true
toc_label: "Table of Contents"
toc_sticky: true
author: "AI Multi-Agent System"
sidebar:
  nav: "blog"
---

{body.strip()}

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
"""
    
    return filename, content


def save_post(filename: str, content: str) -> Path:
    """Save post with collision handling."""
    path = BLOG_POSTS_DIR / filename
    
    if path.exists():
        timestamp = datetime.utcnow().strftime("%H%M%S")
        filename = f"{path.stem}-{timestamp}{path.suffix}"
        path = BLOG_POSTS_DIR / filename
        logger.warning(f"File exists, using: {filename}")
    
    with path.open("w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info(f"✅ Saved: {path}")
    return path


def record_coverage(topic: Topic, filename: str) -> None:
    """Record topic coverage."""
    coverage = load_coverage()
    coverage.append({
        "kind": topic.kind,
        "id": topic.id,
        "version": topic.version,
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "filename": filename,
    })
    save_coverage(coverage)


# ---------- Validation ----------

def validate_body(body: str) -> None:
    """Validate article quality."""
    if len(body) < 800:
        raise RuntimeError(f"Body too short: {len(body)} chars (min 800)")
    if "## " not in body:
        raise RuntimeError("No '##' headings found")
    if "```" not in body:
        raise RuntimeError("No code blocks found")
    logger.info(f"✅ Validation passed: {len(body)} chars, {len(body.split())} words")


# ---------- Main ----------

def main() -> None:
    """Main entry point."""
    logger.info("="*70)
    logger.info("Best-of-the-Best Blog Generator v2.0 (Production)")
    logger.info("="*70)
    logger.info(f"BASE_DIR: {BASE_DIR}")
    logger.info(f"BLOG_POSTS_DIR: {BLOG_POSTS_DIR}")
    logger.info(f"API_DIR: {API_DIR}")
    
    if not API_DIR.exists():
        logger.error(f"❌ API directory missing: {API_DIR}")
        sys.exit(1)
    
    try:
        # Select topic
        topic = select_next_topic()
        logger.info(f"📝 Topic: {topic.kind} | {topic.title} (v{topic.version})")
        
        # Build and run crew
        crew, (t1, t2, t3) = build_blog_crew(topic)
        logger.info("🚀 Running CrewAI agents...")
        result = crew.kickoff()
        
        if not result:
            raise RuntimeError("No result from CrewAI")
        
        # Extract and validate
        body = (t2.output.raw if t2.output else "").strip()
        if not body:
            raise RuntimeError("Empty body from writer")
        
        validate_body(body)
        
        # Parse metadata
        meta_raw = (t3.output.raw if t3.output else "{}").strip()
        try:
            json_start = meta_raw.find("{")
            json_end = meta_raw.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                meta = json.loads(meta_raw[json_start:json_end])
            else:
                meta = json.loads(meta_raw)
        except Exception as e:
            logger.warning(f"Metadata parse failed: {e}")
            meta = {"title": topic.title, "excerpt": topic.summary, "tags": topic.tags}
        
        # Build and save
        filename, content = build_jekyll_post(datetime.utcnow(), topic, body, meta)
        path = save_post(filename, content)
        record_coverage(topic, filename)
        
        # Success
        logger.info("="*70)
        logger.info("✅ BLOG POST GENERATED")
        logger.info(f"   File: {path}")
        logger.info(f"   Title: {meta.get('title', topic.title)}")
        logger.info(f"   Words: ~{len(body.split())}")
        logger.info("="*70)
        
    except Exception as e:
        logger.error("="*70)
        logger.error(f"❌ GENERATION FAILED: {e}")
        logger.error("="*70)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()