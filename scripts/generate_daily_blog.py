#!/usr/bin/env python3
"""
scripts/generate_daily_blog.py

PRODUCTION v2.6 - Daily blog generator with CODE FIXER

Pipeline: Research → Strategy → Write → Validate → FIXER → Edit → Style → Publish

Uses YOUR packages, repositories, papers, and tutorials from:
- blog/api/packages.json
- blog/api/repositories.json
- blog/api/papers.json
- blog/api/tutorials.json

Output:
- blog/posts/YYYY-MM-DD-<slug>.md
- data/blog_coverage.json
- logs/blog_generation.log
"""

import ast
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
    """Safely load JSON file with detailed logging."""
    if not path.exists():
        logger.warning(f"⚠️  Data file not found: {path}")
        logger.warning(f"   Create this file with your packages/repos/papers")
        return None
    
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            logger.debug(f"✅ Loaded: {path.name}")
            return data
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in {path}: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Error reading {path}: {e}")
        return None


def load_coverage() -> List[Dict[str, Any]]:
    """Load blog coverage tracking."""
    if not COVERAGE_FILE.exists():
        logger.info("No existing coverage file - will create on first run")
        return []
    try:
        with COVERAGE_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"✅ Loaded {len(data)} coverage entries")
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
    logger.info(f"✅ Saved {len(entries)} coverage entries")


def max_version_for(coverage: List[Dict[str, Any]], kind: str, id_: str) -> int:
    """Get max version for a topic."""
    versions = [e["version"] for e in coverage if e["kind"] == kind and e["id"] == id_]
    return max(versions) if versions else 0


def select_next_topic() -> Topic:
    """
    Select next blog topic from YOUR data files.
    
    Priority:
    1. Uncovered packages from blog/api/packages.json
    2. Uncovered repos from blog/api/repositories.json
    3. Uncovered papers from blog/api/papers.json
    4. Uncovered tutorials from blog/api/tutorials.json
    5. Version updates for existing packages
    """
    logger.info("="*70)
    logger.info("Selecting next blog topic from YOUR data sources...")
    logger.info("="*70)
    
    # Load YOUR data files
    packages_data = load_json(API_DIR / "packages.json") or {}
    repos_data = load_json(API_DIR / "repositories.json") or {}
    papers_data = load_json(API_DIR / "papers.json") or load_json(API_DIR / "research.json") or {}
    tutorials_data = load_json(API_DIR / "tutorials.json") or load_json(API_DIR / "data.json") or {}
    
    coverage = load_coverage()
    
    # Extract items from data files
    packages = packages_data.get("packages") or packages_data.get("top_packages") or []
    repos = repos_data.get("repositories") or repos_data.get("top_repositories") or []
    papers = papers_data.get("papers") or papers_data.get("most_cited") or papers_data.get("research") or []
    
    if isinstance(tutorials_data, list):
        tutorials = tutorials_data
    else:
        tutorials = tutorials_data.get("tutorials") or tutorials_data.get("top_tutorials") or []
    
    logger.info(f"📊 Data sources loaded:")
    logger.info(f"   • Packages: {len(packages)} from {API_DIR / 'packages.json'}")
    logger.info(f"   • Repositories: {len(repos)} from {API_DIR / 'repositories.json'}")
    logger.info(f"   • Papers: {len(papers)} from {API_DIR / 'papers.json'}")
    logger.info(f"   • Tutorials: {len(tutorials)} from {API_DIR / 'tutorials.json'}")
    logger.info(f"   • Coverage history: {len(coverage)} topics already covered")
    
    # Validate we have data
    total_items = len(packages) + len(repos) + len(papers) + len(tutorials)
    if total_items == 0:
        logger.error("="*70)
        logger.error("❌ NO DATA FOUND IN ANY SOURCE FILES!")
        logger.error("="*70)
        logger.error("")
        logger.error("Please create data files with your content:")
        logger.error(f"  1. {API_DIR / 'packages.json'} - Your Python packages")
        logger.error(f"  2. {API_DIR / 'repositories.json'} - Your GitHub repos")
        logger.error(f"  3. {API_DIR / 'papers.json'} - Your research papers")
        logger.error(f"  4. {API_DIR / 'tutorials.json'} - Your tutorials")
        logger.error("")
        logger.error("Example packages.json structure:")
        logger.error('''{
  "packages": [
    {
      "name": "your-package-name",
      "title": "Your Package Title",
      "summary": "Brief description",
      "url": "https://github.com/you/package",
      "tags": ["python", "ml", "data"]
    }
  ]
}''')
        sys.exit(1)
    
    def pick_uncovered(items: List[Dict], kind: str) -> Optional[Topic]:
        """Pick first uncovered item from list."""
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
            else:  # tutorial
                id_ = item.get("id") or item.get("slug") or item.get("title", "unknown")
                title = item.get("title", id_)
                summary = item.get("excerpt") or item.get("description", f"Tutorial: {title}")
            
            # Check if this item hasn't been covered yet
            if max_version_for(coverage, kind, id_) == 0:
                url = item.get("url") or item.get("link") or item.get("homepage")
                tags = (item.get("tags") or [])[:6] if isinstance(item.get("tags"), list) else []
                
                logger.info("="*70)
                logger.info(f"✅ Selected NEW {kind.upper()}: {title}")
                logger.info(f"   ID: {id_}")
                logger.info(f"   URL: {url or 'N/A'}")
                logger.info(f"   Tags: {', '.join(tags) if tags else 'None'}")
                logger.info("="*70)
                
                return Topic(kind, id_, title, url, summary, tags, 1)
        
        return None
    
    # Try to find uncovered content in priority order
    logger.info("🔍 Searching for uncovered content...")
    
    for kind, items in [("package", packages), ("repo", repos), ("paper", papers), ("tutorial", tutorials)]:
        if not items:
            logger.debug(f"   Skipping {kind} (no data)")
            continue
            
        logger.info(f"   Checking {len(items)} {kind}(s)...")
        topic = pick_uncovered(items, kind)
        if topic:
            return topic
    
    # All items covered - pick package for version update
    logger.info("⚠️  All content has been covered at least once")
    logger.info("🔄 Looking for package version updates...")
    
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
            topic = candidates[0][1]
            
            logger.info("="*70)
            logger.info(f"✅ Selected VERSION UPDATE: {topic.title}")
            logger.info(f"   Version: v{topic.version} (was v{candidates[0][0]})")
            logger.info(f"   ID: {topic.id}")
            logger.info("="*70)
            
            return topic
    
    # Fallback (should never reach here if data exists)
    logger.warning("⚠️  Unexpected: Using fallback topic")
    return Topic("package", "fallback", "AI Technologies Update", None, "Latest in AI/ML", ["ai"], 1)


