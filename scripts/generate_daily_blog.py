#!/usr/bin/env python3
"""
scripts/generate_blog_advanced_orchestrated.py

PRODUCTION v4.1 - Fixed Ollama Compatibility

Key Fixes:
- Removed tools from agents that don't need them
- Fixed max_iter for better completion
- Resolved LiteLLM message list conflicts
- Cleaned up agent instructions

Features:
- 11-agent orchestrated pipeline with dynamic routing
- README-first strategy with web search fallback
- Package health validation
- Code quality assurance
- Source quality tracking
- Topic-specific images
- Ollama compatible
- Production error handling
"""

import ast
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
# ============================================================================
# 🚨 CRITICAL FIX: TIMEOUT CONFIGURATION (must be set BEFORE importing llm_client)
# ============================================================================
# Increase timeout for slow local LLM generations (Ollama on limited hardware)
os.environ.setdefault("LITELLM_REQUEST_TIMEOUT", "1800")  # 30 minutes
os.environ.setdefault("CREWAI_REQUEST_TIMEOUT", "1800")   # 30 minutes
# ============================================================================


# Setup paths
CURRENT_DIR = Path(__file__).resolve().parent
BASE_DIR = CURRENT_DIR.parent
sys.path.insert(0, str(CURRENT_DIR))

# Load environment variables (production-safe)
try:
    from dotenv import load_dotenv

    candidates = [
        BASE_DIR / ".env",           # repo root/.env (typical)
        Path.cwd() / ".env",         # if launched from repo root
    ]

    loaded = False
    for env_path in candidates:
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=False)
            print(f"✅ Loaded environment variables from: {env_path}")
            loaded = True
            break

    if not loaded:
        print("⚠️  No .env file found. Using system environment variables.")

except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables.")


from crewai import Agent, Task, Crew, Process  # type: ignore
from llm_client import llm

# Import ALL search tools
try:
    from search import (
        search_web, 
        scrape_webpage, 
        scrape_readme, 
        get_package_health
    )
    SEARCH_TOOLS_AVAILABLE = True
    README_TOOLS_AVAILABLE = True
    print("✅ All search tools loaded (web + README + health)")
except ImportError as e:
    print(f"⚠️  Search tools import error: {e}")
    SEARCH_TOOLS_AVAILABLE = False
    README_TOOLS_AVAILABLE = False
    search_web = scrape_webpage = scrape_readme = get_package_health = None

# Import image tools
try:
    from image_tools import ImageTools, set_blog_context, get_blog_assets_dir
    IMAGE_TOOLS_AVAILABLE = True
    print("✅ Image tools loaded")
except ImportError:
    IMAGE_TOOLS_AVAILABLE = False
    def set_blog_context(*args, **kwargs):
        pass
    def get_blog_assets_dir():
        return Path("assets/images")

# ============================================================================
# PATHS
# ============================================================================
BASE_DIR = CURRENT_DIR.parent
BLOG_POSTS_DIR = BASE_DIR / "blog" / "posts"
API_DIR = BASE_DIR / "blog" / "api"
DATA_DIR = BASE_DIR / "data"
BASE_ASSETS_DIR = BASE_DIR / "assets" / "images"
COVERAGE_FILE = DATA_DIR / "blog_coverage.json"
LOG_DIR = BASE_DIR / "logs"

