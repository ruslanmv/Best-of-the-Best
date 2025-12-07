#!/usr/bin/env python3
"""
test/test_agents.py

AGENT HEALTH & QUALITY TESTING FRAMEWORK

Tests each agent from generate_daily_blog.py individually to verify:
- Agent initialization works
- Agent can process tasks
- Output quality meets standards
- Response time is reasonable
- No errors or crashes

Usage:
    # Test all agents
    python test/test_agents.py
    
    # Test specific agent
    python test/test_agents.py --agent researcher
    
    # Verbose debugging
    python test/test_agents.py --verbose
    
    # Save report
    python test/test_agents.py --report agents_health.json

Output:
    - Health status for each agent
    - Quality metrics (length, completeness, errors)
    - Performance metrics (time, iterations)
    - Debugging information
    - Overall system health score
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import traceback
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup paths
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=PROJECT_ROOT / '.env', override=False)
except ImportError:
    pass

from crewai import Agent, Task, Crew, Process  # type: ignore

# Import from generate_daily_blog
try:
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    from llm_client import llm
    
    # Import search tools if available
    try:
        from search import search_web, scrape_webpage, scrape_readme, get_package_health
        SEARCH_TOOLS = True
    except ImportError:
        SEARCH_TOOLS = False
        search_web = scrape_webpage = scrape_readme = get_package_health = None
    
except ImportError as e:
    print(f"❌ Failed to import dependencies: {e}")
    sys.exit(1)

# ============================================================================
# LOGGING SETUP
# ============================================================================
LOG_DIR = PROJECT_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / "agent_tests.log", mode='w'),
    ],
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================
@dataclass
class AgentTestResult:
    """Results from testing a single agent"""
    agent_name: str
    role: str
    status: str  # 'PASS', 'FAIL', 'WARNING'
    
    # Initialization
    initialization_success: bool
    initialization_time: float
    initialization_error: Optional[str] = None
    
    # Execution (Added defaults to fix TypeError)
    execution_success: bool = False
    execution_time: float = 0.0
    iterations_used: int = 0
    execution_error: Optional[str] = None
    
    # Output Quality (Added defaults to fix TypeError)
    output_length: int = 0
    output_word_count: int = 0
    output_has_content: bool = False
    output_quality_score: float = 0.0  # 0-100
    output_sample: str = ""
    
    # Issues
    issues: List[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.issues is None:
            self.issues = []
        if self.warnings is None:
            self.warnings = []
    
    @property
    def health_score(self) -> float:
        """Overall health score 0-100"""
        score = 0.0
        
        # Initialization (20 points)
        if self.initialization_success:
            score += 20
        
        # Execution (30 points)
        if self.execution_success:
            score += 30
        
        # Output quality (40 points)
        score += self.output_quality_score * 0.4
        
        # Penalties
        score -= len(self.issues) * 5
        score -= len(self.warnings) * 2
        
        # Time penalty (if too slow)
        if self.execution_time > 60:
            score -= 10
        
        return max(0.0, min(100.0, score))
    
    @property
    def status_emoji(self) -> str:
        if self.status == 'PASS':
            return '✅'
        elif self.status == 'FAIL':
            return '❌'
        else:
            return '⚠️'


@dataclass
class SystemHealthReport:
    """Overall system health report"""
    timestamp: str
    total_agents: int
    passed_agents: int
    failed_agents: int
    warning_agents: int
    average_health_score: float
    agent_results: List[AgentTestResult]
    
    @property
    def overall_status(self) -> str:
        if self.failed_agents == 0:
            if self.warning_agents == 0:
                return 'HEALTHY'
            else:
                return 'MOSTLY HEALTHY'
        elif self.passed_agents > self.failed_agents:
            return 'DEGRADED'
        else:
            return 'CRITICAL'
    
    @property
    def status_emoji(self) -> str:
        if self.overall_status == 'HEALTHY':
            return '✅'
        elif self.overall_status == 'MOSTLY HEALTHY':
            return '⚠️'
        elif self.overall_status == 'DEGRADED':
            return '⚠️'
        else:
            return '❌'


# ============================================================================
# AGENT DEFINITIONS & TEST TASKS
# ============================================================================
def is_ollama_llm() -> bool:
    """Detect if using Ollama"""
    llm_model = os.getenv("NEWS_LLM_MODEL", "")
    return "ollama" in llm_model.lower()


def create_test_agents() -> Dict[str, Tuple[Agent, str]]:
    """
    Create all agents from generate_daily_blog.py for testing.
    Returns: {agent_name: (agent_instance, test_description)}
    """
    using_ollama = is_ollama_llm()
    
    agents = {}
    
    # ========================================================================
    # AGENT 1: RESEARCHER
    # ========================================================================
    researcher_tools = []
    if SEARCH_TOOLS and not using_ollama:
        researcher_tools = [search_web, scrape_webpage] if search_web else []
    
    researcher = Agent(
        role="Research Specialist",
        goal="Research topics and find accurate information",
        backstory="Expert researcher. Find official docs and examples. Report facts only.",
        llm=llm,
        tools=researcher_tools,
        verbose=False,
        allow_delegation=False,
        max_iter=2,
    )
    
    agents['researcher'] = (
        researcher,
        "Research XGBoost Python package. Find current version, features, and code examples."
    )
    
    # ========================================================================
    # AGENT 2: STRATEGIST
    # ========================================================================
    strategist = Agent(
        role="Content Planner",
        goal="Create clear blog outline",
        backstory="Design structured, engaging blog plans.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    agents['strategist'] = (
        strategist,
        "Create blog outline for XGBoost tutorial with sections: Introduction, Installation, Examples, Best Practices, Conclusion."
    )
    
    # ========================================================================
    # AGENT 3: WRITER
    # ========================================================================
    writer = Agent(
        role="Technical Writer",
        goal="Write complete blog article with working code",
        backstory="Write 1200+ word articles with complete imports and working code.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    agents['writer'] = (
        writer,
        "Write a 500-word introduction to XGBoost with one complete code example including all imports."
    )
    
    # ========================================================================
    # AGENT 4: VALIDATOR
    # ========================================================================
    validator = Agent(
        role="Code Validator",
        goal="Check all code for errors",
        backstory="Validate Python code blocks. Report PASS or FAIL with issues.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    test_code = '''```python
import xgboost as xgb
from sklearn.datasets import load_iris
X, y = load_iris(return_X_y=True)
model = xgb.XGBClassifier()
model.fit(train_X, train_y)
```'''
    
    agents['validator'] = (
        validator,
        f"Validate this Python code and report issues:\n{test_code}"
    )
    
    # ========================================================================
    # AGENT 5: FIXER
    # ========================================================================
    fixer = Agent(
        role="Code Fixer",
        goal="Fix all invalid Python code",
        backstory="Fix syntax errors, add imports, remove placeholders.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    agents['fixer'] = (
        fixer,
        f"Fix this code (missing train_test_split):\n{test_code}"
    )
    
    # ========================================================================
    # AGENT 6: EDITOR
    # ========================================================================
    editor = Agent(
        role="Editor",
        goal="Polish readability",
        backstory="Improve flow, remove buzzwords. Keep code unchanged.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    sample_text = """XGBoost is a revolutionary and game-changing machine learning framework 
    that leverages cutting-edge gradient boosting algorithms to deliver unprecedented performance."""
    
    agents['editor'] = (
        editor,
        f"Remove buzzwords from: {sample_text}"
    )
    
    # ========================================================================
    # AGENT 7: STYLIST
    # ========================================================================
    stylist = Agent(
        role="Stylist",
        goal="Add intro and conclusion",
        backstory="Add 'Hello everyone!' intro and 'Congratulations!' conclusion.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    agents['stylist'] = (
        stylist,
        "Add friendly intro and conclusion to: 'XGBoost is a powerful machine learning library.'"
    )
    
    # ========================================================================
    # AGENT 8: PUBLISHER
    # ========================================================================
    publisher = Agent(
        role="Metadata Creator",
        goal="Generate SEO metadata JSON",
        backstory="Create JSON with title, excerpt, tags.",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=1,
    )
    
    agents['publisher'] = (
        publisher,
        'Create metadata JSON for blog about XGBoost: {"title": "...", "excerpt": "...", "tags": [...]}'
    )
    
    return agents


# ============================================================================
# AGENT TESTING FUNCTIONS
# ============================================================================
def extract_task_output(task: Task) -> str:
    """Extract output from task"""
    if not task or not hasattr(task, 'output') or task.output is None:
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
            if result and isinstance(result, str) and len(result) > 10:
                return result.strip()
        except Exception:
            continue
    
    return ""


def calculate_output_quality(output: str, expected_min_length: int = 50) -> Tuple[float, List[str]]:
    """
    Calculate output quality score (0-100) and identify issues.
    
    Checks:
    - Length
    - Word count
    - Completeness
    - Structure
    - No errors/placeholders
    """
    issues = []
    score = 0.0
    
    if not output:
        issues.append("Empty output")
        return 0.0, issues
    
    # Length check (25 points)
    if len(output) >= expected_min_length:
        score += 25
    else:
        score += (len(output) / expected_min_length) * 25
        issues.append(f"Output too short: {len(output)} chars (expected {expected_min_length}+)")
    
    # Word count (15 points)
    word_count = len(output.split())
    if word_count >= expected_min_length / 5:
        score += 15
    else:
        score += (word_count / (expected_min_length / 5)) * 15
        issues.append(f"Low word count: {word_count} words")
    
    # No error messages (20 points)
    error_patterns = [
        r'error',
        r'failed',
        r'exception',
        r'traceback',
        r'cannot',
        r'unable to',
    ]
    
    has_errors = False
    for pattern in error_patterns:
        if re.search(pattern, output, re.IGNORECASE):
            has_errors = True
            issues.append(f"Contains error-like text: '{pattern}'")
            break
    
    if not has_errors:
        score += 20
    
    # No placeholders (15 points)
    placeholder_patterns = [
        r'TODO',
        r'FIXME',
        r'\.\.\.+',
        r'your_\w+',
        r'\[INSERT\]',
        r'\[FILL\]',
    ]
    
    has_placeholders = False
    for pattern in placeholder_patterns:
        if re.search(pattern, output):
            has_placeholders = True
            issues.append(f"Contains placeholder: '{pattern}'")
            break
    
    if not has_placeholders:
        score += 15
    
    # Has structure (15 points)
    has_structure = any([
        len(output.split('\n\n')) > 1,  # Multiple paragraphs
        '##' in output,  # Headings
        '```' in output,  # Code blocks
        '\n- ' in output,  # Lists
    ])
    
    if has_structure:
        score += 15
    else:
        issues.append("No clear structure (paragraphs/headings/code)")
    
    # Coherence check (10 points)
    # Check if output is mostly coherent text (not random characters)
    words = output.split()
    if len(words) > 5:
        avg_word_length = sum(len(w) for w in words) / len(words)
        if 3 <= avg_word_length <= 12:  # Reasonable word length
            score += 10
        else:
            issues.append(f"Unusual average word length: {avg_word_length:.1f}")
    
    return score, issues


def test_agent(agent: Agent, test_description: str, agent_name: str, verbose: bool = False) -> AgentTestResult:
    """
    Test a single agent with comprehensive checks.
    
    Returns: AgentTestResult with all metrics
    """
    logger.info(f"\n{'='*70}")
    logger.info(f"Testing Agent: {agent_name.upper()}")
    logger.info(f"Role: {agent.role}")
    logger.info(f"{'='*70}")
    
    result = AgentTestResult(
        agent_name=agent_name,
        role=agent.role,
        status='UNKNOWN',
        initialization_success=False,
        initialization_time=0.0,
        execution_success=False,
        execution_time=0.0,
        iterations_used=0,
        output_length=0,
        output_word_count=0,
        output_has_content=False,
        output_quality_score=0.0,
    )
    
    # ========================================================================
    # PHASE 1: INITIALIZATION TEST
    # ========================================================================
    logger.info("📋 Phase 1: Initialization Test")
    
    init_start = time.time()
    try:
        # Check agent properties
        assert hasattr(agent, 'role'), "Agent missing 'role'"
        assert hasattr(agent, 'goal'), "Agent missing 'goal'"
        assert hasattr(agent, 'llm'), "Agent missing 'llm'"
        
        logger.info(f"   ✓ Role: {agent.role}")
        logger.info(f"   ✓ Goal: {agent.goal[:60]}...")
        logger.info(f"   ✓ LLM configured: {agent.llm is not None}")
        logger.info(f"   ✓ Tools: {len(agent.tools) if agent.tools else 0}")
        
        result.initialization_success = True
        result.initialization_time = time.time() - init_start
        
        logger.info(f"   ✅ Initialization: PASS ({result.initialization_time:.2f}s)")
        
    except Exception as e:
        result.initialization_success = False
        result.initialization_time = time.time() - init_start
        result.initialization_error = str(e)
        result.issues.append(f"Initialization failed: {e}")
        
        logger.error(f"   ❌ Initialization: FAIL - {e}")
        
        if verbose:
            traceback.print_exc()
        
        result.status = 'FAIL'
        return result
    
    # ========================================================================
    # PHASE 2: EXECUTION TEST
    # ========================================================================
    logger.info("\n🚀 Phase 2: Execution Test")
    logger.info(f"   Test Task: {test_description[:80]}...")
    
    exec_start = time.time()
    output = ""
    
    try:
        # Create task
        task = Task(
            description=test_description,
            expected_output="Comprehensive response addressing all points",
            agent=agent,
        )
        
        # Create minimal crew
        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=verbose,
        )
        
        # Execute
        logger.info("   ⏳ Executing task...")
        crew_result = crew.kickoff()
        
        # Extract output
        output = extract_task_output(task)
        
        result.execution_success = True
        result.execution_time = time.time() - exec_start
        
        # Try to get iteration count
        if hasattr(task, 'iterations'):
            result.iterations_used = task.iterations
        elif hasattr(agent, '_i'):
            result.iterations_used = agent._i
        else:
            result.iterations_used = 1
        
        logger.info(f"   ✅ Execution: PASS ({result.execution_time:.2f}s)")
        logger.info(f"   ℹ️  Iterations: {result.iterations_used}")
        
    except Exception as e:
        result.execution_success = False
        result.execution_time = time.time() - exec_start
        result.execution_error = str(e)
        result.issues.append(f"Execution failed: {e}")
        
        logger.error(f"   ❌ Execution: FAIL - {e}")
        
        if verbose:
            traceback.print_exc()
        
        result.status = 'FAIL'
        return result
    
    # ========================================================================
    # PHASE 3: OUTPUT QUALITY TEST
    # ========================================================================
    logger.info("\n📊 Phase 3: Output Quality Test")
    
    result.output_length = len(output)
    result.output_word_count = len(output.split())
    result.output_has_content = len(output) > 50
    
    logger.info(f"   Length: {result.output_length} chars")
    logger.info(f"   Words: {result.output_word_count}")
    
    # Calculate quality score
    quality_score, quality_issues = calculate_output_quality(output, expected_min_length=100)
    result.output_quality_score = quality_score
    
    # Store sample (first 200 chars)
    result.output_sample = output[:200] + "..." if len(output) > 200 else output
    
    logger.info(f"   Quality Score: {quality_score:.1f}/100")
    
    if quality_issues:
        result.issues.extend(quality_issues)
        logger.warning("   Quality Issues:")
        for issue in quality_issues:
            logger.warning(f"      • {issue}")
    
    # Show output sample
    if verbose and output:
        logger.info("\n   📄 Output Sample (first 300 chars):")
        logger.info("   " + "-"*66)
        for line in output[:300].split('\n'):
            logger.info(f"   {line}")
        logger.info("   " + "-"*66)
    
    # ========================================================================
    # PHASE 4: DETERMINE FINAL STATUS
    # ========================================================================
    logger.info("\n🎯 Final Assessment")
    
    # Determine status
    if result.health_score >= 80:
        result.status = 'PASS'
    elif result.health_score >= 50:
        result.status = 'WARNING'
    else:
        result.status = 'FAIL'
    
    # Performance warnings
    if result.execution_time > 60:
        result.warnings.append(f"Slow execution: {result.execution_time:.1f}s")
    
    if result.iterations_used > 5:
        result.warnings.append(f"High iterations: {result.iterations_used}")
    
    # Log final status
    logger.info(f"   Status: {result.status_emoji} {result.status}")
    logger.info(f"   Health Score: {result.health_score:.1f}/100")
    
    if result.issues:
        logger.warning(f"   Issues ({len(result.issues)}):")
        for issue in result.issues:
            logger.warning(f"      • {issue}")
    
    if result.warnings:
        logger.warning(f"   Warnings ({len(result.warnings)}):")
        for warning in result.warnings:
            logger.warning(f"      • {warning}")
    
    return result


# ============================================================================
# REPORTING
# ============================================================================
def print_summary_table(results: List[AgentTestResult]) -> None:
    """Print summary table of all results"""
    
    print("\n" + "="*70)
    print("AGENT HEALTH SUMMARY")
    print("="*70)
    print()
    
    # Header
    print(f"{'Agent':<15} {'Status':<8} {'Health':<10} {'Time':<10} {'Output':<12} {'Issues':<8}")
    print("-"*70)
    
    # Rows
    for r in results:
        status = f"{r.status_emoji} {r.status}"
        health = f"{r.health_score:.1f}/100"
        exec_time = f"{r.execution_time:.1f}s"
        output = f"{r.output_word_count}w"
        issues = str(len(r.issues))
        
        print(f"{r.agent_name:<15} {status:<8} {health:<10} {exec_time:<10} {output:<12} {issues:<8}")
    
    print("-"*70)
    
    # Stats
    total = len(results)
    passed = sum(1 for r in results if r.status == 'PASS')
    warned = sum(1 for r in results if r.status == 'WARNING')
    failed = sum(1 for r in results if r.status == 'FAIL')
    avg_health = sum(r.health_score for r in results) / total if total > 0 else 0
    avg_time = sum(r.execution_time for r in results) / total if total > 0 else 0
    
    print(f"Total Agents: {total}")
    print(f"Passed: {passed} ({passed/total*100:.1f}%)")
    print(f"Warnings: {warned} ({warned/total*100:.1f}%)")
    print(f"Failed: {failed} ({failed/total*100:.1f}%)")
    print(f"Avg Health: {avg_health:.1f}/100")
    print(f"Avg Time: {avg_time:.1f}s")
    print()


def generate_health_report(results: List[AgentTestResult]) -> SystemHealthReport:
    """Generate system health report"""
    
    total = len(results)
    passed = sum(1 for r in results if r.status == 'PASS')
    warned = sum(1 for r in results if r.status == 'WARNING')
    failed = sum(1 for r in results if r.status == 'FAIL')
    avg_health = sum(r.health_score for r in results) / total if total > 0 else 0
    
    report = SystemHealthReport(
        timestamp=datetime.now().isoformat(),
        total_agents=total,
        passed_agents=passed,
        failed_agents=failed,
        warning_agents=warned,
        average_health_score=avg_health,
        agent_results=results,
    )
    
    return report


def save_report(report: SystemHealthReport, filepath: Path) -> None:
    """Save report to JSON file"""
    
    # Convert to dict
    data = {
        'timestamp': report.timestamp,
        'overall_status': report.overall_status,
        'total_agents': report.total_agents,
        'passed_agents': report.passed_agents,
        'failed_agents': report.failed_agents,
        'warning_agents': report.warning_agents,
        'average_health_score': report.average_health_score,
        'agent_results': [
            {
                'agent_name': r.agent_name,
                'role': r.role,
                'status': r.status,
                'health_score': r.health_score,
                'initialization_success': r.initialization_success,
                'initialization_time': r.initialization_time,
                'execution_success': r.execution_success,
                'execution_time': r.execution_time,
                'iterations_used': r.iterations_used,
                'output_length': r.output_length,
                'output_word_count': r.output_word_count,
                'output_quality_score': r.output_quality_score,
                'output_sample': r.output_sample,
                'issues': r.issues,
                'warnings': r.warnings,
            }
            for r in report.agent_results
        ]
    }
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"\n✅ Report saved: {filepath}")


# ============================================================================
# MAIN
# ============================================================================
def main():
    """Main test runner"""
    
    parser = argparse.ArgumentParser(description="Test blog generation agents")
    parser.add_argument('--agent', type=str, help="Test specific agent only")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output")
    parser.add_argument('--report', type=str, help="Save report to file (JSON)")
    args = parser.parse_args()
    
    print("="*70)
    print("AGENT HEALTH & QUALITY TEST FRAMEWORK")
    print("="*70)
    print(f"Project: {PROJECT_ROOT}")
    print(f"LLM: {os.getenv('NEWS_LLM_MODEL', 'not set')}")
    print(f"Search Tools: {'✅ Available' if SEARCH_TOOLS else '❌ Not available'}")
    print()
    
    # Create agents
    logger.info("🔧 Creating test agents...")
    try:
        test_agents = create_test_agents()
        logger.info(f"✅ Created {len(test_agents)} agents for testing\n")
    except Exception as e:
        logger.error(f"❌ Failed to create agents: {e}")
        traceback.print_exc()
        sys.exit(1)
    
    # Filter if specific agent requested
    if args.agent:
        if args.agent.lower() in test_agents:
            test_agents = {args.agent.lower(): test_agents[args.agent.lower()]}
            logger.info(f"🎯 Testing single agent: {args.agent}\n")
        else:
            logger.error(f"❌ Agent '{args.agent}' not found")
            logger.info(f"Available agents: {', '.join(test_agents.keys())}")
            sys.exit(1)
    
    # Run tests
    results = []
    total = len(test_agents)
    
    for i, (agent_name, (agent, test_desc)) in enumerate(test_agents.items(), 1):
        print(f"\n{'='*70}")
        print(f"TESTING AGENT {i}/{total}: {agent_name.upper()}")
        print(f"{'='*70}")
        
        try:
            result = test_agent(agent, test_desc, agent_name, verbose=args.verbose)
            results.append(result)
            
            # Summary
            print(f"\n{result.status_emoji} {agent_name.upper()}: {result.status}")
            print(f"   Health: {result.health_score:.1f}/100")
            print(f"   Time: {result.execution_time:.1f}s")
            print(f"   Output: {result.output_word_count} words")
            
            if result.issues:
                print(f"   Issues: {len(result.issues)}")
                for issue in result.issues[:3]:  # Show first 3
                    print(f"      • {issue}")
            
        except Exception as e:
            logger.error(f"❌ Test crashed for {agent_name}: {e}")
            if args.verbose:
                traceback.print_exc()
            
            # Create failed result
            result = AgentTestResult(
                agent_name=agent_name,
                role=agent.role if hasattr(agent, 'role') else 'Unknown',
                status='FAIL',
                initialization_success=False,
                initialization_time=0.0,
                execution_success=False,
                execution_time=0.0,
                iterations_used=0,
                output_length=0,
                output_word_count=0,
                output_has_content=False,
                output_quality_score=0.0,
            )
            result.issues.append(f"Test crashed: {e}")
            results.append(result)
    
    # Print summary
    print_summary_table(results)
    
    # Generate report
    report = generate_health_report(results)
    
    print(f"\n{'='*70}")
    print(f"OVERALL SYSTEM STATUS: {report.status_emoji} {report.overall_status}")
    print(f"{'='*70}")
    print(f"Average Health Score: {report.average_health_score:.1f}/100")
    print()
    
    # Recommendations
    failed_agents = [r for r in results if r.status == 'FAIL']
    if failed_agents:
        print("⚠️  FAILED AGENTS REQUIRE ATTENTION:")
        for r in failed_agents:
            print(f"   • {r.agent_name}: {r.issues[0] if r.issues else 'Unknown issue'}")
        print()
    
    warning_agents = [r for r in results if r.status == 'WARNING']
    if warning_agents:
        print("⚠️  AGENTS WITH WARNINGS:")
        for r in warning_agents:
            print(f"   • {r.agent_name}: Health {r.health_score:.1f}/100")
        print()
    
    # Save report if requested
    if args.report:
        report_path = Path(args.report)
        save_report(report, report_path)
    
    # Exit code
    if report.overall_status in ['HEALTHY', 'MOSTLY HEALTHY']:
        print("✅ All agents operational\n")
        sys.exit(0)
    elif report.overall_status == 'DEGRADED':
        print("⚠️  Some agents degraded - review recommended\n")
        sys.exit(1)
    else:
        print("❌ Critical issues detected - immediate action required\n")
        sys.exit(2)


if __name__ == "__main__":
    main()