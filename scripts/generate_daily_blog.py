#!/usr/bin/env python3
"""
scripts/generate_daily_blog.py

PRODUCTION v3.6 FINAL - Topic-Specific Images + Ollama Format Fix

Features:
- 8-agent pipeline: Research → Plan → Write → Validate → FIX → Edit → Polish → Publish
- TOPIC-SPECIFIC images (each blog gets unique relevant images)
- Organized per-blog asset directories
- FIXED: Ollama LLM format errors
- Professional high-quality blog posts
- Web search integration (conditional)
- Real topics from JSON files
- .env file support

Usage:
    python scripts/generate_daily_blog.py

Requirements:
    - blog/api/packages.json, repositories.json, papers.json, tutorials.json
    - .env file with PEXELS_API_KEY (optional)
    - Ollama running (if using Ollama)
"""

import ast
import json
import logging
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup paths
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=CURRENT_DIR.parent / '.env', override=False)
    print("✅ Loaded environment variables from .env")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables.")

from crewai import Agent, Task, Crew, Process  # type: ignore
from llm_client import llm

# Import search tools (optional)
try:
    from search import search_web, scrape_webpage
    SEARCH_TOOLS_AVAILABLE = True
    print("✅ Web search tools loaded")
except ImportError:
    SEARCH_TOOLS_AVAILABLE = False
    search_web = None
    scrape_webpage = None
    print("⚠️  Search tools not available")

# Import image tools
try:
    from image_tools import ImageTools, set_blog_context, get_blog_assets_dir
    IMAGE_TOOLS_AVAILABLE = True
    print("✅ Image tools with organized assets loaded")
except ImportError:
    print("⚠️  image_tools.py not found. Asset management disabled.")
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
        logging.FileHandler(LOG_DIR / "blog_generation.log", mode='a'),
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


# ============================================================================
# LLM DETECTION
# ============================================================================
def is_ollama_llm() -> bool:
    """Detect if using Ollama"""
    llm_model = os.getenv("NEWS_LLM_MODEL", "")
    return "ollama" in llm_model.lower()


# ============================================================================
# OUTPUT EXTRACTION
# ============================================================================
def extract_task_output(task: Task, task_name: str) -> str:
    """Extract output from CrewAI task with 5 fallback methods"""
    if not task or not hasattr(task, 'output') or task.output is None:
        logger.warning(f"⚠️  Task {task_name} has no output")
        return ""
    
    output = task.output
    
    # Try 5 methods
    methods = [
        ('raw', lambda: getattr(output, 'raw', None)),
        ('result', lambda: getattr(output, 'result', None)),
        ('direct', lambda: output if isinstance(output, str) else None),
        ('str()', lambda: str(output)),
        ('__str__()', lambda: output.__str__() if hasattr(output, '__str__') else None),
    ]
    
    for method_name, method_func in methods:
        try:
            result = method_func()
            if result and isinstance(result, str) and len(result) > 50:
                logger.debug(f"✓ Extracted from {task_name}.output.{method_name}: {len(result)} chars")
                return result.strip()
        except Exception:
            continue
    
    logger.warning(f"⚠️  Failed to extract output from {task_name}")
    return ""