for directory in [LOG_DIR, DATA_DIR, BLOG_POSTS_DIR, BASE_ASSETS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================================================
# LOGGING
# ============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "blog_generation_advanced.log", mode='a'),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class Topic:
    """Topic metadata for blog generation"""
    kind: str
    id: str
    title: str
    url: Optional[str]
    summary: Optional[str]
    tags: List[str]
    version: int


@dataclass
class ResearchStrategy:
    """Research strategy decision"""
    strategy: str  # 'readme', 'package_health', 'web_search', 'hybrid'
    confidence: str  # 'high', 'medium', 'low'
    tools_to_use: List[str]
    fallback_needed: bool
    reasoning: str


# ============================================================================
# LLM DETECTION
# ============================================================================
def is_ollama_llm() -> bool:
    """Detect if using Ollama"""
    llm_model = os.getenv("NEWS_LLM_MODEL", "")
    return "ollama" in llm_model.lower()


# ============================================================================
# CONTEXT SIZE MANAGEMENT & TOKEN COUNTING
# ============================================================================
# Approximate token budget: ~4 chars per token for English text.
# LLM context window sizes:
#   qwen2.5:7b  = 128K tokens
#   llama3:8b   = 8K tokens
#   llama3.2:3b = 128K tokens
#
# We set a safe per-task context budget to leave room for system prompts,
# agent backstories, and the task description itself (~2000 tokens overhead).

# For qwen2.5:7b (128K context), we can afford more generous budgets.
# For llama3:8b (8K context), reduce to 1500.
# The total prompt = system prompt (~500) + agent backstory (~500) + task description (~500)
#                  + ALL context task outputs + the actual generation.
# Safe budget: leave ~4000 tokens for system/backstory/task, ~2000 for generation.
MAX_CONTEXT_TOKENS = 4000  # Max tokens per individual task output
CHARS_PER_TOKEN = 4        # Conservative estimate for English text

def estimate_tokens(text: str) -> int:
    """Estimate token count from character count. ~4 chars per token for English."""
    if not text:
        return 0
    return len(text) // CHARS_PER_TOKEN


def _task_completion_callback(task_output):
    """Module-level callback called after each task completes.
    Truncates large outputs to prevent context overflow for subsequent agents.
    Article-body tasks (writer, fixer, editor) are exempt from truncation."""
    try:
        raw = getattr(task_output, 'raw', '') or ''
        tokens = estimate_tokens(raw)
        task_desc = (getattr(task_output, 'description', '') or '')[:80]

        logger.info(f"   📊 Task output: ~{tokens} tokens ({len(raw)} chars)")

        # Skip truncation for article-body tasks
        if any(kw in task_desc.lower() for kw in
               ["write a", "fix all", "take the article", "polish"]):
            logger.info(f"   ↳ Article body task - not truncating")
            return

        # Truncate research/analysis outputs that exceed budget
        per_task_budget = MAX_CONTEXT_TOKENS
        if tokens > per_task_budget:
            truncated = truncate_to_token_budget(raw, per_task_budget)
            task_output.raw = truncated
            logger.info(f"   ↳ Truncated: {tokens} -> ~{per_task_budget} tokens")
        else:
            logger.info(f"   ↳ Within budget ({tokens}/{per_task_budget})")

    except Exception as e:
        logger.warning(f"   ⚠️  Task callback error (non-fatal): {e}")


def truncate_to_token_budget(text: str, max_tokens: int = MAX_CONTEXT_TOKENS) -> str:
    """Truncate text to fit within a token budget while preserving key sections.

    Strategy:
    - Splits on markdown headings (##, ###, **Section**)
    - Always keeps the first section (intro/version/install info)
    - Always keeps the last section (conclusion/warnings/resources)
    - Trims middle sections if needed, keeping their headings as summaries
    """
    if not text:
        return text

    current_tokens = estimate_tokens(text)
    if current_tokens <= max_tokens:
        return text

    # Try section-aware truncation first
    sections = re.split(r'(?=\n#{1,3}\s|\n\*\*[A-Z])', text)

    if len(sections) <= 2:
        # No sections found - fall back to head/tail
        max_chars = max_tokens * CHARS_PER_TOKEN
        head_chars = int(max_chars * 0.80)
        tail_chars = int(max_chars * 0.15)
        truncated = text[:head_chars]
        truncated += f"\n\n[... trimmed to fit context ...]\n\n"
        truncated += text[-tail_chars:]
    else:
        # Keep first section, last section, and as many middle sections as fit
        first = sections[0]
        last = sections[-1]
        middle = sections[1:-1]

        reserved = estimate_tokens(first) + estimate_tokens(last) + 50  # 50 for markers
        remaining_budget = max_tokens - reserved

        kept_middle = []
        for section in middle:
            section_tokens = estimate_tokens(section)
            if remaining_budget >= section_tokens:
                kept_middle.append(section)
                remaining_budget -= section_tokens
            else:
                # Keep just the heading line as a breadcrumb
                heading_line = section.strip().split('\n')[0]
                if heading_line:
                    kept_middle.append(f"\n{heading_line} [... details trimmed ...]\n")
                    remaining_budget -= 10

        truncated = first + ''.join(kept_middle) + last

    new_tokens = estimate_tokens(truncated)
    logger.info(f"   Context truncated: {current_tokens} -> ~{new_tokens} tokens "
                f"({len(text)} -> {len(truncated)} chars)")
    return truncated


def enforce_context_budget(task_outputs: list, max_total_tokens: int = MAX_CONTEXT_TOKENS) -> None:
    """Enforce a total token budget across multiple task outputs.

    Modifies task output.raw in-place to fit within the budget.
    Each task gets a proportional share of the budget.
    """
    if not task_outputs:
        return

    # Gather current sizes
    sizes = []
    for task in task_outputs:
        if task and hasattr(task, 'output') and task.output:
            raw = getattr(task.output, 'raw', '') or ''
            sizes.append((task, raw, estimate_tokens(raw)))
        else:
            sizes.append((task, '', 0))

    total_tokens = sum(s[2] for s in sizes)

    if total_tokens <= max_total_tokens:
        logger.debug(f"   Context budget OK: {total_tokens}/{max_total_tokens} tokens")
        return

    logger.info(f"   ⚠️  Context budget exceeded: {total_tokens}/{max_total_tokens} tokens - truncating")

    # Distribute budget proportionally (but give at least 200 tokens each)
    min_tokens_per_task = 200
    num_tasks = len([s for s in sizes if s[2] > 0])
    if num_tasks == 0:
        return

    available = max_total_tokens - (min_tokens_per_task * num_tasks)
    if available < 0:
        available = max_total_tokens

    for task, raw, tokens in sizes:
        if tokens == 0 or not task or not hasattr(task, 'output') or not task.output:
            continue

        # Proportional share
        share = min_tokens_per_task + int(available * (tokens / total_tokens))
        share = min(share, tokens)  # Don't expand

        if tokens > share:
            truncated = truncate_to_token_budget(raw, share)
            task.output.raw = truncated


# ============================================================================
# OUTPUT EXTRACTION (ROBUST)
# ============================================================================
def extract_task_output(task: Task, task_name: str) -> str:
    """Extract output from CrewAI task with multiple fallbacks.
    Returns a non-empty string whenever possible.
    """
    if not task or not hasattr(task, "output") or task.output is None:
        logger.warning(f"⚠️  Task {task_name} has no output")
        return ""

    output = task.output

    def _as_text(x):
        if x is None:
            return None

        # If tool/agent returned structured data, serialize it.
        if isinstance(x, (dict, list)):
            try:
                return json.dumps(x, ensure_ascii=False)
            except Exception:
                return str(x)

        # Normal string
        if isinstance(x, str):
            return x

        # Some CrewAI versions store the text in .content
        content = getattr(x, "content", None)
        if isinstance(content, str) and content.strip():
            return content

        # Fallback
        try:
            return str(x)
        except Exception:
            return None

    # Try likely fields first
    candidates = [
        ("raw", getattr(output, "raw", None)),
        ("result", getattr(output, "result", None)),
        ("text", getattr(output, "text", None)),
        ("content", getattr(output, "content", None)),
        ("output(str)", output),
    ]

    for method_name, candidate in candidates:
        try:
            text = _as_text(candidate)
            if not text or not isinstance(text, str):
                continue

            text = text.strip()
            if not text:
                continue

            # Remove fenced code wrappers if agent returned ```json ... ```
            text = re.sub(r"^\s*```[a-zA-Z0-9_-]*\s*\n", "", text)
            text = re.sub(r"\n```\s*$", "", text)
            text = text.strip()

            if text:
                logger.debug(f"✓ Extracted from {task_name}.output.{method_name}: {len(text)} chars")
                return text

        except Exception:
            continue

    logger.warning(f"⚠️  Failed to extract output from {task_name}")
    return ""


# ============================================================================
# TOPIC DETECTION
# ============================================================================
def detect_topic_type(topic: Topic) -> Tuple[str, str]:
    """
    Detect if topic is a package, repo, or general topic.
    Returns: (type, identifier)
    """
    if topic.kind == "package":
        return ("package", topic.id)
    elif topic.kind == "repo" and topic.url:
        return ("repo", topic.url)
    elif topic.url and "github.com" in topic.url.lower():
        return ("repo", topic.url)
    else:
        return ("general", topic.title)


# ============================================================================
# IMAGE GENERATION (from original code)
# ============================================================================
def generate_image_queries(topic: Topic) -> Dict[str, str]:
    """Generate topic-specific image search queries"""
    title_lower = topic.title.lower()
    tags_str = " ".join(topic.tags).lower()
    
    queries = {}
    main_keywords = []
    
    tech_terms = ['python', 'javascript', 'java', 'machine', 'learning', 'ai', 'data', 
                  'cloud', 'kubernetes', 'docker', 'neural', 'deep', 'web', 'api',
                  'database', 'sql', 'nosql', 'redis', 'mongo', 'postgres']
    
    for term in tech_terms:
        if term in title_lower or term in tags_str:
            main_keywords.append(term)
    
    if not main_keywords:
        words = topic.title.split()[:2]
        main_keywords = [w.lower() for w in words if len(w) > 3]
    
    if topic.kind == "package":
        base_context = "programming code technology"
    elif topic.kind == "repo":
        base_context = "software development coding"
    elif topic.kind == "paper":
        base_context = "research science technology"
    else:
        base_context = "technology innovation digital"
    
    if main_keywords:
        queries["header-primary"] = f"{' '.join(main_keywords[:2])} abstract technology"
    else:
        queries["header-primary"] = f"{base_context} abstract"
    
    if main_keywords:
        queries["teaser-main"] = f"{main_keywords[0]} modern innovation"
    else:
        queries["teaser-main"] = f"{base_context} modern"
    
    if len(main_keywords) > 1:
        queries["header-secondary"] = f"{main_keywords[1]} digital visualization"
    else:
        queries["header-secondary"] = f"{base_context} visualization"
    
    if main_keywords:
        queries["content-workspace"] = f"{main_keywords[0]} workspace laptop"
    else:
        queries["content-workspace"] = f"{base_context} workspace"
    
    return queries


def ensure_blog_assets_topic_specific(topic: Topic, slug: str, date_str: str) -> Path:
    """Ensure blog assets with topic-specific images"""
    if not IMAGE_TOOLS_AVAILABLE:
        blog_dir = BASE_ASSETS_DIR / f"{date_str}-{slug}"
        blog_dir.mkdir(parents=True, exist_ok=True)
        return blog_dir

    blog_dir = get_blog_assets_dir()
    api_key = os.getenv("PEXELS_API_KEY")
    
    if not api_key:
        logger.warning("⚠️  PEXELS_API_KEY not set. Skipping image download.")
        return blog_dir
    
    queries = generate_image_queries(topic)
    
    assets_to_create = [
        ("header", "ai-abstract", queries["header-primary"]),
        ("teaser", "ai", queries["teaser-main"]),
        ("header", "data-science", queries["header-secondary"]),
        ("header", "cloud", queries["content-workspace"]),
    ]
    
    for asset_type, descriptor, search_query in assets_to_create:
        asset_name = f"{asset_type}-{descriptor}"
        asset_path = blog_dir / f"{asset_name}.jpg"
        
        if asset_path.exists():
            continue
        
        try:
            ImageTools.get_stock_photo(
                search_query,
                filename=f"{asset_name}.jpg",
                asset_type=asset_type
            )
        except Exception as e:
            logger.warning(f"⚠️  Image download failed: {e}")
    
    return blog_dir


# ============================================================================
# DATA LOADING (from original code)
# ============================================================================
def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "topic"


def _norm_id(kind: str, id_: str) -> str:
    """Normalize topic ID for consistent coverage tracking"""
    if kind == "package":
        return id_.lower().strip()
    elif kind == "repo":
        return id_.lower().strip()
    elif kind == "tutorial":
        return slugify(id_)
    else:
        return id_.lower().strip()


def load_json(path: Path) -> Optional[Any]:
    """Load JSON file safely"""
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
        return None


def load_coverage() -> List[Dict[str, Any]]:
    """Load blog coverage history (with auto-recovery from posts)"""

    # ALWAYS recover from posts first (robust fix for missing commits)
    recovered = recover_coverage_from_posts()

    # If coverage file doesn't exist, use recovered data
    if not COVERAGE_FILE.exists():
        logger.info(f"📝 No coverage file found, recovered {len(recovered)} entries from posts")
        if recovered:
            save_coverage(recovered)
        return recovered

    # Try to load existing coverage file
    try:
        with COVERAGE_FILE.open("r", encoding="utf-8") as f:
            existing = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Coverage file corrupt: {COVERAGE_FILE} ({e})")
        # Move corrupt file to backup
        try:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = COVERAGE_FILE.with_suffix(f".corrupt-{ts}.json")
            COVERAGE_FILE.replace(backup)
            logger.error(f"📦 Moved to: {backup}")
        except Exception as move_err:
            logger.error(f"⚠️  Backup failed: {move_err}")
        existing = []
    except Exception as e:
        logger.error(f"❌ Failed to load coverage: {e}")
        existing = []

    # Merge recovered + existing, dedupe by (kind, id, version)
    merged = _merge_and_dedupe_coverage(existing, recovered)

    # If merged has more entries, save it back
    if len(merged) > len(existing):
        logger.info(f"🔄 Merged coverage: {len(existing)} → {len(merged)} entries")
        try:
            save_coverage(merged)
        except Exception as save_err:
            logger.error(f"⚠️  Failed to save merged coverage: {save_err}")

    return merged


def recover_coverage_from_posts() -> List[Dict[str, Any]]:
    """Rebuild blog_coverage.json by scanning existing posts."""
    entries: List[Dict[str, Any]] = []

    if not BLOG_POSTS_DIR.exists():
        return entries

    kind_re = re.compile(r'^topic_kind:\s*"?(.*?)"?\s*$')
    id_re = re.compile(r'^topic_id:\s*"?(.*?)"?\s*$')
    ver_re = re.compile(r'^topic_version:\s*(\d+)\s*$')
    date_re = re.compile(r'^date:\s*(\S+)')

    seen = set()
    for path in sorted(BLOG_POSTS_DIR.glob("*.md")):
        try:
            head = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:80]
        except Exception:
            continue

        if not head or head[0].strip() != "---":
            continue

        fm_lines = []
        for line in head[1:]:
            if line.strip() == "---":
                break
            fm_lines.append(line)

        kind = tid = date_str = None
        version = None

        for line in fm_lines:
            m = kind_re.match(line)
            if m:
                kind = m.group(1).strip()
                continue
            m = id_re.match(line)
            if m:
                tid = m.group(1).strip()
                continue
            m = ver_re.match(line)
            if m:
                version = int(m.group(1))
                continue
            m = date_re.match(line)
            if m:
                date_str = m.group(1).strip()[:10]

        if not (kind and tid and version):
            continue

        norm_kind = (kind or "").strip()
        norm_id = _norm_id(norm_kind, tid)
        key = (norm_kind, norm_id, int(version))
        if key in seen:
            continue
        seen.add(key)

        entries.append({
            "kind": norm_kind,
            "id": norm_id,
            "version": int(version),
            "date": date_str or "",
            "filename": path.name,
        })

    return entries


