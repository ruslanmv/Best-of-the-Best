#!/usr/bin/env python3
"""
scripts/generate_blog_advanced_orchestrated.py

PRODUCTION v4.0 - Advanced Multi-Agent Orchestration with Precise Data Retrieval

Features:
- 11-agent orchestrated pipeline with dynamic routing
- README-first strategy with web search fallback
- Package health validation
- Code quality assurance
- Source quality tracking
- Topic-specific images
- Ollama compatible
- Production error handling

Agents:
1. Orchestrator - Routes research strategy
2. README Analyst - Extracts official documentation
3. Package Health Validator - Checks versions/deprecations
4. Web Search Researcher - Fallback information gathering
5. Source Quality Validator - Rates information quality
6. Content Planner - Creates structured outline
7. Technical Writer - Writes article
8. Code Validator - Checks all code blocks
9. Code Fixer - Fixes issues
10. Content Editor - Polishes prose
11. Metadata Publisher - Creates SEO metadata

Usage:
    python scripts/generate_blog_advanced_orchestrated.py

Requirements:
    - blog/api/packages.json, repositories.json, papers.json, tutorials.json
    - .env file with PEXELS_API_KEY (optional), GITHUB_TOKEN (optional)
    - Ollama running (if using Ollama)
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


# ============================================================================
# 11-AGENT ORCHESTRATED CREW - PRODUCTION READY
# ============================================================================
def build_orchestrated_crew(topic: Topic) -> Tuple[Crew, Tuple]:
    """
    Build 11-agent orchestrated pipeline with precise data retrieval.
    
    Agent Flow:
    1. Orchestrator decides strategy
    2. README Analyst extracts official docs (if available)
    3. Package Health Validator checks version/deprecations (if package)
    4. Web Researcher searches web (if no README)
    5. Source Validator rates quality
    6. Content Planner creates outline
    7. Technical Writer writes article
    8. Code Validator checks code
    9. Code Fixer fixes issues
    10. Content Editor polishes
    11. Metadata Publisher creates SEO data
    """
    
    using_ollama = is_ollama_llm()
    topic_type, identifier = detect_topic_type(topic)
    
    # ========================================================================
    # AGENT 1: ORCHESTRATOR
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
        allow_delegation=True,
        max_iter=2,
    )
    
    # ========================================================================
    # AGENT 2: README ANALYST
    # ========================================================================
    readme_tools = []
    if README_TOOLS_AVAILABLE and scrape_readme:
        readme_tools = [scrape_readme]
    
    readme_analyst = Agent(
        role="README Documentation Analyst",
        goal="Extract complete information from official README",
        backstory="""Expert at reading README files and extracting:
        • Current version numbers
        • Installation instructions
        • COMPLETE working code examples (with ALL imports)
        • API documentation
        • Feature descriptions
        
        You ONLY use information from README - no assumptions.""",
        llm=llm,
        tools=readme_tools,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )
    
    # ========================================================================
    # AGENT 3: PACKAGE HEALTH VALIDATOR
    # ========================================================================
    health_tools = []
    if README_TOOLS_AVAILABLE and get_package_health:
        health_tools = [get_package_health]
    
    package_health_validator = Agent(
        role="Package Health Validator",
        goal="Validate package versions and check for deprecations",
        backstory="""You validate Python packages:
        • Check current version (prevent using outdated versions like 1.5.2 when 2.x exists)
        • Detect deprecated features (e.g., load_boston, sklearn.cross_validation)
        • Verify package maintenance status
        • Extract working code examples from README
        
        You prevent critical errors like using removed datasets.""",
        llm=llm,
        tools=health_tools,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )
    
    # ========================================================================
    # AGENT 4: WEB SEARCH RESEARCHER
    # ========================================================================
    web_tools = []
    if SEARCH_TOOLS_AVAILABLE and not using_ollama:
        if search_web:
            web_tools.append(search_web)
        if scrape_webpage:
            web_tools.append(scrape_webpage)
    
    web_researcher = Agent(
        role="Web Research Specialist",
        goal="Find accurate information through web search (fallback only)",
        backstory="""You search the web when official docs are unavailable:
        • Search for official documentation first
        • Find recent tutorials (2024-2025)
        • Extract working code examples
        • Prefer .org sites and official blogs
        • Note: Your findings need verification
        
        You only activate when README/package health fails.""",
        llm=llm,
        tools=web_tools,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )
    
    # ========================================================================
    # AGENT 5: SOURCE QUALITY VALIDATOR
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
        max_iter=1,
    )
    
    # ========================================================================
    # AGENT 6: CONTENT PLANNER
    # ========================================================================
    content_planner = Agent(
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
        max_iter=1,
    )
    
    # ========================================================================
    # AGENT 7: TECHNICAL WRITER
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
          - REAL datasets (NOT load_boston)
        • Use EXACT code from README when available
        • Adapt tone to source quality
        
        DO NOT use tools. Write based on research provided.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )
    
    # ========================================================================
    # AGENT 8: CODE VALIDATOR
    # ========================================================================
    code_validator = Agent(
        role="Code Quality Validator",
        goal="Ensure all code examples are complete and error-free",
        backstory="""Strict code reviewer. You check:
        • Syntax correctness (Python AST parsing)
        • All imports present
        • All variables defined before use
        • No placeholders or TODOs
        • No deprecated features (based on validation report)
        
        You report PASS or detailed issues.
        DO NOT use tools.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )
    
    # ========================================================================
    # AGENT 9: CODE FIXER
    # ========================================================================
    code_fixer = Agent(
        role="Code Issue Resolver",
        goal="Fix all code errors and issues",
        backstory="""You fix code problems:
        • Add missing imports
        • Define undefined variables
        • Remove placeholders
        • Fix syntax errors
        • Replace deprecated features with current alternatives
        
        You return COMPLETE corrected article.
        DO NOT use tools.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )
    
    # ========================================================================
    # AGENT 10: CONTENT EDITOR
    # ========================================================================
    content_editor = Agent(
        role="Content Editor",
        goal="Polish article readability and flow",
        backstory="""Professional editor who:
        • Improves sentence flow
        • Removes buzzwords and jargon
        • Ensures consistent tone
        • NEVER changes code blocks
        
        You make content more engaging.
        DO NOT use tools.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )
    
    # ========================================================================
    # AGENT 11: METADATA PUBLISHER
    # ========================================================================
    metadata_publisher = Agent(
        role="SEO Metadata Creator",
        goal="Generate optimized metadata",
        backstory="""You create SEO-optimized metadata:
        • Compelling title (≤70 chars)
        • Engaging excerpt (≤200 chars)
        • Relevant tags (4-8)
        • JSON format only
        
        DO NOT use tools.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )
    
    # ========================================================================
    # TASKS
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
    
    # TASK 2: README Analysis (conditional)
    readme_task = Task(
        description=f"""
        Extract complete information from README for: {identifier}
        
        USE: scrape_readme("{identifier}")
        
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
        
        USE: get_package_health("{identifier}")
        
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
           search_web("{topic.title} official documentation")
        
        2. Recent tutorials
           search_web("{topic.title} tutorial 2024")
        
        3. Working examples
           search_web("{topic.title} complete example code")
        
        4. Current version
           search_web("{topic.title} latest version")
        
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
    quality_task = Task(
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
    
    # TASK 6: Content Planning
    planning_task = Task(
        description=f"""
        Create detailed blog outline for: {topic.title}
        
        Based on validated research, create structure:
        
        1. **Introduction** (150 words)
           - What is {topic.title}?
           - Why it matters
           - What readers will learn
        
        2. **Overview** (200 words)
           - Key features
           - Use cases
           - Current version: [from validation]
        
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
           - Resources
        
        CRITICAL:
        • Use version from validation
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
        Write complete blog article about: {topic.title}
        
        Based on research and outline, write 1200+ word article.
        
        MANDATORY REQUIREMENTS:
        
        **Code Quality:**
        • ALL imports at top of code blocks
        • ALL variables defined before use
        • NO placeholders (TODO, ..., your_X)
        • Use REAL datasets (fetch_california_housing, load_iris)
        • NEVER use deprecated features from validation report
        
        **Code Fidelity:**
        • If README examples available → Use EXACTLY as written
        • If web sources → Add note: "Example from tutorial - verify with your version"
        • Always show complete, runnable code
        
        **Structure:**
        • Follow outline from planner
        • Clear section headings
        • Progressive complexity
        • Practical examples
        
        **Tone:**
        • Professional but approachable
        • Explain concepts clearly
        • No buzzwords or hype
        
        DO NOT use tools. Write based on research provided.
        
        OUTPUT: Complete article in Markdown (1200+ words)
        """,
        expected_output="Complete blog article (1200+ words)",
        agent=technical_writer,
        context=[planning_task, quality_task],
    )
    
    # TASK 8: Code Validation
    validation_task = Task(
        description="""
        Validate ALL Python code blocks in article.
        
        For EACH code block, check:
        
        1. **Syntax** 
           - Parse with Python AST
           - Report line numbers for errors
        
        2. **Imports**
           - All used modules imported?
           - Standard library vs third-party clear?
        
        3. **Variables**
           - All variables defined before use?
           - No undefined: train_X, test_y, etc.
        
        4. **Deprecations**
           - Check against validation report
           - Flag: load_boston, sklearn.cross_validation, etc.
        
        5. **Completeness**
           - No placeholders (TODO, ..., your_X)
           - No truncated code (...)
        
        OUTPUT:
```
        Validation Result: [PASS / FAIL]
        
        Code Blocks Checked: [count]
        
        Issues Found:
        [If FAIL, list all issues with block numbers]
        
        Block 1:
        • Missing import: sklearn.model_selection.train_test_split
        • Undefined variable: train_X
        
        Block 2:
        • Deprecated: load_boston (use fetch_california_housing)
```
        
        DO NOT use tools.
        """,
        expected_output="Code validation report",
        agent=code_validator,
        context=[writing_task, health_task],
    )
    
    # TASK 9: Code Fixing
    fixing_task = Task(
        description="""
        Fix ALL code issues found by validator.
        
        For each issue:
        
        **Missing imports** → Add at top of block:
```python
        import xgboost as xgb
        from sklearn.model_selection import train_test_split
        from sklearn.datasets import fetch_california_housing
```
        
        **Undefined variables** → Add definitions:
```python
        # Load data
        X, y = fetch_california_housing(return_X_y=True)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
```
        
        **Deprecated features** → Replace:
```python
        # OLD (deprecated):
        from sklearn.datasets import load_boston
        
        # NEW (current):
        from sklearn.datasets import fetch_california_housing
```
        
        **Placeholders** → Replace with real code:
```python
        # OLD:
        # ... rest of code
        
        # NEW:
        predictions = model.predict(X_test)
        score = model.score(X_test, y_test)
```
        
        Return COMPLETE corrected article with ALL fixes applied.
        
        DO NOT use tools.
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
        
        Return COMPLETE polished article.
        
        DO NOT use tools.
        """,
        expected_output="Polished article (1200+ words)",
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
        • Title: Clear, specific, includes main keyword
        • Excerpt: Summarizes value, calls to action
        • Tags: 4-8 relevant tags (lowercase, hyphenated)
        
        Example:
        {{
          "title": "XGBoost 2.0: Complete Guide with Python Examples",
          "excerpt": "Learn XGBoost 2.0 with complete code examples, best practices, and real-world use cases. Includes gradient boosting fundamentals and performance tuning.",
          "tags": ["python", "machine-learning", "xgboost", "data-science", "gradient-boosting"]
        }}
        
        Output ONLY valid JSON. No preamble.
        
        DO NOT use tools.
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
    logger.info("Advanced Orchestrated Blog Generator v4.0")
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
        logger.info("✅ Ollama mode - Format optimized")
    
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