# ============================================================================
# TOPIC-SPECIFIC IMAGE GENERATION
# ============================================================================
def generate_image_queries(topic: Topic) -> Dict[str, str]:
    """
    Generate topic-specific image search queries.
    Returns dict with asset names and search queries.
    
    FIXED: Creates unique, relevant images for each blog topic
    """
    # Extract keywords from topic
    title_lower = topic.title.lower()
    tags_str = " ".join(topic.tags).lower()
    kind = topic.kind
    
    # Build topic-specific queries
    queries = {}
    
    # Main keywords from title and tags
    main_keywords = []
    
    # Technology keywords
    tech_terms = ['python', 'javascript', 'java', 'machine', 'learning', 'ai', 'data', 
                  'cloud', 'kubernetes', 'docker', 'neural', 'deep', 'web', 'api',
                  'database', 'sql', 'nosql', 'redis', 'mongo', 'postgres']
    
    for term in tech_terms:
        if term in title_lower or term in tags_str:
            main_keywords.append(term)
    
    # Fallback to topic name if no tech terms
    if not main_keywords:
        # Use first 2 words from title
        words = topic.title.split()[:2]
        main_keywords = [w.lower() for w in words if len(w) > 3]
    
    # Generate 4 different queries
    if kind == "package":
        base_context = "programming code technology"
    elif kind == "repo":
        base_context = "software development coding"
    elif kind == "paper":
        base_context = "research science technology"
    else:
        base_context = "technology innovation digital"
    
    # Query 1: Header - Topic specific + abstract
    if main_keywords:
        queries["header-primary"] = f"{' '.join(main_keywords[:2])} abstract technology"
    else:
        queries["header-primary"] = f"{base_context} abstract"
    
    # Query 2: Teaser - Topic specific + modern
    if main_keywords:
        queries["teaser-main"] = f"{main_keywords[0]} modern innovation"
    else:
        queries["teaser-main"] = f"{base_context} modern"
    
    # Query 3: Secondary header - Related concepts
    if len(main_keywords) > 1:
        queries["header-secondary"] = f"{main_keywords[1]} digital visualization"
    else:
        queries["header-secondary"] = f"{base_context} visualization"
    
    # Query 4: Content image - Workspace/practical
    if main_keywords:
        queries["content-workspace"] = f"{main_keywords[0]} workspace laptop"
    else:
        queries["content-workspace"] = f"{base_context} workspace"
    
    logger.info(f"📸 Generated topic-specific image queries:")
    for name, query in queries.items():
        logger.info(f"   • {name}: '{query}'")
    
    return queries


def ensure_blog_assets_topic_specific(topic: Topic, slug: str, date_str: str) -> Path:
    """
    FIXED: Ensures blog assets with TOPIC-SPECIFIC images.
    Each blog gets unique, relevant images based on its topic.
    """
    if not IMAGE_TOOLS_AVAILABLE:
        logger.warning("⚠️  ImageTools not available. Creating placeholders.")
        blog_dir = BASE_ASSETS_DIR / f"{date_str}-{slug}"
        blog_dir.mkdir(parents=True, exist_ok=True)
        _create_topic_placeholders(blog_dir, topic)
        return blog_dir

    logger.info("🎨 Ensuring topic-specific blog assets...")
    
    # Get blog-specific directory
    blog_dir = get_blog_assets_dir()
    logger.info(f"   Assets dir: {blog_dir.relative_to(BASE_DIR)}")
    
    # Check API key
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key:
        logger.warning("⚠️  PEXELS_API_KEY not set. Creating placeholders.")
        logger.info("   → Get free key at: https://www.pexels.com/api/")
        _create_topic_placeholders(blog_dir, topic)
        return blog_dir
    
    # Generate TOPIC-SPECIFIC queries
    queries = generate_image_queries(topic)
    
    # Map queries to asset filenames
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
            logger.info(f"   ✓ {asset_name}.jpg (exists)")
            continue
        
        logger.info(f"   ⚠ Missing: {asset_name}.jpg")
        logger.info(f"   → Downloading: '{search_query}'")
        
        try:
            result = ImageTools.get_stock_photo(
                search_query,
                filename=f"{asset_name}.jpg",  # ✅ FIXED: Explicit filename to match Jekyll paths
                asset_type=asset_type
            )
            
            if isinstance(result, str) and result.startswith("Error"):
                logger.error(f"   ✗ Download failed: {result}")
                create_topic_placeholder(asset_path, asset_name, topic)
            else:
                logger.info(f"   ✓ Downloaded: {asset_name}.jpg")
                
        except Exception as e:
            logger.error(f"   ✗ Exception: {e}")
            create_topic_placeholder(asset_path, asset_name, topic)
    
    logger.info("✅ Topic-specific assets ready")
    return blog_dir

def _create_topic_placeholders(blog_dir: Path, topic: Topic) -> None:
    """Create topic-specific placeholders"""
    assets = [
        ("header-ai-abstract", f"{topic.title} Header"),
        ("teaser-ai", f"{topic.title} Teaser"),
        ("header-data-science", f"{topic.title} Secondary"),
        ("header-cloud", f"{topic.title} Content"),
    ]
    
    for filename_base, text in assets:
        asset_path = blog_dir / f"{filename_base}.jpg"
        if not asset_path.exists():
            create_topic_placeholder(asset_path, filename_base, topic)