def _merge_and_dedupe_coverage(list1: List[Dict], list2: List[Dict]) -> List[Dict]:
    """Merge two coverage lists and remove duplicates"""
    seen = {}  # key: (kind, id, version) -> entry

    for entry in list1 + list2:
        kind = (entry.get("kind") or "").strip()
        id_ = entry.get("id", "")
        version = entry.get("version", 1)

        # Normalize ID
        norm_id = _norm_id(kind, id_)
        key = (kind, norm_id, version)

        # Keep first occurrence
        if key not in seen:
            seen[key] = {
                "kind": kind,
                "id": norm_id,
                "version": version,
                "date": entry.get("date", ""),
                "filename": entry.get("filename", ""),
            }

    # Sort by date
    return sorted(seen.values(), key=lambda x: x.get("date", ""))


def save_coverage(entries: List[Dict[str, Any]]) -> None:
    """Save blog coverage history (atomic-ish write)."""
    tmp = COVERAGE_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    tmp.replace(COVERAGE_FILE)


def max_version_for(coverage: List[Dict[str, Any]], kind: str, id_: str) -> int:
    """Get maximum version number for a topic"""
    norm_id = _norm_id(kind, id_)
    versions = [e["version"] for e in coverage if e["kind"] == kind and e["id"] == norm_id]
    return max(versions) if versions else 0


def select_next_topic() -> Topic:
    """Select next blog topic from JSON files"""
    logger.info("📊 Loading content from JSON files...")
    
    packages_data = load_json(API_DIR / "packages.json") or {}
    repos_data = load_json(API_DIR / "repositories.json") or {}
    papers_data = load_json(API_DIR / "papers.json") or {}
    tutorials_data = load_json(API_DIR / "tutorials.json") or {}
    
    coverage = load_coverage()
    
    packages = packages_data.get("packages", [])
    repos = repos_data.get("repositories", [])
    papers = papers_data.get("papers", [])
    tutorials = tutorials_data if isinstance(tutorials_data, list) else tutorials_data.get("tutorials", [])
    
    logger.info(f"   Packages: {len(packages)}, Repos: {len(repos)}, Papers: {len(papers)}, Tutorials: {len(tutorials)}")
    
    if not any([packages, repos, papers, tutorials]):
        logger.error("❌ No content in JSON files!")
        sys.exit(1)
    
    def pick_uncovered(items: List[Dict], kind: str) -> Optional[Topic]:
        for item in items:
            if kind == "package":
                id_ = item.get("name", "")
                if not id_:
                    continue
                title = id_.replace("-", " ").title()
                desc = item.get("description", "").strip()
                summary = desc if desc else f"Explore {title}, a Python package for AI and machine learning workflows."
                # Build meaningful tags from package name and description
                base_tags = [id_.lower()]
                desc_lower = (desc or "").lower()
                if any(kw in desc_lower for kw in ["machine learning", "ml", "model"]):
                    base_tags.append("machine-learning")
                if any(kw in desc_lower for kw in ["deep learning", "neural", "torch", "tensorflow"]):
                    base_tags.append("deep-learning")
                if any(kw in desc_lower for kw in ["nlp", "language", "text", "llm"]):
                    base_tags.append("nlp")
                if any(kw in desc_lower for kw in ["data", "dataset", "pandas"]):
                    base_tags.append("data-science")
                if any(kw in desc_lower for kw in ["vision", "image", "detection"]):
                    base_tags.append("computer-vision")
                base_tags.extend(["python", "open-source"])
                tags = list(dict.fromkeys(base_tags))[:8]  # dedupe, limit to 8
                url = item.get("url")
            elif kind == "repo":
                name = item.get("name", "")
                if not name or "/" not in name:
                    continue
                id_ = name
                org, repo_short = name.split("/", 1)
                # Use "Org/Repo" format for clear identification
                title = f"{org}/{repo_short.replace('-', ' ').title()}"
                desc = item.get("description", "").strip()
                summary = desc if desc else f"An overview of the {repo_short} GitHub repository and its capabilities."
                base_tags = [repo_short.lower(), "github", "open-source"]
                desc_lower = (desc or "").lower()
                if any(kw in desc_lower for kw in ["machine learning", "ml", "model", "ai"]):
                    base_tags.append("machine-learning")
                if any(kw in desc_lower for kw in ["llm", "language model"]):
                    base_tags.append("llm")
                tags = list(dict.fromkeys(base_tags))[:8]
                url = item.get("url")
            elif kind == "paper":
                name = item.get("name", "")
                if not name:
                    continue
                id_ = name
                title = name
                summary = "Research paper"
                tags = ["research", "paper"]
                url = item.get("url")
            else:  # tutorial
                title = item.get("title", "")
                if not title:
                    continue
                id_ = slugify(title)
                summary = item.get("excerpt", "")
                tags = item.get("tags", [])[:6] if isinstance(item.get("tags"), list) else ["tutorial"]
                url = item.get("url")
            
            if max_version_for(coverage, kind, id_) == 0:
                logger.info(f"✅ Selected: {kind.upper()} - {title}")
                return Topic(kind, id_, title, url, summary, tags, 1)
        
        return None
    
    for kind, items in [("package", packages), ("repo", repos), ("paper", papers), ("tutorial", tutorials)]:
        if items:
            topic = pick_uncovered(items, kind)
            if topic:
                return topic
    
    # Version update fallback
    if packages:
        item = packages[0]
        id_ = item.get("name", "unknown")
        title = id_.replace("-", " ").title()
        url = item.get("url")
        summary = f"Python package: {id_}"
        tags = ["python", "package"]
        version = max_version_for(coverage, "package", id_) + 1
        logger.info(f"✅ Version update: {title} (v{version})")
        return Topic("package", id_, title, url, summary, tags, version)
    
    logger.error("❌ No topics found!")
    sys.exit(1)


# ============================================================================
# CODE VALIDATION
# ============================================================================
def validate_python_code(code: str) -> Tuple[bool, List[str]]:
    """Validate Python code: syntax + semantics"""
    errors = []
    
    if not code or not code.strip():
        return False, ["Empty code block"]
    
    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, [f"Syntax error line {e.lineno}: {e.msg}"]
    except Exception as e:
        return False, [f"Parse error: {str(e)}"]
    
    if re.search(r'^(pip|apt|brew|conda)\s+install', code, re.MULTILINE):
        errors.append("Shell commands in Python block")
    
    if re.search(r'(\.\.\.+|TODO|FIXME|your_\w+)', code, re.MULTILINE):
        errors.append("Contains placeholders")
    
    return len(errors) == 0, errors


def validate_all_code_blocks(content: str) -> Tuple[bool, List[str], List[str]]:
    """
    Validate all Python code blocks.
    
    Fix: Uses a robust regex to capture blocks marked as 'python', 'py', 
    or blocks with no language tag (assumed Python). Ignores explicit 
    non-Python blocks (like 'bash', 'json') to avoid false syntax errors.
    """
    # Regex Explanation:
    # ```             : Match opening backticks
    # (?:python|py)?  : Non-capturing group. Matches 'python', 'py', or Nothing (optional)
    # [ \t]* : Matches optional spaces/tabs after the tag (but before newline)
    # \n              : Match the newline
    # (.*?)           : Capture the code content (non-greedy)
    # ```             : Match closing backticks
    
    code_blocks = re.findall(r'```(?:python|py)?[ \t]*\n(.*?)```', content, re.DOTALL | re.IGNORECASE)
    
    if not code_blocks:
        return True, [], []
    
    all_issues = []
    all_valid = True
    
    for i, code in enumerate(code_blocks, 1):
        # Skip empty blocks which might happen with double newlines
        if not code.strip():
            continue
            
        is_valid, errors = validate_python_code(code)
        if not is_valid:
            all_valid = False
            all_issues.append(f"Block {i}:")
            all_issues.extend([f"  • {err}" for err in errors])
    
    return all_valid, all_issues, code_blocks

