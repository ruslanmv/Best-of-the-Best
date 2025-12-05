#!/usr/bin/env python3
"""
scripts/generate_daily_blog.py

PRODUCTION v2.1 - Daily blog generator with quality improvements

FIXES IN v2.1:
- Remove LLM meta-commentary from output
- Fix date generation (force current year)
- Normalize heading format
- Better writer instructions
- Post-processing cleanup
- Safe regex patterns with fallback

Output:
- blog/posts/YYYY-MM-DD-<slug>.md
- data/blog_coverage.json
- logs/blog_generation.log
"""

import json
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

from crewai import Agent, Task, Crew, Process  # type: ignore
from llm_client import llm

# ============================================================================
# PATH CONFIGURATION
# ============================================================================
BASE_DIR = CURRENT_DIR.parent
BLOG_POSTS_DIR = BASE_DIR / "blog" / "posts"
API_DIR = BASE_DIR / "blog" / "api"
DATA_DIR = BASE_DIR / "data"
COVERAGE_FILE = DATA_DIR / "blog_coverage.json"
LOG_DIR = BASE_DIR / "logs"

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


@dataclass
class Topic:
    kind: str
    id: str
    title: str
    url: Optional[str]
    summary: Optional[str]
    tags: List[str]
    version: int


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
    if COVERAGE_FILE.exists():
        backup = DATA_DIR / f"blog_coverage.backup.{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        try:
            import shutil
            shutil.copy2(COVERAGE_FILE, backup)
            logger.debug(f"Created backup: {backup.name}")
        except Exception as e:
            logger.warning(f"Backup failed: {e}")
    
    with COVERAGE_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    logger.info(f"Saved {len(entries)} coverage entries")


def max_version_for(coverage: List[Dict[str, Any]], kind: str, id_: str) -> int:
    """Get max version for a topic."""
    versions = [e["version"] for e in coverage if e["kind"] == kind and e["id"] == id_]
    return max(versions) if versions else 0


def select_next_topic() -> Topic:
    """Select next blog topic."""
    logger.info("Selecting next topic...")
    
    packages_data = load_json(API_DIR / "packages.json") or {}
    repos_data = load_json(API_DIR / "repositories.json") or {}
    papers_data = load_json(API_DIR / "papers.json") or load_json(API_DIR / "research.json") or {}
    tutorials_data = load_json(API_DIR / "tutorials.json") or load_json(API_DIR / "data.json") or {}
    
    coverage = load_coverage()
    
    packages = packages_data.get("packages") or packages_data.get("top_packages") or []
    repos = repos_data.get("repositories") or repos_data.get("top_repositories") or []
    papers = papers_data.get("papers") or papers_data.get("most_cited") or papers_data.get("research") or []
    
    if isinstance(tutorials_data, list):
        tutorials = tutorials_data
    else:
        tutorials = tutorials_data.get("tutorials") or tutorials_data.get("top_tutorials") or []
    
    logger.info(f"Data sources: {len(packages)} packages, {len(repos)} repos, {len(papers)} papers, {len(tutorials)} tutorials")
    
    def pick_uncovered(items: List[Dict], kind: str) -> Optional[Topic]:
        for item in items:
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
            else:
                id_ = item.get("id") or item.get("slug") or item.get("title", "unknown")
                title = item.get("title", id_)
                summary = item.get("excerpt") or item.get("description", f"Tutorial: {title}")
            
            if max_version_for(coverage, kind, id_) == 0:
                url = item.get("url") or item.get("link") or item.get("homepage")
                tags = (item.get("tags") or [])[:6] if isinstance(item.get("tags"), list) else []
                logger.info(f"Selected new {kind}: {title}")
                return Topic(kind, id_, title, url, summary, tags, 1)
        return None
    
    for kind, items in [("package", packages), ("repo", repos), ("paper", papers), ("tutorial", tutorials)]:
        topic = pick_uncovered(items, kind)
        if topic:
            return topic
    
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
    
    logger.warning("No topics found, using fallback")
    return Topic("package", "fallback", "AI Technologies Update", None, "Latest in AI/ML", ["ai"], 1)