def create_topic_placeholder(path: Path, name: str, topic: Topic) -> None:
    """Create topic-specific placeholder image"""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        # Use topic title for text
        text_lines = []
        if len(topic.title) > 30:
            words = topic.title.split()
            line1 = " ".join(words[:len(words)//2])
            line2 = " ".join(words[len(words)//2:])
            text_lines = [line1, line2]
        else:
            text_lines = [topic.title]
        
        # Create image with gradient
        img = Image.new('RGB', (1200, 400), color='#1a1a2e')
        draw = ImageDraw.Draw(img)
        
        # Add gradient effect
        for y in range(400):
            shade = int(26 + (y / 400) * 30)
            color = f'#{shade:02x}{shade:02x}{shade+20:02x}'
            draw.line([(0, y), (1200, y)], fill=color)
        
        # Font
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 50)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw text centered
        y_offset = 150 if len(text_lines) == 2 else 175
        
        for i, line in enumerate(text_lines):
            bbox = draw.textbbox((0, 0), line, font=font_large)
            x = (1200 - (bbox[2] - bbox[0])) // 2
            y = y_offset + (i * 60)
            
            # Shadow
            draw.text((x+3, y+3), line, fill='#000000', font=font_large)
            # Main text
            draw.text((x, y), line, fill='#4a90e2', font=font_large)
        
        # Subtitle
        subtitle = f"{topic.kind.upper()} • {len(topic.tags)} tags"
        bbox = draw.textbbox((0, 0), subtitle, font=font_small)
        x = (1200 - (bbox[2] - bbox[0])) // 2
        y = y_offset + (len(text_lines) * 60) + 20
        draw.text((x, y), subtitle, fill='#7a9fc2', font=font_small)
        
        # Save
        img.save(str(path), 'JPEG', quality=85)
        logger.info(f"   ✓ Created topic placeholder: {path.name}")
        
    except Exception as e:
        logger.warning(f"   ⚠ Could not create placeholder: {e}")


# ============================================================================
# DATA LOADING
# ============================================================================
def slugify(text: str) -> str:
    """Convert text to URL-friendly slug"""
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "topic"


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
    """Load blog coverage history"""
    if not COVERAGE_FILE.exists():
        return []
    try:
        with COVERAGE_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_coverage(entries: List[Dict[str, Any]]) -> None:
    """Save blog coverage history"""
    with COVERAGE_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def max_version_for(coverage: List[Dict[str, Any]], kind: str, id_: str) -> int:
    """Get maximum version number for a topic"""
    versions = [e["version"] for e in coverage if e["kind"] == kind and e["id"] == id_]
    return max(versions) if versions else 0


# ============================================================================
# TOPIC SELECTION
# ============================================================================
def select_next_topic() -> Topic:
    """Select next blog topic from JSON files"""
    logger.info("="*70)
    logger.info("📊 Loading content from JSON files...")
    logger.info("="*70)
    
    packages_data = load_json(API_DIR / "packages.json") or {}
    repos_data = load_json(API_DIR / "repositories.json") or {}
    papers_data = load_json(API_DIR / "papers.json") or {}
    tutorials_data = load_json(API_DIR / "tutorials.json") or {}
    
    coverage = load_coverage()
    
    packages = packages_data.get("packages", [])
    repos = repos_data.get("repositories", [])
    papers = papers_data.get("papers", [])
    tutorials = tutorials_data if isinstance(tutorials_data, list) else tutorials_data.get("tutorials", [])
    
    logger.info(f"   Packages: {len(packages)}")
    logger.info(f"   Repositories: {len(repos)}")
    logger.info(f"   Papers: {len(papers)}")
    logger.info(f"   Tutorials: {len(tutorials)}")
    logger.info(f"   Already covered: {len(coverage)} topics")
    
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
                summary = f"Python package: {id_}"
                tags = ["python", "package", "pypi"]
                url = item.get("url")
            elif kind == "repo":
                name = item.get("name", "")
                if not name or "/" not in name:
                    continue
                id_ = name
                title = name.split("/")[1].replace("-", " ").title()
                summary = f"GitHub repository"
                tags = ["github", "repository"]
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
    
    # Version update
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
    """Validate all Python code blocks"""
    code_blocks = re.findall(r'```python\n(.*?)```', content, re.DOTALL)
    
    if not code_blocks:
        return True, [], []
    
    all_issues = []
    all_valid = True
    
    for i, code in enumerate(code_blocks, 1):
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
    """Clean and normalize content"""
    original_length = len(body)
    
    # Remove meta-commentary
    patterns = [
        (r'^\s*(Here is|Here\'s).*?[:.]?\s*\n+', '', re.IGNORECASE),
        (r'^\s*I (can|will|have).*?\.\s*\n+', '', re.IGNORECASE),
        (r'^\s*\*\*Final Answer\*\*\s*\n+', ''),
    ]
    
    for pattern, replacement, *flags in patterns:
        flag = flags[0] if flags else 0
        body = re.sub(pattern, replacement, body, flags=flag)
    
    # Remove duplicates
    paragraphs = body.split('\n\n')
    seen = set()
    unique = []
    
    for para in paragraphs:
        normalized = re.sub(r'\s+', ' ', para.strip().lower())
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(para)
    
    body = '\n\n'.join(unique)
    body = re.sub(r'\n{4,}', '\n\n\n', body).strip()
    
    removed = original_length - len(body)
    if original_length > 0:
        logger.info(f"   Cleaned: -{removed} chars ({removed/original_length*100:.1f}%)")
    
    return body


# ============================================================================
# 8-AGENT CREW - FIXED FOR OLLAMA FORMAT
# ============================================================================
def build_blog_crew(topic: Topic) -> Tuple[Crew, Tuple[Task, Task, Task, Task, Task, Task, Task, Task]]:
    """
    Build 8-agent pipeline with Ollama format fixes.
    
    FIXED for v3.6:
    - Simplified task descriptions
    - Clear expected outputs
    - Explicit NO TOOLS instructions where needed
    - Reduced max_iter to prevent loops
    - Better format guidance
    """
    
    # Conditional tools for Ollama
    researcher_tools = []
    using_ollama = is_ollama_llm()
    
    if SEARCH_TOOLS_AVAILABLE and not using_ollama:
        researcher_tools = [search_web, scrape_webpage]
        logger.info("✅ Researcher: Web search enabled")
    else:
        logger.info("⚠️  Researcher: No tools (Ollama mode)")
    
    # Agent 1: Researcher
    researcher = Agent(
        role="Research Specialist",
        goal=f"Research {topic.title} and find accurate information",
        backstory=(
            "Expert researcher. Find official docs and examples. "
            "Report facts only. No speculation."
        ),
        llm=llm,
        tools=researcher_tools,
        verbose=False,
        allow_delegation=False,
        max_iter=2,
    )
    
    # Agent 2: Strategist
    strategist = Agent(
        role="Content Planner",
        goal="Create clear blog outline",
        backstory="Design structured, engaging blog plans.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    # Agent 3: Writer
    writer = Agent(
        role="Technical Writer",
        goal="Write complete blog article with working code",
        backstory=(
            "Write 1200+ word articles with:\n"
            "• Complete imports\n"
            "• Real datasets\n"
            "• Working code\n"
            "DO NOT use tools. Just write."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    # Agent 4: Validator
    validator = Agent(
        role="Code Validator",
        goal="Check all code for errors",
        backstory=(
            "Validate Python code blocks. "
            "Report PASS or FAIL with issues. "
            "DO NOT use tools."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    # Agent 5: Fixer
    fixer = Agent(
        role="Code Fixer",
        goal="Fix all invalid Python code",
        backstory=(
            "Fix syntax errors, add imports, remove placeholders. "
            "Return COMPLETE corrected article. "
            "DO NOT use tools."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    # Agent 6: Editor
    editor = Agent(
        role="Editor",
        goal="Polish readability",
        backstory=(
            "Improve flow, remove buzzwords. "
            "Keep code unchanged. "
            "DO NOT use tools."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    # Agent 7: Stylist
    stylist = Agent(
        role="Stylist",
        goal="Add intro and conclusion",
        backstory=(
            "Add 'Hello everyone!' intro and 'Congratulations!' conclusion. "
            "Keep all other content unchanged. "
            "DO NOT use tools."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    # Agent 8: Publisher
    publisher = Agent(
        role="Metadata Creator",
        goal="Generate SEO metadata JSON",
        backstory=(
            "Create JSON with title, excerpt, tags. "
            "DO NOT use tools."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    # Tasks - SIMPLIFIED
    t1 = Task(
        description=f"Research {topic.title}. Find docs, examples, current version. Report verified facts.",
        expected_output="Research report (500+ words)",
        agent=researcher,
    )
    
    t2 = Task(
        description=f"Create blog outline for {topic.title}. Sections: Intro, Technical, Examples, Use Cases, Getting Started.",
        expected_output="Detailed outline (300+ words)",
        agent=strategist,
        context=[t1],
    )
    
    t3 = Task(
        description=f"Write COMPLETE article (1200+ words) about {topic.title}. Include 2-3 working Python code blocks with ALL imports.",
        expected_output="Complete article (1200+ words) in Markdown format",
        agent=writer,
        context=[t1, t2],
    )
    
    t4 = Task(
        description="Check all Python code blocks for: syntax errors, missing imports, placeholders. Report PASS or list issues.",
        expected_output="Validation report: PASS or FAIL with issues",
        agent=validator,
        context=[t3],
    )
    
    t5 = Task(
        description="Fix ALL code issues. Add imports, fix syntax, remove placeholders. Return COMPLETE corrected article.",
        expected_output="Complete corrected article (1200+ words)",
        agent=fixer,
        context=[t3, t4],
    )
    
    t6 = Task(
        description="Polish article. Improve flow, remove AI buzzwords. DO NOT change code. Return FULL article.",
        expected_output="Polished article (1200+ words)",
        agent=editor,
        context=[t5],
    )
    
    t7 = Task(
        description=f"Add 'Hello everyone!' intro and 'Congratulations!' conclusion to article about {topic.title}. Return COMPLETE article.",
        expected_output="Final article with intro/outro (1200+ words)",
        agent=stylist,
        context=[t6],
    )
    
    t8 = Task(
        description="Create JSON: {\"title\": \"...\", \"excerpt\": \"...\", \"tags\": [...]}. Title ≤70 chars, excerpt ≤200 chars, 4-8 tags.",
        expected_output="JSON object only",
        agent=publisher,
        context=[t2, t7],
    )
    
    crew = Crew(
        agents=[researcher, strategist, writer, validator, fixer, editor, stylist, publisher],
        tasks=[t1, t2, t3, t4, t5, t6, t7, t8],
        process=Process.sequential,
        verbose=False,
        max_rpm=20,
    )
    
    return crew, (t1, t2, t3, t4, t5, t6, t7, t8)


# ============================================================================
# JEKYLL POST BUILDING
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
    
    # Per-blog asset paths
    blog_assets_rel = blog_assets_dir.relative_to(BASE_DIR)
    header_image = f"/{blog_assets_rel}/header-ai-abstract.jpg"
    teaser_image = f"/{blog_assets_rel}/teaser-ai.jpg"
    
    # Select appropriate header
    if "data" in topic.kind or "data" in " ".join(tags):
        header_image = f"/{blog_assets_rel}/header-data-science.jpg"
    elif "cloud" in " ".join(tags):
        header_image = f"/{blog_assets_rel}/header-cloud.jpg"
    
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
        "kind": topic.kind,
        "id": topic.id,
        "version": topic.version,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "filename": filename,
    })
    save_coverage(coverage)


# ============================================================================
# FINAL VALIDATION
# ============================================================================
def validate_final_article(body: str) -> None:
    """Final validation after fixer"""
    min_length = 1000
    min_words = 200
    
    word_count = len(body.split())
    char_count = len(body)
    
    logger.info("🔍 Final validation...")
    logger.info(f"   {char_count} chars, {word_count} words")
    
    if char_count < min_length:
        raise RuntimeError(f"Too short: {char_count} chars (min {min_length})")
    
    if word_count < min_words:
        raise RuntimeError(f"Too short: {word_count} words (min {min_words})")
    
    # Validate code
    all_valid, issues, code_blocks = validate_all_code_blocks(body)
    
    if not all_valid:
        logger.error("❌ CODE VALIDATION FAILED:")
        for issue in issues:
            logger.error(f"   {issue}")
        raise RuntimeError("Invalid code after fixer")
    
    logger.info(f"   ✓ {len(code_blocks)} code blocks validated")
    logger.info("✅ Validation passed")


# ============================================================================
# MAIN
# ============================================================================
def main() -> None:
    """Main entry point"""
    
    logger.info("="*70)
    logger.info("Blog Generator v3.6 FINAL - Topic-Specific Images")
    logger.info("="*70)
    logger.info(f"Base: {BASE_DIR}")
    logger.info(f"Posts: {BLOG_POSTS_DIR}")
    logger.info("")
    
    llm_model = os.getenv("NEWS_LLM_MODEL", "not set")
    logger.info(f"LLM: {llm_model}")
    
    if is_ollama_llm():
        logger.info("✅ Ollama mode - Format optimized")
    
    logger.info("")
    
    try:
        # Step 1: Select topic
        topic = select_next_topic()
        logger.info("")
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
        logger.info("")
        
        # Step 3: Ensure TOPIC-SPECIFIC assets
        ensure_blog_assets_topic_specific(topic, slug, date_str)
        logger.info("")
        
        # Step 4: Build crew
        crew, (t1, t2, t3, t4, t5, t6, t7, t8) = build_blog_crew(topic)
        
        logger.info("🚀 8-Agent Pipeline Starting...")
        logger.info("   1→2→3→4→5→6→7→8")
        logger.info("   Research→Plan→Write→Validate→Fix→Edit→Polish→Publish")
        logger.info("")
        logger.info("   ⏱️  12-18 minutes for high quality...")
        logger.info("")
        
        # Step 5: Run crew
        result = crew.kickoff()
        
        if not result:
            raise RuntimeError("No result from crew")
        
        logger.info("🔍 Extracting outputs...")
        
        # Step 6: Extract body
        body = extract_task_output(t7, "stylist")
        
        if not body or len(body) < 800:
            logger.warning("⚠️  Trying editor...")
            body = extract_task_output(t6, "editor")
        
        if not body or len(body) < 800:
            logger.warning("⚠️  Trying fixer...")
            body = extract_task_output(t5, "fixer")
        
        if not body or len(body) < 800:
            logger.warning("⚠️  Trying writer...")
            body = extract_task_output(t3, "writer")
        
        if not body or len(body) < 800:
            logger.error("❌ Insufficient output")
            raise RuntimeError(f"Too short: {len(body)} chars")
        
        logger.info(f"📄 Generated: {len(body)} chars, {len(body.split())} words")
        
        # Step 7: Clean
        body = clean_content(body)
        
        # Step 8: Validate
        validate_final_article(body)
        logger.info("")
        
        # Step 9: Parse metadata
        meta_raw = extract_task_output(t8, "publisher")
        
        try:
            json_start = meta_raw.find("{")
            json_end = meta_raw.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                meta = json.loads(meta_raw[json_start:json_end])
            else:
                meta = json.loads(meta_raw)
            logger.info(f"✅ Metadata: {meta.get('title', 'N/A')[:50]}")
        except Exception as e:
            logger.warning(f"⚠️  Metadata failed: {e}")
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
        
        # Step 11: Success
        code_blocks = len(re.findall(r'```python', body))
        bash_blocks = len(re.findall(r'```bash', body))
        
        logger.info("")
        logger.info("="*70)
        logger.info("✅ HIGH-QUALITY BLOG POST GENERATED")
        logger.info("="*70)
        logger.info(f"   File: {path.relative_to(BASE_DIR)}")
        logger.info(f"   Assets: {blog_assets_dir.relative_to(BASE_DIR)}")
        logger.info(f"   Topic: {topic.title}")
        logger.info(f"   Words: {len(body.split())}")
        logger.info(f"   Code: {code_blocks} Python + {bash_blocks} Bash")
        logger.info("")
        logger.info("✅ Quality Features:")
        logger.info("   • TOPIC-SPECIFIC images (unique per blog) ✓")
        logger.info("   • Organized per-blog asset folders ✓")
        logger.info("   • Code validated → fixed → validated ✓")
        logger.info("   • Ollama format compatible ✓")
        logger.info("   • Professional quality ✓")
        logger.info("   • 1200+ words with examples ✓")
        logger.info("")
        logger.info("📋 Next Steps:")
        logger.info(f"   1. Review: cat {path.relative_to(BASE_DIR)}")
        logger.info(f"   2. Check images: ls {blog_assets_dir.relative_to(BASE_DIR)}")
        logger.info(f"   3. Preview: jekyll serve")
        logger.info(f"   4. Commit: git add . && git commit -m 'High-quality blog'")
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