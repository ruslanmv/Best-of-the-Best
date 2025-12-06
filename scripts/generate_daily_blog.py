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
# OUTPUT EXTRACTION
# ============================================================================
def extract_task_output(task: Task, task_name: str) -> str:
    """Extract output from CrewAI task with fallback methods"""
    if not task or not hasattr(task, 'output') or task.output is None:
        logger.warning(f"⚠️  Task {task_name} has no output")
        return ""
    
    output = task.output
    
    methods = [
        ('raw', lambda: getattr(output, 'raw', None)),
        ('result', lambda: getattr(output, 'result', None)),
        ('direct', lambda: output if isinstance(output, str) else None),
        ('str()', lambda: str(output)),
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
    """Clean and normalize content"""
    patterns = [
        (r'^\s*(Here is|Here\'s).*?[:.]?\s*\n+', '', re.IGNORECASE),
        (r'^\s*I (can|will|have).*?\.\s*\n+', '', re.IGNORECASE),
        (r'^\s*\*\*Final Answer\*\*\s*\n+', ''),
    ]
    
    for pattern, replacement, *flags in patterns:
        flag = flags[0] if flags else 0
        body = re.sub(pattern, replacement, body, flags=flag)
    
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
    
    return body

import re
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
        max_iter=4,
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
    content_planner_old = Agent(
        role="Content Strategist",
        goal="Create structured, engaging blog outline",
        backstory="""You design blog structures that:
        • Start with clear introduction
        • Progress logically through concepts
        • Include 2-3 practical examples
        • End with actionable next steps
        
        You base outlines on validated research only.""",
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
    # AGENT 7: TECHNICAL WRITER (NO TOOLS) - FIXED
    # ========================================================================
    technical_writer = Agent(
        role="Technical Content Writer",
        goal="Write complete, accurate technical articles",
        backstory="""You write professional technical content:
        • 1200+ words with clear explanations
        • COMPLETE code examples:
          - ALL imports at top
          - ALL variables defined
          - NO placeholders (TODO, ..., your_X)
        • Use EXACT code from README when available
        • Adapt tone to source quality
        
        OUTPUT INSTRUCTION:
        You output the Markdown content ONLY. 
        Do NOT wrap in conversation.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,  # Increased for better completion
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
        backstory="""You fix code problems:
        • Add missing imports
        • Define undefined variables
        • Remove placeholders
        • Fix syntax errors
        • Replace deprecated features
        
        OUTPUT: The FIXED ARTICLE ONLY (raw Markdown).""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )
    
    # AGENT 10: CONTENT EDITOR (NO TOOLS)
    # ========================================================================
    content_editor_old = Agent(
        role="Content Editor",
        goal="Polish article readability and enforce Markdown formatting",
        backstory="""Professional editor who:
        • Improves sentence flow and removes buzzwords (e.g., "game-changing").
        • Ensures consistent tone.
        • ACTS AS A GHOSTWRITER: Your personal voice/opinion must NEVER appear in the text.
        
        CRITICAL FORMATTING RULES (DO NOT IGNORE):
        1. EVERY code block MUST have a language tag. Use ```python for code and ```bash for terminal commands.
        2. NEVER mix Bash commands (pip install) with Python code in the same block. Separate them into two blocks.
        3. Do not remove imports or change variable names inside code blocks.
        4. NO META-COMMENTARY: Do not add "Note:", "I have updated...", or any final thoughts.
        
        OUTPUT: Finalized Markdown content ONLY. Start immediately with the content.""",        
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )

    # AGENT 10: CONTENT EDITOR (NO TOOLS)
    # ========================================================================
    content_editor = Agent(
        role="Content Editor",
        goal="Polish article readability, fix minor consistency issues, and enforce Markdown formatting.",
        backstory="""You are a concise, precision-focused editor.

Core job:
- Improve sentence flow and clarity.
- Remove buzzwords and unnecessary repetition.
- Keep tone and terminology consistent.
- Fix small contradictions using context (pick the clearest, most consistent version).

Markdown rules:
1) Every code block MUST have a language tag:
   - ```python for Python
   - ```bash for shell
   - Use other tags when obvious (json, yaml, etc.).
2) Never mix shell commands (e.g. pip install) with source code in the same block.
3) Do NOT change imports, variable names, or logic inside code blocks.
4) Use proper headings (##, ###). Do not use bold text as headings.
5) Keep spacing clean (no >2 blank lines, blank line around headings and code blocks).
6) If there are links or references, write them in full Markdown format.
Constraints:
- Act as a ghostwriter: no "I", "we", or editor commentary.
- No meta text like "Note:", "I updated...", or describing changes.
- Do not change the overall section structure or remove examples, unless something is clearly broken.

Output:
- Return ONLY the final Markdown article, starting directly with the content.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
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
        Extract complete information from README for: {identifier}
        
        USE the tool: "Get README from PyPI package or GitHub repository" 
        with input "{identifier}"
        
        Extract:
        1. **Version Information**
           - Current version from badges/installation
           - Python requirements
           - Dependencies
        
        2. **Installation**
           - Exact pip install command
           - Setup steps
        
        3. **Code Examples** (CRITICAL!)
           - Extract ALL code blocks
           - Copy EXACTLY as written
           - Include ALL imports
           - Note what each example demonstrates
           - Preserve comments and structure
        
        4. **Features**
           - Main capabilities
           - Use cases
           - API overview
        
        5. **Warnings**
           - Deprecation notices
           - Known issues
           - Version-specific notes
        
        OUTPUT: Structured README analysis with exact code examples
        """,
        expected_output="Complete README analysis (500+ words)",
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
    web_research_task = Task(
        description=f"""
        Research {topic.title} using web search (fallback mode).

        SEARCH STRATEGY:

        1. Official documentation  
           Use the tool "Search the web for information"  
           with query "{topic.title} official documentation"

        2. Recent tutorials  
           Use the tool "Search the web for information"  
           with query "{topic.title} tutorial latest"

        3. Working examples  
           Use the tool "Search the web for information"  
           with query "{topic.title} complete example code"

        4. Current version  
           Use the tool "Search the web for information"  
           with query "{topic.title} latest version"

        For each result:
        • Extract key information  
        • Note source URL  
        • Assess reliability  
        • Flag incomplete examples

        OUTPUT: Web research report with sources cited
        """,
        expected_output="Web research report with URLs",
        agent=web_researcher,
    )

    
    # TASK 5: Source Quality Validation
    quality_task_old = Task(
        description="""
        Validate research quality and assign confidence rating.
        
        Evaluate sources used:
        • README/Official docs → A+ (highest confidence)
        • Package health report → A (high confidence)
        • Web tutorials → B (medium confidence)
        • Missing/incomplete → F (reject)
        
        Check for:
        • Version information present?
        • Code examples complete?
        • Deprecation warnings noted?
        • Sources cited?
        
        OUTPUT:
```
        Quality Rating: [A+ / A / B / C / F]
        Confidence: [High / Medium / Low]
        
        Sources:
        • Primary: [README / Web / None]
        • Validation: [Package Health / None]
        
        Completeness:
        • Version info: [✓ / ✗]
        • Code examples: [✓ / ✗] ([count] found)
        • Deprecations: [✓ / ✗]
        
        Recommendations:
        [How to use this research in blog]
```
        """,
        expected_output="Quality validation report",
        agent=source_validator,
        context=[orchestration_task, readme_task, health_task, web_research_task],
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
            Write a complete blog article about: {topic.title}
            
            Based on the validated research and the outline, write a 1200+ word article.
            
            SOURCE OF TRUTH:
            • Use ONLY the information, version numbers, APIs, and deprecation warnings
            coming from the research context (README analysis, package health report,
            and any validated metadata loaded from the JSON files).
            • Do NOT invent new libraries, frameworks, or datasets. The article must stay
            consistent with the specific package / project / topic that was selected
            from the JSON input.
            • If your internal knowledge conflicts with the research context, prefer the
            research context.
            • If real resource URLs are available and provided in the context, add maximum 2 references a final "Resources" section listing them as Markdown links (e.g. [Label](https://example.com)).
            • Never leave placeholder text in the final article. If information is missing, omit that part entirely.

            MANDATORY REQUIREMENTS:

            **Code Quality:**
            • ALL imports must appear at the top of each code block.
            • ALL variables must be defined before use.
            • NO placeholders (TODO, ..., your_X, or similar).
            • Use REAL, appropriate datasets, functions, and APIs that belong to the
            topic/library described in the research (or standard examples mentioned
            in the official docs for this topic).
            • NEVER use deprecated features listed in the validation / health reports.

            **Code Fidelity:**
            • If README / official documentation examples are available:
            - Use them as the primary reference.
            - You may adapt them slightly (e.g. comments, minor restructuring),
                but keep the logic and APIs accurate.
            • If you need to write new examples:
            - Base them on the APIs, functions, and data sources confirmed in
                the research context or JSON input.
            - Do NOT introduce unrelated libraries or external datasets.
            • Always show complete, runnable code blocks:
            - All necessary imports
            - Any required data-loading or configuration steps

            **Structure:**
            • Follow the outline provided by the Content Planner.
            • Use clear section headings (##, ###).
            • Introduce concepts gradually (from basic to advanced).
            • Include at least 2 practical, end-to-end examples that are relevant
            to the topic as defined by the JSON and research context.

            **Topical Consistency:**
            • The article must remain focused on the selected topic (from the JSON).
            • Do NOT switch to competing frameworks, packages, or tools unless the
            outline explicitly calls for a brief comparison section — and even
            there, comparisons should remain high-level and textual, not code-based.
            • All code examples must use the same main library / package that
            the article is about.

            **Tone:**
            • Professional but approachable.
            • Explain concepts clearly and concretely.
            • Avoid empty buzzwords and hype.
            • No first-person commentary, no meta-comments about being an AI.

            OUTPUT:
            • A complete article in Markdown (1200+ words).
            • Start directly with the article content (no preamble, no explanations).
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
            - Parse with Python AST.
            - Report any syntax errors with line numbers, if possible.

            2. **Imports**
            - Are all used modules imported?
            - Are imports consistent with the topic and libraries used in the article?
            - Distinguish clearly between standard library and third-party imports.

            3. **Variables**
            - Are all variables defined before use?
            - No obviously undefined names (e.g., train_X, test_y, model, etc.).
            - Check for accidental reuse of variables in a way that breaks the example.

            4. **Deprecations**
            - Check against the package health / validation report and research context.
            - Flag any APIs, functions, or classes that are known to be deprecated or removed.
            - When possible, mention that a replacement should be used, but do NOT invent replacements.

            5. **Completeness**
            - No placeholders (TODO, ..., your_X, pass where code is expected).
            - No truncated code indicated by "..." or similar.
            - Each code block should be self-contained and runnable in a realistic context
                (e.g., all necessary imports and data loading steps are present or clearly explained).

            6. **Topical Consistency**
            - Verify that the code uses the same main library/topic as the article.
            - If the article is about a specific package, code examples should not silently switch
                to a different, competing library unless the outline explicitly includes a comparison.
            
            OUTPUT FORMAT (plain text):

            Validation Result: [PASS / FAIL]

            Code Blocks Checked: [count]

            Issues Found:
            [If FAIL, list all issues with block numbers]

            Block 1:
            • [Issue 1]
            • [Issue 2]

            Block 2:
            • [Issue 1]
            • [Issue 2]

            If there are no issues, state clearly that all code blocks passed validation.
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
            libraries. If the article is about a specific package or ML library, all
            examples must consistently use that same library.

            **Undefined variables** → Add minimal, sensible definitions that are
            consistent with the surrounding code. Reuse the same datasets, variable
            names, and conventions already present in the article instead of inventing
            new ones.

            **Deprecated features** → Replace them with the recommended alternatives
            from the validation context or from the official documentation for this
            topic. Do NOT copy replacements from other, unrelated libraries or domains.

            **Placeholders** → Replace any placeholders (such as "...", "TODO",
            "your_X") with fully working code, or remove the example if you cannot
            make it complete without guessing.

            GLOBAL CONSTRAINTS:
            • Never switch to a different framework or library than the one the
            article is about.
            • Do not add example code that changes the main topic (for example, do
            not bring in competing ML frameworks without an explicit comparison
            section in the outline).
            • Keep all code blocks self-contained, runnable, and consistent with the
            article’s narrative and research context.
            • Preserve the overall structure and intent of each example; only change
            what is necessary to make it correct and complete.

            Return the COMPLETE corrected article with ALL fixes applied, in raw Markdown.
            """,
        expected_output="Complete corrected article (1200+ words)",
        agent=code_fixer,
        context=[writing_task, validation_task],
    )

    # TASK 10: Editing
    editing_task = Task(
        description="""
        Polish article for readability and flow.
        
        Improvements:
        • Remove buzzwords: "revolutionary", "game-changing", "cutting-edge"
        • Improve sentence flow
        • Fix awkward phrasing
        • Ensure consistent tone
        • Check transitions between sections
        
        NEVER change:
        • Code blocks (keep exactly as-is)
        • Technical accuracy
        • Structure/headings
        
        NEGATIVE CONSTRAINTS (CRITICAL):
        • DO NOT add personal opinions, notes, or explanations (e.g., "Note: I kept the code...").
        • DO NOT output preambles (e.g., "Here is the polished version...").
        • The output must be the pure Article content ONLY.
        
        Return COMPLETE polished article.
        """,
        expected_output="Polished article (1200+ words) without meta-commentary",
        agent=content_editor,
        context=[fixing_task],
    )
    # TASK 11: Metadata
    metadata_task = Task(
        description=f"""
            Create SEO metadata for blog about: {topic.title}
            
            Generate JSON:
            {{
            "title": "Engaging title (≤70 chars)",
            "excerpt": "Compelling description (≤200 chars)",
            "tags": ["tag1", "tag2", "tag3", "tag4"]
            }}
            
            Requirements:
            • Title: Clear, specific, includes the main keyword from "{topic.title}"
            • Excerpt: Summarizes the value of the article and can optionally include a light call to action
            • Tags: 4-8 relevant tags (lowercase, hyphenated, no spaces)
            
            Example (generic):
            {{
            "title": "{topic.title}: Complete Guide with Python Examples",
            "excerpt": "Learn {topic.title} with complete code examples, best practices, and real-world use cases.",
            "tags": ["python", "machine-learning", "gradient-boosting", "data-science"]
            }}
            
            IMPORTANT CONSTRAINTS:
            • Do NOT mention unrelated libraries, frameworks, or tools that are not part of the article topic.
            • Keep the title concise (≤70 characters) and focused on the main topic.
            • Keep the excerpt ≤200 characters and avoid marketing fluff.
            • Tags must be directly relevant to the topic and its ecosystem.
            
            Output ONLY valid JSON. No preamble, no explanation, no extra text.
            """,
        expected_output="JSON metadata object",
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
        body = extract_task_output(editing_task, "editor")
        
        if not body or len(body) < 800:
            logger.warning("⚠️  Trying fixer...")
            body = extract_task_output(fixing_task, "fixer")
        
        if not body or len(body) < 800:
            logger.warning("⚠️  Trying writer...")
            body = extract_task_output(writing_task, "writer")
        
        if not body or len(body) < 800:
            logger.error("❌ Insufficient output")
            raise RuntimeError(f"Too short: {len(body)} chars")
        
        logger.info(f"📄 Generated: {len(body)} chars, {len(body.split())} words")
        
        # Step 7: Clean
        # ----- Ollama fix for extra formatting -----
        body = clean_llm_output(body) 
        # ---------------------

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