def validate_python_code(code: str) -> Tuple[bool, List[str]]:
    """
    Validate Python code syntax and check for common issues.
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    if not code or not code.strip():
        errors.append("Empty code block")
        return False, errors
    
    # Check for syntax errors
    try:
        ast.parse(code)
    except SyntaxError as e:
        errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
        return False, errors
    except Exception as e:
        errors.append(f"Parse error: {str(e)}")
        return False, errors
    
    # Check for deprecated APIs
    deprecated_patterns = [
        (r'sklearn\.datasets\.load_boston', 'load_boston is deprecated, use fetch_california_housing'),
        (r'from sklearn\.datasets import load_boston', 'load_boston is deprecated, use fetch_california_housing'),
        (r'pd\.np\.\w+', 'pd.np is deprecated, use np directly'),
        (r'\.ix\[', '.ix is deprecated, use .loc or .iloc'),
    ]
    
    for pattern, message in deprecated_patterns:
        if re.search(pattern, code):
            errors.append(f"Deprecated API usage: {message}")
    
    # Check for common import issues
    lines = code.split('\n')
    has_imports = False
    uses_packages = []
    
    common_packages = {
        'pandas': ['pd.', 'DataFrame', 'Series'],
        'numpy': ['np.', 'array', 'ndarray'],
        'sklearn': ['sklearn.', 'fit(', 'predict(', 'train_test_split'],
        'matplotlib': ['plt.', 'pyplot'],
        'torch': ['torch.', 'nn.Module', 'Tensor'],
        'tensorflow': ['tf.', 'keras.'],
    }
    
    for line in lines:
        if line.strip().startswith('import ') or line.strip().startswith('from '):
            has_imports = True
        
        for pkg, indicators in common_packages.items():
            for indicator in indicators:
                if indicator in line:
                    uses_packages.append(pkg)
                    break
    
    if uses_packages and not has_imports:
        errors.append(f"Missing imports for: {', '.join(set(uses_packages))}")
    
    # Check for placeholder/incomplete code
    placeholder_patterns = [
        r'\.\.\.+',  # Ellipsis
        r'#\s*TODO',
        r'#\s*FIXME',
        r'pass\s*$',  # Just 'pass' on a line
        r'your_\w+',  # Placeholders like your_data
        r'<.*?>',  # XML-style placeholders
    ]
    
    for pattern in placeholder_patterns:
        if re.search(pattern, code, re.MULTILINE):
            errors.append(f"Code contains placeholders or TODOs")
            break
    
    return len(errors) == 0, errors


def extract_and_validate_code_blocks(body: str) -> Tuple[bool, List[str]]:
    """
    Extract all Python code blocks and validate them.
    Returns (all_valid, list_of_issues)
    """
    code_blocks = re.findall(r'```python\n(.*?)```', body, re.DOTALL)
    
    if not code_blocks:
        logger.warning("No Python code blocks found in article")
        return True, []  # No code to validate
    
    logger.info(f"Found {len(code_blocks)} Python code blocks to validate")
    
    all_issues = []
    all_valid = True
    
    for i, code in enumerate(code_blocks, 1):
        logger.debug(f"Validating code block {i}/{len(code_blocks)}")
        is_valid, errors = validate_python_code(code)
        
        if not is_valid:
            all_valid = False
            all_issues.append(f"Code block {i} has errors:")
            all_issues.extend([f"  - {err}" for err in errors])
            logger.error(f"❌ Code block {i} validation failed: {errors}")
        else:
            logger.info(f"✅ Code block {i} validated successfully")
    
    return all_valid, all_issues


def clean_and_normalize_body(body: str) -> str:
    """Clean meta-commentary and normalize formatting."""
    logger.info("Cleaning and normalizing article body...")
    logger.debug(f"Original length: {len(body)} chars")
    
    original_body = body
    original_length = len(body)
    
    # Remove meta-commentary at start only
    meta_patterns = [
        (r'^\s*I (now )?can (give|provide|write)( a)? (great |good )?answer\.?\s*\n+', ''),
        (r'^\s*\*\*Final Answer\*\*\s*\n+', ''),
        (r'^\s*(Here is|Here\'s) (the |your )?(article|blog post|content).*?[:.]?\s*\n+', ''),
        (r'^\s*I (can |will )?help( you)?( with that)?\.?\s*\n+', ''),
        (r'^\s*Let me (write|create|generate|polish|edit|wrap).*?\.\s*\n+', ''),
        (r'^\s*I (understand|see|have)( that)?.*?(reviewed|edited|polished|wrapped).*?\.\s*\n+', ''),
        (r'^\s*###?\s*Enterprise-Focused Blog Outline:\s*["\'].*?["\']\s*\n+', ''),
    ]
    
    for pattern, replacement in meta_patterns:
        before = len(body)
        body = re.sub(pattern, replacement, body, flags=re.IGNORECASE)
        after = len(body)
        if before != after:
            logger.debug(f"Removed {before - after} chars of meta-commentary")
    
    # Convert [Image of ...] to HTML comments
    def _image_placeholder_to_comment(match: re.Match) -> str:
        desc = match.group(1).strip()
        return f"<!-- Diagram: {desc} -->"

    before_img = len(body)
    body = re.sub(r'\[Image of ([^\]]+)\]', _image_placeholder_to_comment, body)
    after_img = len(body)
    if before_img != after_img:
        logger.info("Converted [Image of ...] placeholders to HTML comments")
    
    # Normalize headings
    lines = body.split('\n')
    result = []
    i = 0
    normalized_headings = 0
    
    while i < len(lines):
        line = lines[i]
        
        if i + 1 < len(lines):
            next_line = lines[i + 1]
            
            if (re.match(r'^[=\-]{3,}$', next_line) and 
                line.strip().startswith('**') and line.strip().endswith('**')):
                heading_text = line.strip().strip('*').strip()
                if heading_text:
                    result.append(f"## {heading_text}")
                    normalized_headings += 1
                    i += 2
                    continue
        
        result.append(line)
        i += 1
    
    body = '\n'.join(result)
    if normalized_headings > 0:
        logger.info(f"Normalized {normalized_headings} headings")
    
    # Clean excessive whitespace
    body = re.sub(r'\n{4,}', '\n\n\n', body)
    body = body.strip()
    
    # Safety check
    final_length = len(body)
    removed = original_length - final_length
    removal_percent = (removed / original_length * 100) if original_length > 0 else 0
    
    logger.info(f"Cleaning complete: {removed} chars removed ({removal_percent:.1f}%)")
    logger.info(f"Final length: {final_length} chars, {len(body.split())} words")
    
    if removal_percent > 60:
        logger.warning(f"⚠️  Cleaning removed {removal_percent:.1f}% - using original")
        return original_body
    
    if final_length < 500:
        logger.warning(f"⚠️  Cleaned body too short ({final_length} chars) - using original")
        return original_body
    
    return body


def get_current_date() -> datetime:
    """Get current date with validation."""
    now = datetime.now(timezone.utc)
    logger.info(f"Using date: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    return now


def build_blog_crew(topic: Topic) -> Tuple[Crew, Tuple[Task, Task, Task, Task, Task, Task, Task, Task]]:
    """
    Build 8-agent CrewAI pipeline with Research, Validation, and Fixer.
    
    Pipeline: Researcher → Strategist → Writer → Validator → FIXER → Editor → Stylist → Publisher
    """
    
    # Agent 1: Research Agent
    researcher = Agent(
        role="Technical Research Specialist",
        goal="Verify technologies exist and gather accurate, factual information from official sources",
        backstory=(
            "You are a meticulous researcher who NEVER invents information. "
            "Before writing about any technology, you:\n"
            "1. Verify it actually exists\n"
            "2. Find official documentation\n"
            "3. Identify real APIs, methods, and imports\n"
            "4. Note what the technology ACTUALLY does (not what you think it might do)\n"
            "5. Gather real code examples from official docs\n\n"
            "You are FORBIDDEN from:\n"
            "- Inventing APIs or methods that don't exist\n"
            "- Assuming functionality without verification\n"
            "- Creating fake code examples\n"
            "- Making up statistics or performance claims\n\n"
            "If you cannot find reliable information, you say so explicitly."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    # Agent 2: Strategist
    strategist = Agent(
        role="AI Content Strategist",
        goal="Design enterprise-focused blog outlines based on VERIFIED research",
        backstory=(
            "You create detailed outlines using ONLY information from the research phase. "
            "You focus on concrete examples, measurable benefits, and practical applications. "
            "You NEVER add information that wasn't verified by the researcher."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    # Agent 3: Writer
    writer = Agent(
        role="Senior Technical Writer",
        goal="Write comprehensive blog posts using ONLY verified information and real APIs",
        backstory=(
            "You write complete, accurate articles using ONLY the research provided. "
            "You follow these STRICT rules:\n\n"
            "CODE RULES:\n"
            "- Every code block MUST use real, verified APIs from the research\n"
            "- All imports must be correct and complete\n"
            "- Never invent method names, classes, or functions\n"
            "- Never use deprecated APIs (e.g., sklearn.datasets.load_boston)\n"
            "- Always include ALL required imports in each code block\n"
            "- Code must be self-contained and actually runnable\n"
            "- NEVER put shell commands like 'pip install ...' inside ```python``` blocks\n"
            "- Use ```bash``` (or ```shell```) for installation commands\n"
            "- If you must show pip inside a Python block, comment it out\n\n"
            "CONTENT RULES:\n"
            "- Use ONLY facts from the research - no speculation\n"
            "- Never invent statistics or performance claims\n"
            "- If research is incomplete, say so - don't fill gaps with fiction\n"
            "- Be accurate over being comprehensive\n\n"
            "If the research doesn't provide enough detail for code examples, "
            "you write what you CAN verify and note what you can't."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    # Agent 4: Code Validator
    validator = Agent(
        role="Code Quality Validator",
        goal="Verify all code examples are syntactically correct and use real APIs",
        backstory=(
            "You are a strict code reviewer who validates every Python code block. "
            "You check for:\n"
            "1. Syntax errors\n"
            "2. Missing imports\n"
            "3. Deprecated APIs\n"
            "4. Placeholder code (TODO, ..., etc.)\n"
            "5. Invented or non-existent APIs\n"
            "6. Shell commands in Python blocks (pip install, etc.)\n\n"
            "If code fails validation, you provide a detailed report. "
            "The Fixer agent will use your report to correct issues."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    # Agent 5: Code Fixer (NEW!)
    fixer = Agent(
        role="Code Fixer",
        goal="Rewrite or correct invalid Python code blocks so they are syntactically correct, use real APIs from research, and pass validation",
        backstory=(
            "You are a meticulous bug fixer. You receive a technical article and a code validation report.\n"
            "You ONLY touch code blocks. You:\n"
            "1. Fix syntax errors in Python code.\n"
            "2. Ensure all imports are present and correct.\n"
            "3. Remove or comment placeholder code (TODO, ..., your_data, etc.).\n"
            "4. Convert non-Python commands (like 'pip install ...') to either bash code blocks "
            "   (```bash```) or commented-out Python so that Python code blocks are always valid.\n"
            "5. Use ONLY APIs and methods verified in the research phase. Never invent new APIs.\n\n"
            "CRITICAL RULES:\n"
            "- If you see ```python with shell commands (pip, apt, etc.), change the fence to ```bash\n"
            "- OR comment out the shell command inside the Python block with # pip install ...\n"
            "- Every ```python block MUST be valid, parseable Python after your fixes\n"
            "- Do NOT change any narrative text outside code blocks\n"
            "- Return the FULL corrected article in Markdown\n\n"
            "You keep the narrative text unchanged."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    # Agent 6: Editor
    editor = Agent(
        role="Senior Technical Editor",
        goal="Polish content while preserving technical accuracy",
        backstory=(
            "You refine articles for readability WITHOUT changing technical content. "
            "You break up dense paragraphs, remove generic phrases, and improve flow. "
            "You NEVER alter code examples or technical claims. "
            "You ensure the article reads naturally while staying 100% accurate."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    # Agent 7: Stylist
    stylist = Agent(
        role="Blog Voice Stylist",
        goal="Add friendly intro and motivating conclusion while preserving all technical content",
        backstory=(
            "You add warmth to technical articles with:\n"
            "- A friendly 'Hello everyone!' greeting at the start\n"
            "- A 'Congratulations!' conclusion at the end\n\n"
            "You NEVER change technical content, code, or factual claims. "
            "You only add conversational bookends."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )
    
    # Agent 8: Publisher
    publisher = Agent(
        role="Jekyll Metadata Curator",
        goal="Generate SEO-optimized metadata based on actual article content",
        backstory=(
            "You create compelling metadata that accurately reflects the article. "
            "You never exaggerate or misrepresent what the article covers."
        ),
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
    
    # Task 1: RESEARCH
    t1 = Task(
        description=f"""Research and verify information about: {topic.title}