def clean_and_normalize_body(body: str) -> str:
    """
    Clean meta-commentary and normalize formatting.
    
    Uses conservative patterns to avoid removing actual content.
    Falls back to original if cleaning removes too much.
    """
    logger.info("Cleaning and normalizing article body...")
    logger.debug(f"Original length: {len(body)} chars")
    
    original_body = body
    original_length = len(body)
    
    # Step 1: Remove meta-commentary at start of body only
    # Using very specific patterns that only match at the beginning
    meta_patterns = [
        # "I now can give a great answer." at start
        (r'^\s*I (now )?can (give|provide|write)( a)? (great |good )?answer\.?\s*\n+', ''),
        # "**Final Answer**" at start
        (r'^\s*\*\*Final Answer\*\*\s*\n+', ''),
        # "Here is the article:" at start
        (r'^\s*(Here is|Here\'s) (the |your )?(article|blog post|content).*?[:.]?\s*\n+', ''),
        # "I can help with that" at start
        (r'^\s*I (can |will )?help( you)?( with that)?\.?\s*\n+', ''),
        # "Let me write/create..." at start
        (r'^\s*Let me (write|create|generate).*?\.\s*\n+', ''),
        # "I understand you want..." at start
        (r'^\s*I (understand|see)( that)? you.*?\.\s*\n+', ''),
        # Remove outline-style prefix
        (r'^\s*###?\s*Enterprise-Focused Blog Outline:\s*["\'].*?["\']\s*\n+', ''),
    ]
    
    for pattern, replacement in meta_patterns:
        before = len(body)
        body = re.sub(pattern, replacement, body, flags=re.IGNORECASE)
        after = len(body)
        if before != after:
            logger.debug(f"Pattern matched, removed {before - after} chars")
    
    # Step 2: Normalize headings (convert bold+underline to proper markdown)
    lines = body.split('\n')
    result = []
    i = 0
    normalized_headings = 0
    
    while i < len(lines):
        line = lines[i]
        
        # Check for bold text with underlines
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            
            # Bold text with === or --- underline
            if (re.match(r'^[=\-]{3,}$', next_line) and 
                line.strip().startswith('**') and line.strip().endswith('**')):
                heading_text = line.strip().strip('*').strip()
                if heading_text:  # Only if there's actual text
                    result.append(f"## {heading_text}")
                    normalized_headings += 1
                    logger.debug(f"Normalized heading: {heading_text[:50]}")
                    i += 2
                    continue
        
        result.append(line)
        i += 1
    
    body = '\n'.join(result)
    logger.info(f"Normalized {normalized_headings} headings")
    
    # Step 3: Clean up excessive whitespace
    body = re.sub(r'\n{4,}', '\n\n\n', body)  # Max 3 newlines
    body = body.strip()
    
    # Step 4: Safety check - if we removed too much, use original
    final_length = len(body)
    removed = original_length - final_length
    removal_percent = (removed / original_length * 100) if original_length > 0 else 0
    
    logger.info(f"Cleaning complete: {removed} chars removed ({removal_percent:.1f}%)")
    logger.info(f"Final length: {final_length} chars, {len(body.split())} words")
    
    # If we removed more than 50% of content, something went wrong
    if removal_percent > 50:
        logger.warning(f"⚠️  Cleaning removed {removal_percent:.1f}% of content - using original")
        logger.warning(f"   This likely means the LLM output was mostly meta-commentary")
        return original_body
    
    # If final length is too short, use original
    if final_length < 500:
        logger.warning(f"⚠️  Cleaned body too short ({final_length} chars) - using original")
        return original_body
    
    return body


