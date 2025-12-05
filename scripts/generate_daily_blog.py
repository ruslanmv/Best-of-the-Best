#!/usr/bin/env python3
"""
scripts/generate_daily_blog.py

Daily blog generator for ruslanmv.com/Best-of-the-Best.

Key goals:
- Minimal context (only metadata needed for the topic).
- Fast, local Ollama llama3 in CI (via llm_client.py).
- Compatible with watsonx.ai / OpenAI / Anthropic (by changing NEWS_LLM_MODEL).
- Multi-agent but lightweight: Strategist -> Writer -> Publisher-metadata.

Output:
- blog/posts/YYYY-MM-DD-<slug>.md
- data/blog_coverage.json (log of what has been covered and which version)
"""

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add scripts directory to path to import llm_client
sys.path.insert(0, str(Path(__file__).resolve().parent))

from crewai import Agent, Task, Crew, Process
from llm_client import llm  # your multi-provider LLM


BASE_DIR = Path(__file__).resolve().parents[1]
BLOG_POSTS_DIR = BASE_DIR / "blog" / "posts"
API_DIR = BASE_DIR / "blog" / "api"
DATA_DIR = BASE_DIR / "data"
COVERAGE_FILE = DATA_DIR / "blog_coverage.json"


# ---------- Data structures & helpers ----------

@dataclass
class Topic:
    kind: str           # "package" | "repo" | "paper" | "tutorial"
    id: str             # unique ID (package name, repo full_name, DOI, etc.)
    title: str
    url: Optional[str]
    summary: Optional[str]
    tags: List[str]
    version: int        # 1 for first time, 2 for v2, etc.


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "topic"