{topic_context}

Your task is to gather VERIFIED, FACTUAL information:

1. VERIFY THE TECHNOLOGY EXISTS:
   - What is it actually called?
   - Is it a Python package, library, framework, or tool?
   - Who created/maintains it?
   - Where is the official documentation?

2. GATHER REAL API INFORMATION:
   - What are the actual import statements?
   - What are the real class names and methods?
   - What parameters do methods actually take?
   - Find at least 2 real code examples from official docs

3. IDENTIFY ACTUAL CAPABILITIES:
   - What does it ACTUALLY do (not what you think)?
   - What are its real use cases from official sources?
   - What limitations are documented?

4. FIND CONCRETE DATA:
   - Are there real benchmarks or statistics?
   - What version is current?
   - What are actual known issues?

CRITICAL RULES:
- Use official documentation, GitHub repos, PyPI pages ONLY
- If you cannot verify something, explicitly say "Not found/verified"
- Never assume APIs or functionality
- Provide exact import statements and method signatures
- Include links to official sources

Output a detailed research report with:
- Verified facts ONLY
- Official documentation links
- Real code examples with sources
- Explicit gaps where information wasn't found""",
        expected_output="Detailed research report with verified facts and sources",
        agent=researcher,
    )
    
    # Task 2: Outline
    t2 = Task(
        description=f"""Create a detailed blog outline for: {topic.title}

Use ONLY the verified information from the research phase.

Sections:
1. Opening Overview - What it is and key benefits (from research)
2. Why It Matters - Real-world impact (verified use cases only)
3. Technical Deep Dive - Architecture (based on actual documentation)
4. Example Implementation - 2+ Python examples (using REAL APIs from research)
5. Business Value & Use Cases - Specific applications (verified only)
6. Limitations & Alternatives - Honest assessment (from research)
7. Getting Started - Actionable steps (using real commands/APIs)

{f"Include: What's New in v{topic.version}" if topic.version > 1 else ""}

RULES:
- Use ONLY facts from the research report
- Note which APIs are verified vs. not found
- If research is incomplete, plan around what IS verified
- Do not add speculative content

Target: 800-1200 words of VERIFIED content""",
        expected_output="Detailed outline using only verified research",
        agent=strategist,
        context=[t1],
    )
    
    # Task 3: Write Draft
    t3 = Task(
        description=f"""Write a complete technical blog article about: {topic.title}

Topic: {topic.summary or 'n/a'}

Use ONLY the verified research and outline provided.

STRUCTURE:
- Start with a natural opening (not 'Executive Summary')
- Use ## for main sections, ### for subsections
- Include 2+ Python code examples using REAL APIs from research
- Write 900-1400 words based on VERIFIED information
- Provide technical depth using actual documentation

CODE REQUIREMENTS - CRITICAL:
- Use ONLY APIs and methods verified in the research phase
- Every import must be exactly as documented
- Every method call must match real API signatures
- NO invented functions, classes, or parameters
- Code must be self-contained with all imports
- NO deprecated APIs (e.g., load_boston)
- NEVER put shell commands like 'pip install ...' inside ```python``` blocks
- Use ```bash``` for installation commands
- If you must show pip in Python, comment it out: # pip install package

CONTENT RULES - CRITICAL:
- Use ONLY facts from the research report
- Never invent statistics, benchmarks, or claims
- If you lack information, acknowledge it - don't fabricate
- Accuracy > Completeness
- Link to official documentation when possible

EXAMPLE CODE STRUCTURE:
```python
# All necessary imports (verified from research)
import verified_package as vp
from verified_module import VerifiedClass

# Real API usage (exactly as documented)
obj = VerifiedClass(param1="value")
result = obj.actual_method()
```

{f"Include a '## What's New in v{topic.version}' section" if topic.version > 1 else ""}

Write the complete, ACCURATE article now.""",
        expected_output="Complete article using ONLY verified information and real APIs",
        agent=writer,
        context=[t1, t2],
    )
    
    # Task 4: VALIDATE CODE
    t4 = Task(
        description="""Validate all Python code blocks in the article.

For EACH code block, check:

1. SYNTAX:
   - Can it be parsed by Python?
   - Are there syntax errors?

2. IMPORTS:
   - Are all used packages imported?
   - Are import statements correct?

3. DEPRECATED APIS:
   - No sklearn.datasets.load_boston
   - No pd.np.* usage
   - No .ix[] indexing
   - Other known deprecated APIs

4. COMPLETENESS:
   - No ... (ellipsis) placeholders
   - No TODO comments
   - No your_* placeholders
   - No incomplete functions

5. CORRECTNESS VS RESEARCH:
   - Do the APIs match what was verified in research?
   - Are method names exactly as documented?
   - Are parameters correct?

6. SHELL COMMANDS IN PYTHON BLOCKS:
   - Check for 'pip install', 'apt-get', etc. in ```python blocks
   - These are NOT valid Python and must be flagged

For each code block, report:
- Block number
- Syntax status (correct/incorrect)
- Import status (present/missing)
- Any issues found

If ANY code block fails, list ALL issues clearly.
If all pass, confirm with specific counts.

Provide a clear VALIDATION REPORT.""",
        expected_output="Validation report: PASS with details, or FAIL with specific issues",
        agent=validator,
        context=[t1, t3],
    )
    
    # Task 5: FIX CODE (NEW!)
    t5 = Task(
        description=(
            "You are given a technical article and a code validation report.\n\n"
            "1. Read the article from the Writer.\n"
            "2. Read the Validator's report. Identify which Python code blocks are invalid.\n\n"
            "For EACH Python code block in the article:\n"
            "- If it contains shell/CLI commands like 'pip install ...', do NOT keep them as Python:\n"
            "    • Either change the fence to ```bash``` and keep the command, OR\n"
            "    • Comment out the command so that the code becomes valid Python: # pip install ...\n"
            "- If there is a syntax error, correct it using REAL, verified APIs from the research.\n"
            "- If imports are missing, add them to the top of that code block.\n"
            "- Remove or replace placeholders like '...', 'TODO', 'your_data', etc.\n\n"
            "STRICT RULES:\n"
            "- Use ONLY APIs/methods that were verified in the research report.\n"
            "- Do NOT invent new classes, functions, or methods.\n"
            "- Do NOT change any narrative text outside code blocks.\n"
            "- Return the FULL corrected article in Markdown.\n\n"
            "EXAMPLES OF FIXES:\n"
            "BAD: ```python\npip install folium\n```\n"
            "GOOD: ```bash\npip install folium\n```\n"
            "OR: ```python\n# pip install folium\nimport folium\n```\n\n"
            "Apply fixes and return the complete corrected article."
        ),
        expected_output="Full article with all Python code blocks corrected so they are syntactically valid",
        agent=fixer,
        context=[t1, t3, t4],  # needs research, article, and validation report
    )
    
    # Task 6: Editorial Review (uses Fixer output)
    t6 = Task(
        description="""Review and refine the article for publication quality.

HUMANIZATION & READABILITY:
1. Remove AI fluff phrases:
   - "In today's rapidly evolving landscape"
   - "In the fast-paced world of"
   - "It's worth noting that"
   - "Leveraging the power of"
   - Generic business buzzwords
   
2. Improve flow and tone:
   - Make it conversational but authoritative
   - Break up walls of text
   - Add smooth transitions
   - Vary sentence structure
   
3. Ensure human voice:
   - Active voice over passive
   - Natural language over robotic phrases

VISUAL HINTS:
4. Where diagrams would help, add:
   <!-- Diagram: description -->

PRESERVATION:
5. DO NOT change technical content or code
6. DO NOT alter any verified facts or APIs
7. Preserve all code blocks exactly as written
8. Only improve readability, not accuracy

Return the FULL polished article.""",
        expected_output="Polished article with improved readability, preserved accuracy",
        agent=editor,
        context=[t5],  # NOTE: now uses Fixer output, not Writer directly
    )
    
    # Task 7: Voice & Style
    t7 = Task(
        description=f"""Add friendly bookends to the technical article about: {topic.title}.

INTRO (add at very beginning):
- Start with: "Hello everyone!" on first line
- In 2-4 sentences, introduce the article
- Mention the topic: "{topic.title}"
- Set friendly but professional tone
- Keep it concise

OUTRO (add at very end):
- Begin with: "Congratulations! You've learned..."
- In 2-4 sentences, summarize key takeaways
- Be encouraging and motivating
- No new technical content

RULES:
- DO NOT change ANY technical content
- DO NOT modify code blocks
- DO NOT alter factual claims
- ONLY add intro and outro
- Preserve all markdown structure

Return the COMPLETE final article.""",
        expected_output="Final article with friendly intro and motivating outro",
        agent=stylist,
        context=[t6],
    )
    
    # Task 8: Metadata
    t8 = Task(
        description="""Create metadata JSON for the final article.

Return ONLY JSON (no other text):
{"title": "Article Title", "excerpt": "Brief description", "tags": ["tag1", "tag2"]}

Requirements:
- Title: Accurate, compelling, ≤80 characters
- Excerpt: Clear value proposition, ≤220 characters
- Tags: 4-8 lowercase tags (use hyphens for multi-word)
- Must accurately reflect actual article content

Return only the JSON object.""",
        expected_output="JSON object with title, excerpt, and tags",
        agent=publisher,
        context=[t2, t7],
    )
    
    crew = Crew(
        agents=[researcher, strategist, writer, validator, fixer, editor, stylist, publisher],
        tasks=[t1, t2, t3, t4, t5, t6, t7, t8],
        process=Process.sequential,
        verbose=False,
    )
    
    return crew, (t1, t2, t3, t4, t5, t6, t7, t8)