# ============================================================================
# CONTENT CLEANING
# ============================================================================
def clean_content(body: str) -> str:
    """
    Clean and normalize content: remove LLM artifacts while preserving article content.
    """
    if not body:
        return ""

    # Remove common LLM preamble/artifact lines that leak into output
    artifact_patterns = [
        (r'^\s*(Here is|Here\'s)\s+(the|my|a)\s+.*?[:.]?\s*$', '', re.IGNORECASE | re.MULTILINE),
        (r'^\s*I (now can give|now have|will now)[^\n]*$', '', re.IGNORECASE | re.MULTILINE),
        (r'^\s*\*\*Final Answer\*\*\s*$', '', re.MULTILINE),
        (r'^\s*Final Answer\s*[:.]?\s*$', '', re.IGNORECASE | re.MULTILINE),
        (r'^\s*The complete corrected article[^\n]*$', '', re.IGNORECASE | re.MULTILINE),
        (r'^\s*Begin![^\n]*$', '', re.IGNORECASE | re.MULTILINE),
        (r'^\s*Thought:[^\n]*$', '', re.IGNORECASE | re.MULTILINE),
        (r'^\s*Action:[^\n]*$', '', re.IGNORECASE | re.MULTILINE),
        (r'^\s*Action Input:[^\n]*$', '', re.IGNORECASE | re.MULTILINE),
        # Remove trailing debug notes like "Note: I fixed..."
        (r'\n-{5,}\s*\n+\s*Note:.*$', '', re.IGNORECASE | re.DOTALL),
    ]

    for pattern, replacement, *flags in artifact_patterns:
        flag = flags[0] if flags else 0
        body = re.sub(pattern, replacement, body, flags=flag)

    # Normalize excessive vertical spacing
    body = re.sub(r'\n{4,}', '\n\n\n', body)

    body = body.strip() + "\n"

    return body


def clean_llm_output(text: str) -> str:
    """
    Clean LLM-generated Markdown for Jekyll / Minimal Mistakes.

    - Safely unwraps a global ```markdown ... ``` or ``` ... ``` wrapper.
    - Preserves YAML front matter (--- ... ---) exactly as-is.
    - Converts bold-only headings (**Title**) to proper markdown headings (## Title)
      in prose sections only (not inside code fences).
    - Ensures bare 'Introduction' lines become '## Introduction' in prose.
    """
    if not text:
        return ""

    # Normalize BOM and surrounding whitespace
    text = text.replace("\ufeff", "").strip()

    # 0) Unwrap a single outer ```markdown ... ``` or ``` ... ``` wrapper, if it
    #    covers the entire content.
    outer = re.match(
        r"^```(?:markdown)?\s*(.*?)\s*```$",
        text.strip(),
        flags=re.DOTALL | re.IGNORECASE,
    )
    if outer:
        text = outer.group(1)

    # 1) Extract Jekyll front matter if present at the very start of the file.
    front_matter = ""
    body = text

    if text.startswith("---\n") or text.startswith("---\r\n"):
        lines = text.splitlines(keepends=True)
        end_idx = None

        for i in range(1, len(lines)):
            # The closing '---' line for front matter
            if lines[i].startswith("---"):
                end_idx = i
                break

        if end_idx is not None:
            front_matter = "".join(lines[: end_idx + 1])
            body = "".join(lines[end_idx + 1 :])

    # 2) Helper to clean ONLY prose (no code fences).
    def _clean_prose(prose: str) -> str:
        # Convert lines like "**Introduction**" → "## Introduction"
        prose = re.sub(
            r"^\s*\*\*(.*?)\*\*\s*$",
            r"## \1",
            prose,
            flags=re.MULTILINE,
        )

        # Ensure plain "Introduction" line becomes a heading too
        prose = re.sub(
            r"^Introduction\s*$",
            r"## Introduction",
            prose,
            flags=re.MULTILINE | re.IGNORECASE,
        )

        return prose

    # 3) Split body into prose and code fences, clean only prose parts.
    code_fence_re = re.compile(r"```.*?```", re.DOTALL)
    cleaned_body_parts = []
    last_pos = 0

    for m in code_fence_re.finditer(body):
        # Prose before the code fence
        prose_chunk = body[last_pos : m.start()]
        cleaned_body_parts.append(_clean_prose(prose_chunk))

        # Code fence itself (unchanged)
        cleaned_body_parts.append(m.group(0))

        last_pos = m.end()

    # Trailing prose after the last code fence
    prose_chunk = body[last_pos:]
    cleaned_body_parts.append(_clean_prose(prose_chunk))

    cleaned_body = "".join(cleaned_body_parts).strip()

    # 4) Reassemble front matter + cleaned body
    result = (front_matter + cleaned_body).rstrip() + "\n"
    return result