def load_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_coverage() -> List[Dict]:
    if not COVERAGE_FILE.exists():
        return []
    with COVERAGE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_coverage(entries: List[Dict]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with COVERAGE_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def max_version_for(coverage: List[Dict], kind: str, id_: str) -> int:
    versions = [
        entry["version"]
        for entry in coverage
        if entry["kind"] == kind and entry["id"] == id_
    ]
    return max(versions) if versions else 0


# ---------- Topic selection (optimized) ----------

def select_next_topic() -> Topic:
    """
    Priority:
      1) Top packages not yet covered (v1).
      2) Top repos not yet covered.
      3) Most cited papers / research not yet covered.
      4) Tutorials not yet covered.
      5) If everything has v1, start v2+ cycles from packages (rotate by lowest version).

    Uses:
      - blog/api/packages.json
      - blog/api/repositories.json
      - blog/api/papers.json or blog/api/research.json
      - blog/api/tutorials.json
    """
    packages_data = load_json(API_DIR / "packages.json") or {}
    repos_data = load_json(API_DIR / "repositories.json") or {}
    papers_data = (
        load_json(API_DIR / "papers.json")
        or load_json(API_DIR / "research.json")
        or {}
    )
    tutorials_data = load_json(API_DIR / "tutorials.json") or []

    coverage = load_coverage()

    # Keep only what we need to keep context small
    packages = packages_data.get("packages") or []
    repos = repos_data.get("repositories") or []
    papers = papers_data.get("papers") or []

    # tutorials.json is already a list
    if isinstance(tutorials_data, list):
        tutorials = tutorials_data
    elif isinstance(tutorials_data, dict):
        tutorials = tutorials_data.get("tutorials") or []
    else:
        tutorials = []

    def pick_first_uncovered(items, kind: str) -> Optional[Topic]:
        for item in items:
            if kind == "package":
                id_ = item.get("name") or item.get("id") or item.get("slug", "unknown-package")
                title = item.get("name") or item.get("title") or id_
                summary = item.get("summary") or item.get("description") or f"Top Python package: {title}"
            elif kind == "repo":
                id_ = item.get("name") or item.get("full_name") or item.get("id", "unknown-repo")
                title = item.get("name") or item.get("full_name") or id_
                summary = item.get("description") or f"Popular GitHub repository: {title}"
            elif kind == "paper":
                id_ = item.get("name") or item.get("title") or item.get("doi") or item.get("id", "unknown-paper")
                title = item.get("name") or item.get("title") or id_
                summary = item.get("abstract") or item.get("summary") or f"Highly cited research: {title}"
            else:
                id_ = item.get("id") or item.get("slug") or item.get("title", "unknown-tutorial")
                title = item.get("title") or id_
                summary = item.get("excerpt") or item.get("description") or f"Tutorial: {title}"

            if max_version_for(coverage, kind, id_) == 0:
                url = item.get("url") or item.get("link") or item.get("homepage")
                tags_raw = item.get("tags") or []
                tags = tags_raw[:6] if isinstance(tags_raw, list) else []
                return Topic(kind=kind, id=id_, title=title, url=url, summary=summary, tags=tags, version=1)
        return None

    # Phase 1: any v0 item in priority order
    for kind, items in [
        ("package", packages),
        ("repo", repos),
        ("paper", papers),
        ("tutorial", tutorials),
    ]:
        topic = pick_first_uncovered(items, kind)
        if topic:
            return topic

    # Phase 2: everything has v1 → rotate v2, v3... on packages (fast)
    candidates: List[Tuple[int, Topic]] = []
    for item in packages:
        id_ = item.get("name") or item.get("id") or item.get("slug", "unknown-package")
        title = item.get("name") or item.get("title") or id_
        url = item.get("url") or item.get("link") or item.get("homepage")
        summary = item.get("summary") or item.get("description") or f"Top Python package: {title}"
        tags_raw = item.get("tags") or []
        tags = tags_raw[:6] if isinstance(tags_raw, list) else []
        current_v = max_version_for(coverage, "package", id_)
        next_v = current_v + 1
        candidates.append(
            (current_v, Topic(kind="package", id=id_, title=title, url=url, summary=summary, tags=tags, version=next_v))
        )

    if not candidates:
        # fallback if no data at all
        return Topic(
            kind="package",
            id="dummy-package",
            title="Daily AI Package",
            url=None,
            summary="Auto-generated blog content.",
            tags=["AI"],
            version=1,
        )

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


# ---------- CrewAI pipeline (3 lightweight agents) ----------

def build_blog_crew(topic: Topic):
    """
    Build a small, efficient Crew:
      - Strategist: decide angle + outline
      - Writer: body content
      - Publisher: metadata only (title, excerpt, tags)
    """

    # 1) Strategist
    strategist = Agent(
        role="AI Content Strategist",
        goal="Decide an enterprise-focused angle and outline for a short technical blog post.",
        backstory=(
            "You receive metadata about one AI/ML package, repo, paper or tutorial. "
            "You pick the most impactful angle for enterprise engineers and leaders."
        ),
        llm=llm,
        verbose=False,       # performance: no verbose logging
        allow_delegation=False,
    )

    # 2) Writer
    writer = Agent(
        role="Senior Technical Writer",
        goal="Write a concise but useful blog post that mixes technical detail and business value.",
        backstory=(
            "You write for busy professionals. You keep sections focused and include at least "
            "one code or pseudo-code example."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    # 3) Publisher-meta (no file IO here, just metadata)
    publisher = Agent(
        role="Jekyll Metadata Curator",
        goal="Produce compact metadata: title, excerpt, tags.",
        backstory=(
            "You ensure titles are clear, excerpts are SEO-friendly, and tags are consistent."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    # Minified context text
    topic_context = (
        f"Kind: {topic.kind}\n"
        f"ID: {topic.id}\n"
        f"Title: {topic.title}\n"
        f"URL: {topic.url or 'n/a'}\n"
        f"Summary: {topic.summary or 'n/a'}\n"
        f"Tags: {', '.join(topic.tags) if topic.tags else 'n/a'}\n"
        f"Version: v{topic.version}\n"
    )

    # --- Task 1: Outline ---
    t1 = Task(
        description=(
            "You are given a single topic from a Best-of-the-Best AI dashboard.\n\n"
            f"{topic_context}\n\n"
            "Goal: design a short but valuable blog outline for enterprise readers.\n"
            "Constraints:\n"
            "- Total final article length: roughly 800–1200 words.\n"
            "- Sections:\n"
            "  1. Executive Summary\n"
            "  2. What it is & why it matters\n"
            "  3. Technical Deep Dive (architecture / usage)\n"
            "  4. Example Implementation (Python or pseudo-code)\n"
            "  5. Business ROI / Use Cases\n"
            "  6. Limitations & Alternatives\n"
            "  7. Conclusion / Next Steps\n"
            f"- If this is version v{topic.version} and v>1, include a bullet list of 'What's new in v{topic.version}'.\n"
        ),
        expected_output="A concise markdown outline with headings and bullets for each section.",
        agent=strategist,
    )

    # --- Task 2: Body ---
    t2 = Task(
        description=(
            "Write the full markdown body from the outline.\n"
            "Rules:\n"
            "- 800–1200 words max.\n"
            "- Use clear H2/H3 headings, short paragraphs, and bullets.\n"
            "- Include at least one Python code block or pseudo-code example.\n"
            f"- If this is version v{topic.version} and v>1, include a 'What's New' section.\n"
            "- Do NOT include any YAML front matter.\n"
            "- Do NOT include title at the very top; start directly with content.\n"
        ),
        expected_output="A complete markdown article body (no front matter).",
        agent=writer,
        context=[t1],
    )

    # --- Task 3: Metadata ---
    t3 = Task(
        description=(
            "You will receive the final markdown body and the topic metadata.\n"
            "Your job is ONLY to propose metadata.\n\n"
            "Return a single JSON object:\n"
            '{\"title\": \"...\", \"excerpt\": \"...\", \"tags\": [\"tag1\", \"tag2\", ...]}\n\n'
            "Constraints:\n"
            "- Title: <= 80 characters, no quotes inside.\n"
            "- Excerpt: 1–2 sentences, <= 220 characters.\n"
            "- Tags: 4–8 short tags, all lowercase, no spaces (use hyphens).\n"
            "Answer with JSON only. No other text."
        ),
        expected_output="A small JSON object for title, excerpt, and tags.",
        agent=publisher,
        context=[t2],
    )

    crew = Crew(
        agents=[strategist, writer, publisher],
        tasks=[t1, t2, t3],
        process=Process.sequential,
        verbose=False,   # important: stop verbose logs for speed
    )

    return crew, (t1, t2, t3)


# ---------- Jekyll template & saving ----------

def build_jekyll_post(filename_date: datetime, topic: Topic, body_markdown: str, meta: Dict) -> Tuple[str, str]:
    title = meta.get("title") or topic.title
    excerpt = meta.get("excerpt") or (topic.summary or "")
    tags = meta.get("tags") or topic.tags or ["ai"]
    tags = tags[:8]  # cap tags

    tag_lines = "\n  - " + "\n  - ".join(tags) if tags else "\n  - ai"
    date_iso = filename_date.strftime("%Y-%m-%dT09:00:00-00:00")
    date_prefix = filename_date.strftime("%Y-%m-%d")

    version_suffix = f"-v{topic.version}" if topic.version > 1 else ""
    slug = f"{topic.kind}-{slugify(topic.title)}{version_suffix}"
    filename = f"{date_prefix}-{slug}.md"

    front_matter = f"""---
title: "{title}"
date: {date_iso}
last_modified_at: {date_iso}
categories:
  - Engineering
  - AI
tags:{tag_lines}
excerpt: "{excerpt.replace('"', "'")}"
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

"""

    footer = """

---

<small>Powered by Jekyll & Minimal Mistakes.</small>
"""

    full_content = front_matter + body_markdown.strip() + footer
    return filename, full_content


def save_post(filename: str, content: str) -> Path:
    BLOG_POSTS_DIR.mkdir(parents=True, exist_ok=True)
    path = BLOG_POSTS_DIR / filename
    with path.open("w", encoding="utf-8") as f:
        f.write(content)
    return path


def record_coverage(topic: Topic, filename: str) -> None:
    coverage = load_coverage()
    coverage.append(
        {
            "kind": topic.kind,
            "id": topic.id,
            "version": topic.version,
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "filename": filename,
        }
    )
    save_coverage(coverage)


# ---------- Main ----------

def main():
    print("=== Daily Best-of-the-Best Blog Generation (Ollama-optimized) ===")

    topic = select_next_topic()
    print(f"✅ Selected topic: {topic.kind} | {topic.title} (v{topic.version})")

    crew, (t1, t2, t3) = build_blog_crew(topic)
    print(f"🚀 Starting CrewAI pipeline with 3 agents...")

    result = crew.kickoff()
    if not result:
        raise RuntimeError("CrewAI returned no result.")

    outline = t1.output.raw if t1.output else ""
    body = t2.output.raw if t2.output else ""
    meta_raw = t3.output.raw if t3.output else "{}"

    print(f"📝 Parsing metadata...")
    try:
        # Try to extract JSON from the metadata response
        # Sometimes LLMs add extra text, so we need to find the JSON part
        meta_text = meta_raw.strip()

        # Find JSON object in the response
        json_start = meta_text.find('{')
        json_end = meta_text.rfind('}') + 1

        if json_start >= 0 and json_end > json_start:
            meta_json = meta_text[json_start:json_end]
            meta = json.loads(meta_json)
        else:
            meta = json.loads(meta_text)
    except Exception as e:
        print(f"⚠️  Warning: Could not parse metadata JSON: {e}")
        print(f"   Raw metadata: {meta_raw}")
        meta = {}

    # Safety: short body
    body = body.strip()
    if not body:
        raise RuntimeError("Writer produced empty body.")

    today = datetime.utcnow()
    filename, content = build_jekyll_post(today, topic, body, meta)
    path = save_post(filename, content)
    record_coverage(topic, filename)

    print(f"✅ Blog post generated: {path}")
    print(f"   Topic: {topic.kind} {topic.id} v{topic.version}")
    print(f"   Filename: {filename}")


if __name__ == "__main__":
    main()