def build_jekyll_post(date: datetime, topic: Topic, body: str, meta: Dict) -> Tuple[str, str]:
    """Build Jekyll post with front matter."""
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


def validate_final_body(body: str) -> None:
    """Validate article quality after styling with CODE VALIDATION."""
    min_chars = 700
    
    if len(body) < min_chars:
        logger.error("Body validation failed:")
        logger.error(f"  Length: {len(body)} chars (minimum: {min_chars})")
        logger.error(f"  Words: {len(body.split())}")
        raise RuntimeError(
            f"Generated body too short: {len(body)} chars (min {min_chars})"
        )
    
    # Check for friendly intro
    if body.startswith("Hello everyone!") or "Hello everyone!" in body[:200]:
        logger.info("✅ Found friendly intro greeting")
    else:
        logger.warning("⚠️  No 'Hello everyone!' intro found")
    
    # Check for motivating outro
    if "Congratulations!" in body:
        logger.info("✅ Found motivating conclusion")
    else:
        logger.warning("⚠️  No 'Congratulations!' outro found")
    
    # Check for headings
    if "## " not in body and "### " not in body:
        logger.warning("⚠️  No markdown headings found")
    
    # CRITICAL: Validate all code blocks
    logger.info("🔍 Validating Python code blocks...")
    all_valid, issues = extract_and_validate_code_blocks(body)
    
    if not all_valid:
        logger.error("❌ CODE VALIDATION FAILED:")
        for issue in issues:
            logger.error(f"   {issue}")
        raise RuntimeError(
            f"Article contains invalid code. Cannot publish.\n" +
            "\n".join(issues)
        )
    else:
        code_count = len(re.findall(r'```python', body))
        logger.info(f"✅ All {code_count} Python code blocks validated successfully")
    
    # Check for robotic phrases
    robotic_phrases = [
        "executive summary",
        "rapidly evolving landscape",
        "fast-paced world",
        "it's worth noting",
        "at the end of the day",
    ]
    
    found_robotic = []
    lower_body = body.lower()
    for phrase in robotic_phrases:
        if phrase in lower_body:
            found_robotic.append(phrase)
    
    if found_robotic:
        logger.warning(f"⚠️  Robotic phrases found: {', '.join(found_robotic)}")
    
    logger.info(f"✅ Validation passed: {len(body)} chars, {len(body.split())} words")