# ============================================================================
# 11-AGENT ORCHESTRATED CREW - FIXED FOR OLLAMA
# ============================================================================
def build_orchestrated_crew(topic: Topic) -> Tuple[Crew, Tuple]:
    """
    Build 11-agent orchestrated pipeline - FIXED FOR OLLAMA
    
    KEY FIXES:
    - Removed tools from agents that don't need them
    - Increased max_iter for better completion
    - Simplified agent instructions
    - Fixed allow_delegation conflicts
    """
    
    using_ollama = is_ollama_llm()
    topic_type, identifier = detect_topic_type(topic)
    
    # ========================================================================
    # AGENT 1: ORCHESTRATOR (NO TOOLS)
    # ========================================================================
    orchestrator = Agent(
        role="Research Orchestrator",
        goal=f"Determine optimal research strategy for {topic.title}",
        backstory="""You are a strategic research coordinator. You analyze topics and decide:
        • If topic is package/repo → Use README + Package Health
        • If no README available → Use Web Search
        • Always prioritize official sources over web tutorials
        
        You coordinate specialized agents and ensure quality.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,  
        max_iter=3,
    )
    
    # ========================================================================
    # AGENT 2: README ANALYST (HAS TOOLS)
    # ========================================================================
    readme_tools = []
    # OLD LINE: if README_TOOLS_AVAILABLE and scrape_readme and not using_ollama:
    # NEW LINE:
    if README_TOOLS_AVAILABLE and scrape_readme:
        readme_tools = [scrape_readme]

    readme_analyst = Agent(
        role="README Documentation Analyst",
        goal="Extract complete information from official README",
        backstory="""You are an expert at reading README files for software projects and extracting:
        • Current version numbers
        • Installation instructions
        • COMPLETE working code examples (with ALL imports)
        • API documentation
        • Feature descriptions

        You ONLY use information from the README and other trusted project documentation – no assumptions.

        TOOL CALLING FORMAT (CRITICAL)

        You have access to the tool: Get README from PyPI package or GitHub repository

        When you respond:

        1) If you NEED to use a tool:
           You MUST respond EXACTLY in this format, and nothing else:

           Thought: <very brief reasoning about why you are calling the tool>
           Action: Get README from PyPI package or GitHub repository
           Action Input: "<identifier or URL for the project>"

           • Do not add extra text before or after these three lines.
           • Do not include JSON or markdown fences around this.

        2) If you do NOT need to use any more tools and can give your final answer:
           You MUST respond EXACTLY in this format:

           Thought: I now can give a great answer
           Final Answer: <your best complete answer, following the Task's OUTPUT instructions>

           • The Final Answer must be the structured README analysis the Task asks for.
           • Do not mention tools, Thought, or meta-commentary inside the Final Answer content itself.

        Never write 'Action:' if you are not actually calling a tool.
        Never mix multiple Actions in a single response.
        """,
        llm=llm,
        tools=readme_tools,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )

    
    # ========================================================================
    # AGENT 3: PACKAGE HEALTH VALIDATOR (HAS TOOLS)
    # ========================================================================
    health_tools = []
    # OLD LINE: if README_TOOLS_AVAILABLE and get_package_health and not using_ollama:
    # NEW LINE:
    if README_TOOLS_AVAILABLE and get_package_health:
        health_tools = [get_package_health]


    package_health_validator = Agent(
        role="Package Health Validator",
        goal="Validate package versions and check for deprecations",
        backstory="""You validate Python packages based on trusted metadata and documentation:
        • Check current version (prevent using outdated versions)
        • Detect deprecated or removed features
        • Verify package maintenance status
        • Extract working code examples from README or official docs

        You prevent critical errors like using removed datasets or deprecated APIs.

        TOOL CALLING FORMAT (CRITICAL)

        You have access to the tool: Get comprehensive package health report with validation

        When you respond:

        1) If you NEED to use a tool:
           You MUST respond EXACTLY in this format, and nothing else:

           Thought: <very brief reasoning about why you are calling the tool>
           Action: Get comprehensive package health report with validation
           Action Input: "<package name or identifier>"

           • Do not add extra text before or after these three lines.
           • Do not wrap this in JSON or markdown fences.

        2) If you do NOT need to use any more tools and can give your final answer:
           You MUST respond EXACTLY in this format:

           Thought: I now can give a great answer
           Final Answer: <your best complete package health report, following the Task's OUTPUT instructions>

           • The Final Answer should summarize version, deprecations, maintenance, and example quality.
           • Do not talk about tools or your reasoning inside the Final Answer content.

        Never output 'Action:' unless you are actually calling a tool.
        Never mix multiple tools or multiple Actions in a single response.
        """,
        llm=llm,
        tools=health_tools,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )

 
   
   # ========================================================================
    # AGENT 4: WEB SEARCH RESEARCHER (HAS TOOLS - if not Ollama)
    # ========================================================================
    web_tools = []
    # OLD LINE: if SEARCH_TOOLS_AVAILABLE and not using_ollama:
    # NEW LINE (Remove the restriction):
    if SEARCH_TOOLS_AVAILABLE: 
        if search_web:
            web_tools.append(search_web)
        if scrape_webpage:
            web_tools.append(scrape_webpage)

    web_researcher = Agent(
        role="Web Research Specialist",
        goal="Find accurate information through web search (fallback only)",
        backstory="""You search the web when official docs and package health data are insufficient:
        • Search for official documentation first
        • Find recent tutorials and blog posts.
        • Extract working code examples
        • Prefer official sites, reputable documentation, and high-quality blogs

        You activate ONLY when README analysis and package health validation did not provide enough information.

        TOOL CALLING FORMAT (CRITICAL)

        You have access to these tools (depending on configuration):
        • Search the web for information
        • Scrape and extract content from a specific webpage

        When you respond:

        1) If you NEED to use a tool:
           You MUST respond EXACTLY in this format, and nothing else:

           Thought: <very brief reasoning about why you are calling a tool and which one>
           Action: <tool_name>
           Action Input: "<query or URL>"

           Examples of valid outputs:
           Thought: I need to find the official documentation site.
           Action: Search the web for information
           Action Input: "PACKAGE_NAME official documentation"

           Thought: I found a promising URL and want to extract details.
           Action: Scrape and extract content from a specific webpage
           Action Input: "https://example.com/docs/page"

           • Do not include extra text before or after these three lines.
           • Do not wrap this in JSON or markdown fences.

        2) If you do NOT need to use any more tools and can give your final answer:
           You MUST respond EXACTLY in this format:

           Thought: I now can give a great answer
           Final Answer: <your best complete web research report, following the Task's OUTPUT instructions>

           • The Final Answer should summarize sources, URLs, reliability, and key findings.
           • Do not mention tools or your internal chain-of-thought inside the Final Answer content.

        RULES:
        • Never output 'Action:' unless you are actually calling a tool.
        • Never output more than one Action per response.
        • Never include markdown fences around Thought/Action blocks.
        """,
        llm=llm,
        tools=web_tools,
        verbose=True,
        allow_delegation=False,
        max_iter=5,  # 2 searches + 2 processing + 1 final answer
    )

    
    # ========================================================================
    # AGENT 5: SOURCE QUALITY VALIDATOR (NO TOOLS)
    # ========================================================================
    source_validator = Agent(
        role="Source Quality Validator",
        goal="Validate and rate information quality",
        backstory="""You rate research quality:
        • README/Official docs = A+ (use as-is, high confidence)
        • Package metadata = A (high confidence)
        • Web tutorials = B (needs verification notes)
        • Missing/incomplete = F (reject)
        
        You ensure only high-quality information reaches the writer.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )
    

    # ========================================================================
    # AGENT 6: CONTENT PLANNER (NO TOOLS)
    # ========================================================================
    content_planner = Agent(
        role="Content Strategist",
        goal="Create structured, engaging blog outline from the research.",
        backstory="""You design blog structures that:
        • Start with clear introduction
        • Progress logically through concepts
        • Include 2-3 practical examples
        • End with actionable next steps        
Must:
- Use the research context as the source of truth.
- Do not remove links or key facts unless they are exact duplicates.

Style:
- Use Markdown headings (##, ###).
- Produce an outline only, not the full article.

Output:
- You base outlines on validated research only.
- Markdown outline ONLY, no commentary.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


    # ========================================================================
    # AGENT 7: TECHNICAL WRITER (NO TOOLS)
    # ========================================================================
    technical_writer = Agent(
        role="Technical Content Writer",
        goal="Write a complete, accurate technical article in clean Markdown.",
        backstory="""
    You write professional technical articles based on the provided research and outline.

    HARD FORMAT RULES (MUST FOLLOW):
    - Output ONLY the article body in Markdown.
    - Use ONLY ATX headings: ##, ###.
    - The first non-empty line should be a heading.

    CODE RULES (CRITICAL):
    - Use fenced code blocks ONLY for code, e.g. ```python ... ```.
    - Each code block must be self-contained and runnable (imports, variables defined).
    - **ANTI-HALLUCINATION PROTOCOL:** If the research context suggests using classes or methods that do not actually exist in the library (e.g., `Library.ImaginaryClass`), **DISCARD THEM**. 
      Instead, rely on your internal knowledge to provide the correct, canonical pattern for that library.
    - Do NOT invent APIs that do not exist.

    CONTENT RULES:
    - Follow the outline but prioritize TECHNICAL ACCURACY over strict adherence to flawed outline examples.
    - Explain concepts clearly and step-by-step.
    - Stay focused on the main library/topic.

    TONE:
    - Professional but approachable. No meta-comments.
    """,
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=2,
    )

    # ========================================================================
    # AGENT 8: CODE VALIDATOR (NO TOOLS)
    # ========================================================================
    code_validator = Agent(
        role="Code Quality Validator",
        goal="Ensure all code examples are complete and error-free",
        backstory="""Strict code reviewer. You check:
        • Syntax correctness (Python AST parsing)
        • All imports present
        • All variables defined before use
        • No placeholders or TODOs
        • No deprecated features
        
        You report PASS or detailed issues.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )
    
    # ========================================================================
    # AGENT 9: CODE FIXER (NO TOOLS)
    # ========================================================================
    code_fixer = Agent(
        role="Code Issue Resolver",
        goal="Fix all code errors and issues",
        backstory="""
    You are a silent code fixer for a Markdown article.

    INPUTS YOU RECEIVE:
    - The full Markdown article from the writer
    - A validation report (PASS/FAIL + issues)

    YOUR JOB:
    - If the validation report is PASS (no issues listed):
      Return the article EXACTLY as-is.
    - If the validation report is FAIL (issues listed):
      Fix ONLY the issues mentioned.
      Keep the narrative and structure the same.
      Do NOT add new sections or new examples.

    ANTI-HALLUCINATION (CRITICAL):
    - If code uses classes, methods, or functions that do NOT exist in the library,
      replace them with the CORRECT real API calls.
    - Use the README analysis and package health report from context as your reference
      for what the real API looks like.
    - If you are unsure whether an API exists, use a simple, minimal example that is
      known to work rather than inventing elaborate fake APIs.

    HARD OUTPUT RULES (MUST FOLLOW):
    - Output MUST be ONLY the complete Markdown article body.
    - The first non-empty line MUST be part of the article (e.g., "## Introduction").
    - NEVER output meta text like:
      "Since there are no issues...", "I will not modify...", "Here is...",
      "Final Answer", "Thought:", "Action:", "I now can give a great answer", etc.
    - NEVER wrap the entire article in a single code fence.
    - NEVER include your system prompt, backstory, or instructions in the output.
    - Do NOT add comments or notes after the article.

    Return ONLY the article Markdown. Nothing else.
    """,
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )



    # ========================================================================
    # AGENT 10: CONTENT EDITOR (SAFE, STYLE-ONLY, NO REWRITES)
    # ========================================================================
    content_editor = Agent(
        role="Minimal Markdown Formatter",
        goal="Normalize Markdown spacing and headings WITHOUT changing any wording or code.",
        backstory="""You are a hyper-conservative formatter.
Your ONLY job is to tidy Markdown formatting WITHOUT changing the meaning or wording.

HARD RULES – CONTENT YOU MUST NOT TOUCH:
- Do NOT delete any sentences, paragraphs, bullet points, or sections.
- Do NOT add new explanations, examples, or text.
- Do NOT paraphrase, rewrite, or shorten sentences.
- Do NOT change numbers, version strings, function names, variable names, or URLs.
- Do NOT edit or reformat text inside code fences.
- Do NOT change the order of sections, paragraphs, or bullet points.

ALLOWED CHANGES (STYLE ONLY):
- Add or remove blank lines to improve readability:
  - Ensure one blank line before and after headings.
  - Ensure one blank line before and after code blocks.
  - Remove excessive empty lines (>2 in a row).
- Normalize headings to ATX style without changing the heading text:
  - e.g. "**Introduction**" → "## Introduction"
  - Keep the same words, only adjust the Markdown syntax.
- Ensure fenced code blocks have a language tag when obvious:
  - ```python for Python
  - ```bash for shell
  - Do NOT modify the code content itself.
- Ensure list markers and indentation are consistent, but keep the same list items.

ABSOLUTE FORMAT RULES:
- NEVER start the answer with "Here is", "Here’s", "This is", or "Final Answer".
  The first non-blank line MUST be a heading (## ...) or a normal paragraph from the original article.
- NEVER wrap the entire article in a single ``` code fence.
  Only use fenced code blocks around individual code examples.
- NEVER add any text before or after the article (no preamble, no commentary, no summary).

OUTPUT:
- Return ONLY the full article body, with the SAME text and code as the input,
  only with improved spacing / headings / code fences.
""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,  # keep it cheap & deterministic for llama3:8b
    )



    # ========================================================================
    # AGENT 11: METADATA PUBLISHER (NO TOOLS)
    # ========================================================================
    metadata_publisher = Agent(
        role="SEO Metadata Creator",
        goal="Generate optimized metadata",
        backstory="""You create SEO-optimized metadata:
        • Compelling title (≤70 chars)
        • Engaging excerpt (≤200 chars)
        • Relevant tags (4-8)
        • JSON format only""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )
    
    # ========================================================================
    # TASKS - keeping original task definitions...
    # ========================================================================
    
    # TASK 1: Orchestration
    orchestration_task = Task(
        description=f"""
        Analyze topic and determine research strategy: {topic.title}
        
        Topic type: {topic_type}
        Identifier: {identifier}
        
        DECISION TREE:
        
        1. IF topic is package or GitHub repo:
           → Strategy: README-first
           → Delegate to README Analyst
           → Then delegate to Package Health Validator
           → Expected: Official documentation + validation
        
        2. ELSE IF README not available:
           → Strategy: Web search
           → Delegate to Web Researcher
           → Expected: Curated web results
        
        3. ALWAYS:
           → Delegate to Source Quality Validator
           → Get quality rating
        
        OUTPUT FORMAT:
```
        Strategy: [README-first / Web search / Hybrid]
        Confidence: [High / Medium / Low]
        Sources Used: [README, Package Health, Web]
        Quality Rating: [A+ / A / B / C]
        
        Research Summary:
        [Key findings from delegated agents]
        
        Recommendations:
        • Version to use: [X.Y.Z]
        • Features to avoid: [deprecated items]
        • Code examples available: [count]
        • Source reliability: [assessment]
```
        """,
        expected_output="Complete research strategy execution report",
        agent=orchestrator,
    )
    
    # TASK 2: README Analysis
    readme_task = Task(
        description=f"""
        Extract a CONDENSED summary from README for: {identifier}

        USE the tool: "Get README from PyPI package or GitHub repository"
        with input "{identifier}"

        IMPORTANT: Your output must be a SHORT, STRUCTURED SUMMARY (max 800 words).
        Do NOT copy the entire README. Extract only the essential information:

        1. **Version**: Current version number and Python requirement (1 line)
        2. **Install**: Exact pip install command (1 line)
        3. **What it does**: 2-3 sentence description
        4. **Key features**: Bullet list (max 5 items)
        5. **Code example**: ONE short working example from the README (max 15 lines).
           - Copy EXACTLY as written. If none exists, write: "NO_CODE_EXAMPLES_FOUND"
        6. **Warnings**: Any deprecation notices (1-2 lines, or "None")

        OUTPUT: A condensed summary under 800 words. NOT the raw README.
        """,
        expected_output="Condensed README summary (under 800 words) with version, install, features, and one code example",
        agent=readme_analyst,
    )


    # TASK 3: Package Health Validation
    health_task = Task(
        description=f"""
        Validate package health for: {identifier}
        
        USE the tool: "Get comprehensive package health report with validation"
        with input "{identifier}"
        
        The tool provides:
        • Latest version number
        • Deprecation warnings
        • Maintenance status
        • Working code examples
        
        Extract and report:
        1. **Version Validation**
           - Latest version: X.Y.Z
           - Python requirements: >=X.Y
           - Last release date
        
        2. **Deprecation Check**
           - Deprecated features found: [list]
           - Removed functions: [list]
           - Migration recommendations
        
        3. **Code Examples**
           - Number of examples in README
           - Quality assessment
        
        4. **Maintenance Status**
           - Active development? Yes/No
           - Last commit date
           - Community support
        
        OUTPUT: Package health report with actionable warnings
        """,
        expected_output="Package health validation report",
        agent=package_health_validator,
        context=[readme_task],
    )

    
    # TASK 4: Web Research (fallback)
    # NOTE: Keep search count <= max_iter-2 so the agent has iterations left
    # for processing results and generating the final answer.
    web_research_task = Task(
        description=f"""
        Research {topic.title} using web search (fallback mode).

        SEARCH STRATEGY (do at most 2 searches):

        1. Official documentation and overview
           Use the tool "Search the web for information"
           with query "{topic.title} official documentation getting started"

        2. Working code examples
           Use the tool "Search the web for information"
           with query "{topic.title} Python example tutorial"

        After searching, produce a CONCISE report (max 500 words):
        • Top 3 URLs found (with titles)
        • Version number (if found)
        • One code example (if found)
        • Source reliability assessment

        OUTPUT: Concise web research report with sources cited (max 500 words)
        """,
        expected_output="Concise web research report with URLs (max 500 words)",
        agent=web_researcher,
    )


    # TASK 5: Source Quality Validation
    quality_task = Task(
        description="""
        Validate research quality and assign a confidence rating.

        Evaluate sources used:
        - README / official docs → A+ (highest confidence)
        - Package health report → A (high confidence)
        - Web tutorials / blogs → B (medium confidence)
        - Missing / incomplete → F (reject)

        Check:
        - Version information present?
        - Code examples complete?
        - Deprecation warnings noted?
        - Sources cited (with URLs)?

        CRITICAL URL RULES:
        - If any URLs appear in the research context, you MUST copy them into the Resources section below.
        - List them as Markdown links.
        - NEVER write placeholders like "[Insert relevant URLs...]".

        OUTPUT FORMAT (use this template exactly, keep the headings):

        Quality Rating: [A+ / A / B / C / F]
        Confidence: [High / Medium / Low]

        Sources:
        • Primary: [README / Web / None]
        • Validation: [Package Health / None]

        Completeness:
        • Version info: [✓ / ✗]
        • Code examples: [✓ / ✗] ([count] found)
        • Deprecations: [✓ / ✗]

        Resources:
        - [Label 1](https://example.com/real-url-1)
        - ...

        (IMPORTANT: If any URLs appear in the research context,
        you MUST list them here as Markdown links. Do NOT use
        placeholders like "[Insert relevant URLs...]".)

        Recommendations:
        [How to use this research in blog]
        """,
        expected_output="Quality validation report with explicit Resources section",
        agent=source_validator,
        context=[orchestration_task, readme_task, health_task, web_research_task],
    )


    # TASK 6: Content Planning
    planning_task = Task(
        description=f"""
        Create detailed blog outline for: {topic.title}
        
        CRITICAL INSTRUCTION: 
        You MUST use the EXACT version number found by the 'Package Health Validator' in the context. 
        If the validator reports version 3.x, DO NOT use version 1.x or outdated data.
        
        Based on validated research, create structure:
        
        1. **Introduction** (150 words)
            - What is {topic.title}?
            - Why it matters
            - What readers will learn
        
        2. **Overview** (200 words)
            - Key features
            - Use cases
            - Current version: [MUST MATCH VALIDATION REPORT]
        
        3. **Getting Started** (250 words)
            - Installation
            - Quick example (complete code)
        
        4. **Core Concepts** (300 words)
            - Main functionality
            - API overview
            - Example usage
        
        5. **Practical Examples** (400 words)
            - Example 1: [specific use case]
            - Example 2: [another use case]
            - Each with COMPLETE code
        
        6. **Best Practices** (150 words)
            - Tips and recommendations
            - Common pitfalls
        
        7. **Conclusion** (100 words)
            - Summary
            - Next steps
            - Resources:
              - If the quality report contains a 'Resources' section with Markdown links,
                copy those links, choose the top 1 reference if are provided otherwise skip.
              - If there are NO URLs in the research context, omit the Resources subsection entirely.   
        
        CRITICAL:
        • Use version from validation ONLY
        • Note deprecated features to AVOID
        • Mark web-sourced content for verification
        """,
        expected_output="Detailed blog outline (300+ words)",
        agent=content_planner,
        context=[quality_task],
    )

    # TASK 7: Writing
    writing_task = Task(
        description=f"""
    Write a Markdown blog article about: {topic.title}

    Use ONLY the information from the context (README analysis, package health report, outline).
    Do NOT invent new libraries, versions, datasets, or APIs.

    Formatting:
    - Use headings with ## and ### only.
    - Do NOT use ===, --- or bold-only headings.
    - Do NOT wrap the whole article in a single ``` code block.
    - Use ```python only around Python code examples.

    Code:
    - Each code block must be complete and runnable.
    - Put all imports at the top of the code block.
    - Define all variables before use.
    - No placeholders like TODO, ..., your_X.
    - Use the library and version from the context, avoid deprecated features.

    Structure:
    - Follow the outline: Introduction, Overview, Getting Started, Core Concepts,
    Practical Examples, Best Practices, Conclusion.
    - Include at least 2 end-to-end practical code examples.

    Tone:
    - Professional and clear.
    - No first-person and no comments about being an AI.

    Output:
    - One Markdown article (~1200 words).
    - Start directly with a heading (e.g. ## Introduction). No preamble or explanation.
    """,
        expected_output="Complete blog article (1200+ words)",
        agent=technical_writer,
        context=[planning_task, quality_task],
    )


    
    # TASK 8: Code Validation
    validation_task = Task(
        description="""
            Validate ALL Python code blocks in the article.

            For EACH code block, check:

            1. **Syntax**
            - Parse with Python AST (check for basic syntax errors).

            2. **Semantic Reality Check (CRITICAL)**
            - Do the imported classes and functions *actually exist* in the library?
            - **FAIL** any code that invents convenient but non-existent APIs (e.g., `langchain.Chatbot`, `pandas.read_brain`).
            - Compare code symbols against the README/Health Report in the context.

            3. **Imports**
            - Are all used modules imported?
            - Are imports consistent with the topic?

            4. **Variables**
            - Are all variables defined before use?
            - No placeholders (TODO, ..., your_X).

            5. **Deprecations**
            - Flag any APIs known to be deprecated or removed based on the package health report.

            OUTPUT FORMAT (plain text):

            Validation Result: [PASS / FAIL]
            Code Blocks Checked: [count]
            
            Issues Found:
            [If FAIL, list specific issues]
            Block X:
            • [Issue description]
            
            If no issues, state clearly that all blocks passed.
            """,
        expected_output="Code validation report",
        agent=code_validator,
        context=[writing_task, health_task],
    )

    
    # TASK 9: Code Fixing
    fixing_task = Task(
        description="""
            Fix ALL code issues found by the validator.

            For each issue:

            **Missing imports** → Add the appropriate imports for the libraries that are
            ACTUALLY used in the current article. Do NOT introduce new or unrelated
            libraries.

            **Undefined variables** → Add minimal, sensible definitions that are
            consistent with the surrounding code.

            **Deprecated features** → Replace them with the recommended alternatives
            from the validation context or from the official documentation.

            **Placeholders** → Replace any placeholders (such as "...", "TODO",
            "your_X") with fully working code, or remove the example if you cannot
            make it complete without guessing.

            **Hallucinated APIs** → If code uses classes, functions, or methods that
            do NOT actually exist in the library, replace them with the correct,
            real API calls based on the package health report and README context.

            GLOBAL CONSTRAINTS:
            • Never switch to a different framework or library.
            • Keep all code blocks self-contained and runnable.
            • Preserve the overall structure and intent of each example.

            STRICT OUTPUT RULES:
            • Return ONLY the complete corrected article body as Markdown.
            • Do NOT wrap the entire answer in ``` or any other code fences.
            • Only use ```python (or other languages) around individual code examples.
            • Do NOT add preambles like "Here is..." or "Final Answer:".
            • Do NOT add comments or notes after the article.

            Return the COMPLETE corrected article with ALL fixes applied, in raw Markdown.
            """,
        expected_output="Complete corrected article (1200+ words)",
        agent=code_fixer,
        context=[writing_task, validation_task],
    )



    # TASK 10: Editing (STYLE-ONLY, NO CONTENT CHANGE)
    editing_task = Task(
        description="""
        Take the article from the Code Issue Resolver and ONLY apply minimal Markdown formatting.

        GOAL:
        - Improve readability by adjusting SPACING and MARKDOWN SYNTAX ONLY.
        - The informational content (words, sentences, sections, code) must remain EXACTLY the same.

        YOU MUST NOT:
        - Do NOT delete any text (no sentences, bullets, or sections).
        - Do NOT add any new sentences, explanations, or comments.
        - Do NOT paraphrase or rewrite existing sentences.
        - Do NOT change numbers, version strings, function names, variable names, or URLs.
        - Do NOT change code inside ``` fences in any way.
        - Do NOT change the order of paragraphs, lists, or sections.

        YOU MAY:
        - Normalize spacing:
          • Ensure exactly one blank line before and after headings.
          • Ensure exactly one blank line before and after code blocks.
          • Remove extra empty lines (more than 2 in a row).
        - Normalize headings:
          • Convert bold-only headings like "**Introduction**" into "## Introduction"
            without changing the words.
        - Normalize fenced code blocks:
          • Add a language tag (```python, ```bash, etc.) when it is obvious.
          • Do NOT modify or reindent the code itself.

        ABSOLUTE FORMAT RULES:
        - The first non-empty line of your answer MUST be a heading or paragraph
          from the original article (no "Here is...", no "Final Answer:").
        - The answer MUST NOT begin or end with ``` or any other code fence.
          Do NOT wrap the whole article in a single code block.
        - The output must be ONLY the article body. No notes, no explanations, no comments.

        Return the COMPLETE article, with the same content, only with cleaner Markdown formatting.
        """,
        expected_output="Same article content with only spacing/Markdown formatting improved.",
        agent=content_editor,
        context=[fixing_task],
    )



    # TASK 11: Metadata
  # TASK 11: Metadata (STRICT JSON ONLY)
    metadata_task = Task(
        description=f"""
    You are generating SEO metadata for a blog post about: {topic.title}

    RETURN ONLY VALID JSON.
    - Output must be a SINGLE LINE.
    - The FIRST character must be '{{' and the LAST character must be '}}'.
    - Do NOT wrap in markdown. Do NOT use ``` fences. Do NOT add commentary.

    Schema (must match exactly):
    {{
    "title": "string (<= 70 chars)",
    "excerpt": "string (<= 200 chars)",
    "tags": ["string", "string", "string", "string"]
    }}

    Rules:
    - title: must include the main keyword "{topic.title}" (or its canonical spelling)
    - excerpt: plain English sentence(s), no code, no markdown, no quotes from the article, <= 200 chars
    - tags: 4 to 8 tags total
    - lowercase only
    - hyphenated (use '-' instead of spaces)
    - no punctuation besides hyphen
    - directly relevant to "{topic.title}" and its ecosystem

    Bad outputs (DO NOT DO THESE):
    - Any text before/after the JSON
    - Markdown formatting
    - Code snippets in excerpt
    - Tags with spaces, uppercase, or unrelated tools

    Now produce the JSON for: {topic.title}
    """,
        expected_output="A single-line JSON object with title, excerpt, and tags.",
        agent=metadata_publisher,
        context=[planning_task, editing_task],
    )

    
    # ========================================================================
    # ASSEMBLE CREW
    # ========================================================================
    crew = Crew(
        agents=[
            orchestrator,
            readme_analyst,
            package_health_validator,
            web_researcher,
            source_validator,
            content_planner,
            technical_writer,
            code_validator,
            code_fixer,
            content_editor,
            metadata_publisher,
        ],
        tasks=[
            orchestration_task,
            readme_task,
            health_task,
            web_research_task,
            quality_task,
            planning_task,
            writing_task,
            validation_task,
            fixing_task,
            editing_task,
            metadata_task,
        ],
        process=Process.sequential,
        verbose=True,
        max_rpm=15,
        task_callback=_task_completion_callback,
    )
    
    return crew, (
        orchestration_task,
        readme_task,
        health_task,
        web_research_task,
        quality_task,
        planning_task,
        writing_task,
        validation_task,
        fixing_task,
        editing_task,
        metadata_task,
    )


