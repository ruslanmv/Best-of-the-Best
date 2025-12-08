"""
Research Phase Tasks (Tasks 1-5) - Phase 1 of Split-Crew Architecture

These tasks handle the research phase:
1. Orchestration - Strategy decision
2. README Analysis - Extract documentation
3. Package Health - Version validation
4. Web Research - Fallback search
5. Quality Validation - Source rating
"""
from typing import Tuple
from crewai import Task, Agent  # type: ignore

from blog_generator.core.models import Topic


def build_research_tasks(
    topic: Topic,
    topic_type: str,
    identifier: str,
    orchestrator: Agent,
    readme_analyst: Agent,
    package_health_validator: Agent,
    web_researcher: Agent,
    source_validator: Agent,
) -> Tuple[Task, Task, Task, Task, Task]:
    """
    Build all research phase tasks (Tasks 1-5)
    
    Args:
        topic: Topic metadata
        topic_type: Type of topic (package/repo/general)
        identifier: Topic identifier
        orchestrator: Agent 1
        readme_analyst: Agent 2
        package_health_validator: Agent 3
        web_researcher: Agent 4
        source_validator: Agent 5
    
    Returns:
        Tuple of 5 tasks
    """
    
    # Task 1: Orchestration
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
    
    # Task 2: README Analysis
    readme_task = Task(
        description=f"""
        Extract complete information from README for: {identifier}
        
        USE the tool: "Get README from PyPI package or GitHub repository" 
        with input "{identifier}"
        
        Extract:
        1. **Version Information**
           - Current version, Python requirements, dependencies
        
        2. **Installation**
           - Exact pip install command
        
        3. **Code Examples** (STRICT REALITY CHECK)
           - Extract code blocks ONLY if they literally exist in the README text.
           - Copy them EXACTLY as written.
           - If the README contains no code, output: "NO_CODE_EXAMPLES_FOUND".
           - DO NOT INVENT, SIMULATE, OR WRITE YOUR OWN CODE EXAMPLES.
        
        4. **Features**
           - Main capabilities and Use cases
        
        5. **Warnings**
           - Deprecation notices or known issues
        
        OUTPUT: Structured README analysis. If no code is in the source, explicitly state that.
        """,
        expected_output="Accurate README analysis based ONLY on provided text",
        agent=readme_analyst,
    )
    
    # Task 3: Package Health Validation
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
    
    # Task 4: Web Research (Fallback)
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
    
    # Task 5: Source Quality Validation
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
        - Top 1 Source cited (with URLs)?

        CRITICAL URL RULES:
        - If any URLs appear in the research context, you MUST copy the top 1 into the Resources section below.
        - List them as Markdown links.
        - Max 2 URLs only.
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
    
    return (
        orchestration_task,
        readme_task,
        health_task,
        web_research_task,
        quality_task,
    )