def get_current_date() -> datetime:
    """Get current date with validation."""
    now = datetime.now(timezone.utc)
    logger.info(f"Using date: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    return now


def build_blog_crew(topic: Topic) -> Tuple[Crew, Tuple[Task, Task, Task]]:
    """Build CrewAI pipeline with improved instructions."""
    
    strategist = Agent(
        role="AI Content Strategist",
        goal="Design enterprise-focused blog outlines with specific, actionable content",
        backstory=(
            "You create detailed, specific outlines that avoid generic business buzzwords. "
            "You focus on concrete examples, measurable benefits, and practical applications."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    writer = Agent(
        role="Senior Technical Writer",
        goal="Write clear, engaging blog posts that demonstrate immediate value",
        backstory=(
            "You are a professional technical writer who creates high-quality blog content. "
            "You write complete, detailed articles with proper structure and code examples. "
            "You write the article content directly - no meta-commentary, no preambles. "
            "You start immediately with the first section heading and write the full article."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    publisher = Agent(
        role="Jekyll Metadata Curator",
        goal="Generate SEO-optimized, accurate metadata",
        backstory="Ensures consistent, searchable blog metadata with compelling titles",
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
    
    t1 = Task(
        description=f"""Create a detailed blog outline for: {topic.title}

{topic_context}

Create sections:
1. Executive Summary - Brief overview with key benefits
2. What it is & Why it Matters - Concrete explanation
3. Technical Deep Dive - How it works
4. Example Implementation - 2+ Python code examples
5. Business Value & Use Cases - Specific industries and ROI
6. Limitations & Alternatives - Honest assessment
7. Getting Started - Actionable next steps

{f"Include: What's New in v{topic.version}" if topic.version > 1 else ""}

Target: 800-1200 words
Focus on specific, concrete information.""",
        expected_output="Detailed markdown outline with bullets for each section",
        agent=strategist,
    )
    
    t2 = Task(
        description=f"""Write a complete blog article about: {topic.title}

Topic: {topic.summary or 'n/a'}

IMPORTANT: Write the COMPLETE article following the outline.

STRUCTURE REQUIREMENTS:
- Start with: ## Executive Summary
- Use ## for main sections and ### for subsections
- Include 2+ Python code examples in ```python blocks
- Write 800-1200 words minimum
- End each section before starting the next

WRITING STYLE:
- Professional and informative
- Start with specific facts, not generic phrases
- Use concrete examples and numbers where possible
- Write as the published article, not about writing it

DO NOT INCLUDE:
- Any meta-commentary like "I will write" or "Here is the article"
- First-person references to the writing process
- Preambles or acknowledgments
- The word "outline" in headings

{f"Include a '## What's New in v{topic.version}' section" if topic.version > 1 else ""}

Write the complete article now, starting with ## Executive Summary.""",
        expected_output="Complete 800-1200 word markdown article with code examples",
        agent=writer,
        context=[t1],
    )
    
    t3 = Task(
        description="""Create metadata JSON for the article.

Return ONLY a JSON object (no other text):
{"title": "Article Title", "excerpt": "Brief description", "tags": ["tag1", "tag2"]}

Requirements:
- Title: Compelling, ≤80 characters
- Excerpt: Value proposition, ≤220 characters
- Tags: 4-8 lowercase tags (use hyphens for multi-word)

Return only the JSON object.""",
        expected_output="JSON object with title, excerpt, and tags",
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
        timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
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
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "filename": filename,
    })
    save_coverage(coverage)


def validate_body(body: str) -> None:
    """
    Validate article quality.
    
    Checks:
    - Minimum length
    - Has headings
    - Has code blocks
    """
    min_chars = 700  # Slightly lower to account for cleaning
    
    if len(body) < min_chars:
        logger.error(f"Body validation failed:")
        logger.error(f"  Length: {len(body)} chars (minimum: {min_chars})")
        logger.error(f"  Words: {len(body.split())}")
        logger.error(f"  First 200 chars: {body[:200]}")
        raise RuntimeError(
            f"Generated body too short: {len(body)} chars (min {min_chars}). "
            f"This usually means the LLM didn't generate a full article. "
            f"Check logs for the actual output."
        )
    
    if "## " not in body and "### " not in body:
        logger.warning("⚠️  No markdown headings found")
        # Don't fail - some LLMs might use different formatting
    
    if "```" not in body:
        logger.warning("⚠️  No code blocks found")
        # Don't fail - not all articles need code
    
    # Check for meta-commentary that survived cleaning
    meta_checks = [
        "I now can",
        "Final Answer",
        "Here is the article",
        "I can help",
    ]
    
    found_meta = []
    for phrase in meta_checks:
        if phrase.lower() in body.lower():
            found_meta.append(phrase)
    
    if found_meta:
        logger.warning(f"⚠️  Potential meta-commentary found: {', '.join(found_meta)}")
        logger.warning("   Article may need manual review")
    
    logger.info(f"✅ Validation passed: {len(body)} chars, {len(body.split())} words")


def main() -> None:
    """Main entry point."""
    logger.info("="*70)
    logger.info("Daily Best-of-the-Best Blog Generation (Production v2.1)")
    logger.info("="*70)
    logger.info(f"BASE_DIR: {BASE_DIR}")
    logger.info(f"BLOG_POSTS_DIR: {BLOG_POSTS_DIR}")
    logger.info(f"API_DIR: {API_DIR}")
    
    if not API_DIR.exists():
        logger.error(f"❌ API directory missing: {API_DIR}")
        logger.error(f"   Expected: {API_DIR}")
        logger.error(f"   Please ensure blog/api/ directory exists with data files")
        sys.exit(1)
    
    try:
        # Select topic
        topic = select_next_topic()
        logger.info(f"📝 Topic: {topic.kind} | {topic.title} (v{topic.version})")
        
        # Build and run crew
        crew, (t1, t2, t3) = build_blog_crew(topic)
        logger.info("🚀 Running CrewAI agents...")
        logger.info("   This may take 1-3 minutes...")
        
        result = crew.kickoff()
        
        if not result:
            raise RuntimeError("CrewAI returned no result")
        
        # Extract body
        body = (t2.output.raw if t2.output else "").strip()
        
        if not body:
            raise RuntimeError(
                "Writer agent produced empty output. "
                "This may indicate an LLM configuration issue."
            )
        
        logger.info(f"📄 Writer produced: {len(body)} chars, {len(body.split())} words")
        
        # Log first 200 chars for debugging
        logger.debug(f"Body preview: {body[:200]}")
        
        # Clean meta-commentary and normalize
        body = clean_and_normalize_body(body)
        
        # Validate
        validate_body(body)
        
        # Parse metadata
        meta_raw = (t3.output.raw if t3.output else "{}").strip()
        logger.debug(f"Metadata raw: {meta_raw[:200]}")
        
        try:
            json_start = meta_raw.find("{")
            json_end = meta_raw.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                meta = json.loads(meta_raw[json_start:json_end])
            else:
                meta = json.loads(meta_raw)
            logger.info(f"✅ Parsed metadata: title='{meta.get('title', 'N/A')[:50]}'")
        except Exception as e:
            logger.warning(f"⚠️  Metadata parse failed: {e}")
            meta = {
                "title": topic.title,
                "excerpt": topic.summary or f"Technical deep-dive into {topic.title}",
                "tags": topic.tags or ["ai", "machine-learning"]
            }
            logger.info(f"   Using fallback metadata")
        
        # Build and save post
        today = get_current_date()
        filename, content = build_jekyll_post(today, topic, body, meta)
        path = save_post(filename, content)
        record_coverage(topic, filename)
        
        # Success summary
        logger.info("="*70)
        logger.info("✅ BLOG POST GENERATED SUCCESSFULLY")
        logger.info(f"   File: {path}")
        logger.info(f"   Topic: {topic.kind} - {topic.title} (v{topic.version})")
        logger.info(f"   Title: {meta.get('title', topic.title)}")
        logger.info(f"   Date: {today.strftime('%Y-%m-%d')}")
        logger.info(f"   Words: ~{len(body.split())}")
        logger.info(f"   Size: {len(content)} bytes")
        logger.info("="*70)
        logger.info("")
        logger.info("📝 Next steps:")
        logger.info(f"   • Review: cat '{path}'")
        logger.info(f"   • Preview: cd {BASE_DIR} && jekyll serve")
        logger.info(f"   • Commit: git add blog/posts/ data/ && git commit -m 'Add blog post'")
        logger.info("")
        
    except Exception as e:
        logger.error("="*70)
        logger.error(f"❌ GENERATION FAILED: {e}")
        logger.error("="*70)
        logger.error("")
        logger.error("🔍 Troubleshooting:")
        logger.error("   1. Check if Ollama is running: ollama list")
        logger.error("   2. Check model availability: ollama pull llama3:8b")
        logger.error("   3. Review full logs: cat logs/blog_generation.log")
        logger.error("   4. Run diagnostics: python scripts/diagnose_blog_system.py")
        logger.error("")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()