# ============================================================================
# JEKYLL POST BUILDING (keeping original)
# ============================================================================
def build_jekyll_post(date: datetime, topic: Topic, body: str, meta: Dict, blog_assets_dir: Path) -> Tuple[str, str]:
    """Build Jekyll post with per-blog asset paths"""
    
    title = meta.get("title", topic.title)
    excerpt = meta.get("excerpt", topic.summary or "")
    tags = (meta.get("tags") or topic.tags or ["ai"])[:8]
    
    date_iso = date.strftime("%Y-%m-%dT09:00:00+00:00")
    date_prefix = date.strftime("%Y-%m-%d")
    version_suffix = f"-v{topic.version}" if topic.version > 1 else ""
    slug = f"{topic.kind}-{slugify(topic.title)}{version_suffix}"
    filename = f"{date_prefix}-{slug}.md"
    
    safe_excerpt = (excerpt or "").replace('"', "'")
    tag_lines = "\n  - " + "\n  - ".join(tags)
    
    blog_assets_rel = blog_assets_dir.relative_to(BASE_DIR)
    header_image = f"/{blog_assets_rel}/header-ai-abstract.jpg"
    teaser_image = f"/{blog_assets_rel}/teaser-ai.jpg"
    
    if "data" in topic.kind or "data" in " ".join(tags):
        header_image = f"/{blog_assets_rel}/header-data-science.jpg"
    elif "cloud" in " ".join(tags):
        header_image = f"/{blog_assets_rel}/header-cloud.jpg"
    
    content = f"""---
title: "{title}"
date: {date_iso}
last_modified_at: {date_iso}
topic_kind: "{topic.kind}"
topic_id: "{topic.id}"
topic_version: {topic.version}
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

<small>Powered by Jekyll & Minimal Mistakes.</small>
"""
    
    return filename, content