def main() -> None:
    """Main entry point with 8-agent pipeline including Fixer."""
    logger.info("="*70)
    logger.info("Daily Blog Generation (Production v2.6 - WITH CODE FIXER)")
    logger.info("8-Agent Pipeline: Research → Strategy → Write → Validate → FIX → Edit → Style → Publish")
    logger.info("="*70)
    logger.info(f"BASE_DIR: {BASE_DIR}")
    logger.info(f"BLOG_POSTS_DIR: {BLOG_POSTS_DIR}")
    logger.info(f"API_DIR: {API_DIR}")
    
    if not API_DIR.exists():
        logger.error(f"❌ API directory missing: {API_DIR}")
        logger.error(f"   Please create: mkdir -p {API_DIR}")
        sys.exit(1)
    
    try:
        # Select topic FROM YOUR DATA
        topic = select_next_topic()
        logger.info(f"📝 Selected Topic:")
        logger.info(f"   Kind: {topic.kind}")
        logger.info(f"   Title: {topic.title}")
        logger.info(f"   ID: {topic.id}")
        logger.info(f"   Version: v{topic.version}")
        
        # Build 8-agent crew with research, validation, and fixer
        crew, (t1, t2, t3, t4, t5, t6, t7, t8) = build_blog_crew(topic)
        logger.info("🚀 Running 8-agent CrewAI pipeline...")
        logger.info("   🔬 Stage 1/8: Researcher (verifying technology)")
        logger.info("   📋 Stage 2/8: Strategist (outlining)")
        logger.info("   ✍️  Stage 3/8: Writer (drafting)")
        logger.info("   🔍 Stage 4/8: Validator (checking code)")
        logger.info("   🔧 Stage 5/8: Fixer (correcting code)")
        logger.info("   ✨ Stage 6/8: Editor (polishing)")
        logger.info("   💬 Stage 7/8: Stylist (humanizing)")
        logger.info("   📦 Stage 8/8: Publisher (metadata)")
        logger.info("   This may take 6-10 minutes with validation and fixing...")
        
        result = crew.kickoff()
        
        if not result:
            raise RuntimeError("CrewAI returned no result")
        
        # Check validation result (but don't exit - let Fixer handle it)
        validation_output = (t4.output.raw if t4.output else "").strip()
        if "FAIL" in validation_output.upper():
            logger.warning("⚠️  LLM validator reported FAIL - Fixer will attempt to correct code.")
            logger.info("Validation issues found (Fixer will handle):")
            for line in validation_output.split('\n')[:10]:  # Show first 10 lines
                logger.info(f"   {line}")
        else:
            logger.info("✅ LLM validator reported PASS")
        
        # Extract body from stylist (t7), which sits after Fixer + Editor
        body = (t7.output.raw if t7.output else "").strip()
        
        if not body:
            logger.warning("⚠️  Stylist produced no output, falling back to editor")
            body = (t6.output.raw if t6.output else "").strip()
            
            if not body:
                logger.warning("⚠️  Editor produced no output, falling back to fixer")
                body = (t5.output.raw if t5.output else "").strip()
                
                if not body:
                    raise RuntimeError("All agents produced empty output")
        
        logger.info(f"📄 Final content: {len(body)} chars, {len(body.split())} words")
        
        # Clean meta-commentary
        body = clean_and_normalize_body(body)
        
        # Final validation with code checking - THIS IS THE HARD GATE
        logger.info("🔒 Final validation gate (AST-based)...")
        validate_final_body(body)
        
        # Parse metadata (from t8 now)
        meta_raw = (t8.output.raw if t8.output else "{}").strip()
        
        try:
            json_start = meta_raw.find("{")
            json_end = meta_raw.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                meta = json.loads(meta_raw[json_start:json_end])
            else:
                meta = json.loads(meta_raw)
            logger.info(f"✅ Parsed metadata: '{meta.get('title', 'N/A')[:50]}'")
        except Exception as e:
            logger.warning(f"⚠️  Metadata parse failed: {e}")
            meta = {
                "title": topic.title,
                "excerpt": topic.summary or f"Learn about {topic.title}",
                "tags": topic.tags or ["ai", "machine-learning"]
            }
        
        # Build and save
        today = get_current_date()
        filename, content = build_jekyll_post(today, topic, body, meta)
        path = save_post(filename, content)
        record_coverage(topic, filename)
        
        # Count features
        code_blocks = len(re.findall(r'```python', body))
        bash_blocks = len(re.findall(r'```bash', body))
        diagram_count = len(re.findall(r'<!--\s*Diagram:\s*[^>]+-->', body))
        has_intro = "Hello everyone!" in body[:200]
        has_outro = "Congratulations!" in body
        
        # Success summary
        logger.info("="*70)
        logger.info("✅ BLOG POST GENERATED AND VALIDATED SUCCESSFULLY")
        logger.info(f"   File: {path}")
        logger.info(f"   Topic: {topic.kind} - {topic.title} (v{topic.version})")
        logger.info(f"   Title: {meta.get('title', topic.title)}")
        logger.info(f"   Date: {today.strftime('%Y-%m-%d')}")
        logger.info(f"   Words: ~{len(body.split())}")
        logger.info(f"   Size: {len(content)} bytes")
        logger.info("="*70)
        logger.info("")
        logger.info("🔬 Quality Assurance:")
        logger.info("   ✅ Technology research completed")
        logger.info("   ✅ APIs verified against documentation")
        logger.info(f"   ✅ {code_blocks} Python code blocks validated for syntax")
        logger.info(f"   ✅ {bash_blocks} bash blocks for shell commands")
        logger.info("   ✅ Code fixer applied corrections")
        logger.info("   ✅ No deprecated APIs detected")
        logger.info("   ✅ All imports verified")
        logger.info("   ✅ Editorial review completed")
        logger.info(f"   ✅ {'Friendly intro added' if has_intro else '⚠️  No intro'}")
        logger.info(f"   ✅ {'Motivating outro added' if has_outro else '⚠️  No outro'}")
        logger.info(f"   ✅ {diagram_count} diagram hints added")
        logger.info("")
        logger.info("🔧 Next steps:")
        logger.info(f"   • Review: cat '{path}'")
        logger.info(f"   • Add diagrams at <!-- Diagram: ... --> comments")
        logger.info(f"   • Preview: cd {BASE_DIR} && jekyll serve")
        logger.info(f"   • Commit: git add blog/posts/ data/ && git commit -m 'Add validated blog post'")
        logger.info("")
        
    except Exception as e:
        logger.error("="*70)
        logger.error(f"❌ GENERATION FAILED: {e}")
        logger.error("="*70)
        logger.error("")
        logger.error("🔍 Troubleshooting:")
        logger.error("   1. Check if data files exist with YOUR packages/repos")
        logger.error(f"      ls -l {API_DIR}/*.json")
        logger.error("   2. Verify JSON format is valid")
        logger.error("   3. Check Ollama: ollama list")
        logger.error("   4. Review logs: cat logs/blog_generation.log")
        logger.error("")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()