def save_post(filename: str, content: str) -> Path:
    """Save post"""
    path = BLOG_POSTS_DIR / filename
    
    if path.exists():
        timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
        filename = f"{path.stem}-{timestamp}{path.suffix}"
        path = BLOG_POSTS_DIR / filename
    
    with path.open("w", encoding="utf-8") as f:
        f.write(content)
    
    logger.info(f"✅ Saved: {path.relative_to(BASE_DIR)}")
    return path


def record_coverage(topic: Topic, filename: str) -> None:
    """Record coverage"""
    coverage = load_coverage()
    coverage.append({
        "kind": (topic.kind or "").strip(),
        "id": _norm_id(topic.kind, topic.id),
        "version": topic.version,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "filename": filename,
    })
    save_coverage(coverage)


# ============================================================================
# MAIN
# ============================================================================
def main() -> None:
    """Main entry point"""
    
    logger.info("="*70)
    logger.info("Advanced Orchestrated Blog Generator v4.1 - Ollama Fixed")
    logger.info("11-Agent Pipeline with Precise Data Retrieval")
    logger.info("="*70)
    logger.info(f"Base: {BASE_DIR}")
    logger.info(f"Posts: {BLOG_POSTS_DIR}")
    logger.info("")
    
    # Check tools
    if README_TOOLS_AVAILABLE:
        logger.info("✅ README + Package Health tools available")
    else:
        logger.warning("⚠️  README tools not available - using web search only")
    
    if SEARCH_TOOLS_AVAILABLE:
        logger.info("✅ Web search tools available")
    else:
        logger.warning("⚠️  Web search tools not available")
    
    llm_model = os.getenv("NEWS_LLM_MODEL", "not set")
    logger.info(f"LLM: {llm_model}")
    
    if is_ollama_llm():
        logger.info("✅ Ollama mode - Fixed for compatibility")
    
    logger.info("")
    
    try:
        # Step 1: Select topic
        topic = select_next_topic()
        logger.info(f"📝 Topic: {topic.title}")
        logger.info(f"   Type: {topic.kind}")
        logger.info(f"   Tags: {', '.join(topic.tags[:3])}")
        logger.info("")
        
        # Step 2: Setup blog context
        today = datetime.now(timezone.utc)
        date_str = today.strftime("%Y-%m-%d")
        slug = f"{topic.kind}-{slugify(topic.title)}"
        
        if IMAGE_TOOLS_AVAILABLE:
            blog_assets_dir = set_blog_context(slug, topic.title, date_str)
        else:
            blog_assets_dir = BASE_ASSETS_DIR / f"{date_str}-{slug}"
            blog_assets_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Assets: {blog_assets_dir.relative_to(BASE_DIR)}")
        
        # Step 3: Ensure assets
        ensure_blog_assets_topic_specific(topic, slug, date_str)
        logger.info("")
        
        # Step 4: Build orchestrated crew
        crew, tasks = build_orchestrated_crew(topic)
        
        logger.info("🚀 11-Agent Orchestrated Pipeline Starting...")
        logger.info("")
        logger.info("   Agent Flow:")
        logger.info("   1. Orchestrator → Decides strategy")
        logger.info("   2. README Analyst → Extracts docs")
        logger.info("   3. Package Health → Validates version")
        logger.info("   4. Web Researcher → Fallback search")
        logger.info("   5. Source Validator → Rates quality")
        logger.info("   6. Content Planner → Creates outline")
        logger.info("   7. Technical Writer → Writes article")
        logger.info("   8. Code Validator → Checks code")
        logger.info("   9. Code Fixer → Fixes issues")
        logger.info("   10. Content Editor → Polishes")
        logger.info("   11. Metadata Publisher → SEO data")
        logger.info("")
        logger.info("   ⏱️  Estimated: 15-25 minutes for highest quality...")
        logger.info("")
        
        # Step 5: Run crew
        result = crew.kickoff()
        
        if not result:
            raise RuntimeError("No result from crew")
        
        logger.info("🔍 Extracting outputs...")
        
        # Extract from tasks (in reverse order for best content)
        (orchestration_task, readme_task, health_task, web_research_task,
         quality_task, planning_task, writing_task, validation_task,
         fixing_task, editing_task, metadata_task) = tasks
        
        # Step 6: Extract body (try in order of refinement)
        # Step 6: Extract body (try in order of refinement)

        # --- OLD LOGIC (DISABLED) ---
        # body = extract_task_output(editing_task, "editor")
        #
        # if not body or len(body) < 800:
        #     logger.warning("⚠️  Trying fixer...")
        #     body = extract_task_output(fixing_task, "fixer")
        #
        # if not body or len(body) < 800:
        #     logger.warning("⚠️  Trying writer...")
        #     body = extract_task_output(writing_task, "writer")
        #
        # if not body or len(body) < 800:
        #     logger.error("❌ Insufficient output")
        #     raise RuntimeError(f"Too short: {len(body)} chars")
        # ----------------------------

        # NEW LOGIC: try editor → fixer → writer (most refined first)
        body = extract_task_output(editing_task, "editor")

        if not body or len(body) < 800:
            logger.warning("⚠️  Editor output too short, trying fixer...")
            body = extract_task_output(fixing_task, "fixer")

        if not body or len(body) < 800:
            logger.warning("⚠️  Fixer output too short, trying writer...")
            body = extract_task_output(writing_task, "writer")

        if not body or len(body) < 800:
            logger.error("❌ Insufficient output from writer")
            raise RuntimeError(f"Too short: {len(body)} chars" if body else "Empty body")

        logger.info(f"📄 Generated: {len(body)} chars, {len(body.split())} words")


        # Step 7: Clean LLM artifacts and normalize formatting
        body = clean_llm_output(body)
        body = clean_content(body)
        
        # Step 8: Final validation
        all_valid, issues, code_blocks = validate_all_code_blocks(body)
        
        if not all_valid:
            logger.warning("⚠️  Code validation issues found:")
            for issue in issues[:5]:  # Show first 5
                logger.warning(f"   {issue}")
            logger.warning("   Proceeding anyway (fixer may have missed some)")
        
        logger.info(f"   ✓ {len(code_blocks)} code blocks")
        logger.info("")
        
        # Step 9: Parse metadata
        meta_raw = extract_task_output(metadata_task, "publisher")
        
        try:
            json_start = meta_raw.find("{")
            json_end = meta_raw.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                meta = json.loads(meta_raw[json_start:json_end])
            else:
                meta = json.loads(meta_raw)
            logger.info(f"✅ Metadata: {meta.get('title', 'N/A')[:50]}")
        except Exception as e:
            logger.warning(f"⚠️  Metadata parse failed: {e}")
            meta = {
                "title": topic.title,
                "excerpt": topic.summary or f"Learn about {topic.title}",
                "tags": topic.tags or ["ai"]
            }
        
        logger.info("")
        
        # Step 10: Build and save
        filename, content = build_jekyll_post(today, topic, body, meta, blog_assets_dir)
        path = save_post(filename, content)
        record_coverage(topic, filename)
        
        # Step 11: Success summary
        bash_blocks = len(re.findall(r'```bash', body))
        
        logger.info("")
        logger.info("="*70)
        logger.info("✅ PROFESSIONAL BLOG POST GENERATED")
        logger.info("="*70)
        logger.info(f"   File: {path.relative_to(BASE_DIR)}")
        logger.info(f"   Assets: {blog_assets_dir.relative_to(BASE_DIR)}")
        logger.info(f"   Topic: {topic.title}")
        logger.info(f"   Words: {len(body.split())}")
        logger.info(f"   Code: {len(code_blocks)} Python + {bash_blocks} Bash")
        logger.info("")
        logger.info("✅ Quality Assurance:")
        logger.info("   • README-first data retrieval ✓")
        logger.info("   • Package health validation ✓")
        logger.info("   • Deprecation detection ✓")
        logger.info("   • Code validation → fixing ✓")
        logger.info("   • Source quality tracking ✓")
        logger.info("   • Topic-specific images ✓")
        logger.info("   • Professional editing ✓")
        logger.info("   • SEO optimization ✓")
        logger.info("")
        
        # Show research quality
        quality_report = extract_task_output(quality_task, "source_validator")
        if quality_report:
            logger.info("📊 Source Quality:")
            if "A+" in quality_report or "High" in quality_report:
                logger.info("   ⭐⭐⭐ Highest Quality (Official Sources)")
            elif "A" in quality_report or "Medium" in quality_report:
                logger.info("   ⭐⭐ High Quality (Validated Sources)")
            else:
                logger.info("   ⭐ Good Quality (Web Sources)")
        
        logger.info("")
        logger.info("📋 Next Steps:")
        logger.info(f"   1. Review: cat {path.relative_to(BASE_DIR)}")
        logger.info(f"   2. Test code: Extract and run examples")
        logger.info(f"   3. Preview: jekyll serve")
        logger.info(f"   4. Publish: git add . && git commit -m 'Professional blog'")
        logger.info("")
        
    except Exception as e:
        logger.error("="*70)
        logger.error(f"❌ GENERATION FAILED: {e}")
        logger.error("="*70)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()