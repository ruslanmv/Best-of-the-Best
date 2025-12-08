"""
Crew Builder - Standard and Memory-Optimized Architectures - PRODUCTION v4.3

CRITICAL FIXES:
- Dynamic agent prompts (no hardcoded package names)
- Pass package_identifier and topic_title to agent factories
- Validation gates for research quality
- Memory-optimized split-crew architecture

This module provides two ways to build CrewAI crews:

1. Standard Mode (build_standard_crew):
   - All 11 agents in single crew
   - Higher memory usage (~9GB peak)
   - Simpler debugging
   - Use for local development

2. Optimized Mode (build_research_crew_optimized + build_writing_crew_optimized):
   - Split into Phase 1 (research, 5 agents) and Phase 2 (writing, 6 agents)
   - Lower memory usage (~5GB peak)
   - Garbage collection between phases
   - Use for GitHub workflows / limited memory environments
"""
import gc
from typing import Dict, Tuple

from crewai import Crew, Process, Task  # type: ignore

from blog_generator.config import logger
from blog_generator.core.models import Topic
from blog_generator.core.utils import detect_topic_type
from blog_generator.agents.research_agents import (
    create_orchestrator,
    create_readme_analyst,
    create_package_health_validator,
    create_web_researcher,
    create_source_quality_validator,
)
from blog_generator.agents.writing_agents import (
    create_content_planner,
    create_technical_writer,
    create_code_validator,
    create_code_fixer,
    create_content_editor,
    create_metadata_publisher,
)
from blog_generator.agents.research_tasks import build_research_tasks
from blog_generator.agents.writing_tasks import build_writing_tasks


# ============================================================================
# STANDARD MODE - Monolithic Architecture (All 11 Agents)
# ============================================================================

def build_all_tasks_standard(
    topic: Topic,
    topic_type: str,
    identifier: str,
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
) -> Tuple:
    """
    Build all 11 tasks for standard monolithic pipeline.
    
    In standard mode, writing tasks use task.context dependencies
    instead of string injection for research data.
    
    Args:
        topic: Topic metadata
        topic_type: Type of topic (package/repo/general)
        identifier: Topic identifier
        All 11 agent instances
    
    Returns:
        Tuple of all 11 tasks in execution order
    """
    # ========================================================================
    # PHASE 1: Research Tasks (1-5)
    # ========================================================================
    (
        orchestration_task,
        readme_task,
        health_task,
        web_research_task,
        quality_task,
    ) = build_research_tasks(
        topic, topic_type, identifier,
        orchestrator, readme_analyst, package_health_validator,
        web_researcher, source_validator
    )
    
    # ========================================================================
    # PHASE 2: Writing Tasks (6-11)
    # ========================================================================
    # In standard mode, we use task.context to link tasks
    # instead of string injection used in optimized mode
    
    # Task 6: Content Planning
    planning_task = Task(
        description=f"""
        Create detailed blog outline for: {topic.title}
        
        CRITICAL INSTRUCTION: 
        You MUST use the EXACT version number found by the 'Package Health Validator' in the context. 
        If the validator reports version 3.x, DO NOT use version 1.x or outdated data.
        
        Based on validated research from the quality task, create structure:
        
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
            - Resources (if URLs available in research)
        
        CRITICAL:
        • Use version from validation ONLY
        • Note deprecated features to AVOID
        • Mark web-sourced content for verification
        """,
        expected_output="Detailed blog outline (300+ words)",
        agent=content_planner,
        context=[quality_task],
    )
    
    # Task 7: Technical Writing
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
    
    # Task 8: Code Validation
    validation_task = Task(
        description="""
        Validate ALL Python code blocks in the article.

        For EACH code block, check:

        1. **Syntax**
        - Parse with Python AST (check for basic syntax errors).

        2. **Semantic Reality Check (CRITICAL)**
        - Do the imported classes and functions *actually exist* in the library?
        - **FAIL** any code that invents convenient but non-existent APIs.

        3. **Imports**
        - Are all used modules imported?

        4. **Variables**
        - Are all variables defined before use?
        - No placeholders (TODO, ..., your_X).

        5. **Deprecations**
        - Flag any deprecated APIs based on package health report.

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
    
    # Task 9: Code Fixing
    fixing_task = Task(
        description="""
        Fix ALL code issues found by the validator.

        CRITICAL RULES:

        1) If validation report says PASS:
           → Return the article from the writer EXACTLY as-is
           → Do NOT modify anything

        2) If validation report lists issues:
           → Fix ONLY the reported problems

        3) Never switch frameworks or add new examples

        STRICT OUTPUT RULES:
        • Return ONLY the complete corrected article body as Markdown.
        • Do NOT wrap the entire answer in ``` or code fences.
        • Only use ```python around individual code examples.
        • Do NOT add preambles like "Here is...".
        • Do NOT add comments after the article.
        """,
        expected_output="Complete corrected article (1200+ words)",
        agent=code_fixer,
        context=[writing_task, validation_task],
    )
    
    # Task 10: Content Editing
    editing_task = Task(
        description="""
        Apply minimal Markdown formatting to improve readability.

        YOU MUST NOT:
        - Delete any text
        - Add new content
        - Paraphrase or rewrite
        - Change code
        - Reorder sections

        YOU MAY:
        - Normalize spacing (1 line before/after headings and code)
        - Convert **bold** headings to ## ATX headings
        - Add language tags to code blocks

        OUTPUT:
        - Complete article with same content, cleaner formatting
        - No preambles, no code fences around entire article
        """,
        expected_output="Same article with improved formatting",
        agent=content_editor,
        context=[fixing_task],
    )
    
    # Task 11: Metadata Publishing
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
        • Title: Clear, specific, includes main keyword from "{topic.title}"
        • Excerpt: Summarizes value, optional light CTA
        • Tags: 4-8 relevant tags (lowercase, hyphenated)
        
        Output ONLY valid JSON. No preamble, no extra text.
        """,
        expected_output="JSON metadata object",
        agent=metadata_publisher,
        context=[planning_task, editing_task],
    )
    
    return (
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


def build_standard_crew(topic: Topic) -> Tuple[Crew, Tuple]:
    """
    Build standard monolithic crew with all 11 agents.
    
    PRODUCTION v4.3: Dynamic agent prompts with package_identifier and topic_title.
    
    This creates a single crew that runs all agents sequentially.
    Memory usage: ~9GB peak during execution.
    
    Best for:
    - Local development with sufficient RAM (>10GB)
    - Full debugging and logging
    - Simpler architecture
    
    Args:
        topic: Topic metadata
    
    Returns:
        Tuple of (crew, tasks_tuple)
        - crew: Configured CrewAI Crew object
        - tasks_tuple: Tuple of all 11 tasks
    
    Example:
        >>> topic = select_next_topic()
        >>> crew, tasks = build_standard_crew(topic)
        >>> result = crew.kickoff()
    """
    # Detect topic type and extract identifier
    topic_type, identifier = detect_topic_type(topic)
    
    logger.info("🔧 Building standard crew (11 agents)...")
    logger.info(f"   Topic type: {topic_type}")
    logger.info(f"   Identifier: {identifier}")
    
    # ========================================================================
    # Create All Agents with Dynamic Parameters (v4.3 FIX)
    # ========================================================================
    # Research agents (1-5)
    orchestrator = create_orchestrator(topic.title)
    readme_analyst = create_readme_analyst(identifier)  # ✅ Dynamic
    package_health_validator = create_package_health_validator(identifier)  # ✅ Dynamic
    web_researcher = create_web_researcher(topic.title)  # ✅ Dynamic
    source_validator = create_source_quality_validator()
    
    # Writing agents (6-11)
    content_planner = create_content_planner()
    technical_writer = create_technical_writer()
    code_validator = create_code_validator()
    code_fixer = create_code_fixer()
    content_editor = create_content_editor()
    metadata_publisher = create_metadata_publisher()
    
    logger.info("   ✓ Created 11 agents")
    
    # ========================================================================
    # Build All Tasks
    # ========================================================================
    tasks_tuple = build_all_tasks_standard(
        topic, topic_type, identifier,
        orchestrator, readme_analyst, package_health_validator,
        web_researcher, source_validator, content_planner,
        technical_writer, code_validator, code_fixer,
        content_editor, metadata_publisher
    )
    
    (orchestration_task, readme_task, health_task, web_research_task,
     quality_task, planning_task, writing_task, validation_task,
     fixing_task, editing_task, metadata_task) = tasks_tuple
    
    logger.info("   ✓ Created 11 tasks")
    
    # ========================================================================
    # Assemble Crew
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
            # content_editor,  # Optional: uncomment to enable editing
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
            # editing_task,  # Optional: uncomment to enable editing
            metadata_task,
        ],
        process=Process.sequential,
        verbose=True,
        max_rpm=15,
    )
    
    logger.info("   ✓ Assembled crew")
    logger.info("")
    
    return crew, tasks_tuple


# ============================================================================
# OPTIMIZED MODE - Split-Crew Architecture (Phase 1 + Phase 2)
# ============================================================================

def build_research_crew_optimized(topic: Topic) -> Tuple[Crew, Dict[str, Task]]:
    """
    Build Phase 1: Research Crew (Agents 1-5).
    
    PRODUCTION v4.3: Dynamic agent prompts with package_identifier and topic_title.
    
    Memory-optimized architecture for GitHub workflows.
    This crew handles all research and data gathering.
    
    Memory usage: ~3GB peak during execution.
    
    Agents:
    1. Orchestrator - Strategy decision
    2. README Analyst - Extract documentation
    3. Package Health - Version validation
    4. Web Researcher - Fallback search
    5. Source Validator - Quality rating
    
    Args:
        topic: Topic metadata
    
    Returns:
        Tuple of (crew, tasks_dict)
        - crew: Research crew with 5 agents
        - tasks_dict: Dict mapping task names to Task objects
    
    Example:
        >>> topic = select_next_topic()
        >>> crew, tasks = build_research_crew_optimized(topic)
        >>> result = crew.kickoff()
        >>> research_context = extract_research_data(tasks)
    """
    # Detect topic type and extract identifier
    topic_type, identifier = detect_topic_type(topic)
    
    logger.info("🔧 Building research crew (5 agents)...")
    logger.info(f"   Topic type: {topic_type}")
    logger.info(f"   Identifier: {identifier}")
    
    # ========================================================================
    # Create Research Agents with Dynamic Parameters (v4.3 FIX)
    # ========================================================================
    orchestrator = create_orchestrator(topic.title)
    readme_analyst = create_readme_analyst(identifier)  # ✅ Dynamic
    package_health_validator = create_package_health_validator(identifier)  # ✅ Dynamic
    web_researcher = create_web_researcher(topic.title)  # ✅ Dynamic
    source_validator = create_source_quality_validator()
    
    logger.info("   ✓ Created 5 research agents")
    
    # ========================================================================
    # Build Research Tasks
    # ========================================================================
    (orchestration_task, readme_task, health_task,
     web_research_task, quality_task) = build_research_tasks(
        topic, topic_type, identifier,
        orchestrator, readme_analyst, package_health_validator,
        web_researcher, source_validator
    )
    
    logger.info("   ✓ Created 5 research tasks")
    
    # ========================================================================
    # Assemble Research Crew
    # ========================================================================
    crew = Crew(
        agents=[
            orchestrator,
            readme_analyst,
            package_health_validator,
            web_researcher,
            source_validator,
        ],
        tasks=[
            orchestration_task,
            readme_task,
            health_task,
            web_research_task,
            quality_task,
        ],
        process=Process.sequential,
        verbose=True,
        max_rpm=15,
    )
    
    logger.info("   ✓ Assembled research crew")
    logger.info("")
    
    return crew, {
        "orchestration": orchestration_task,
        "readme": readme_task,
        "health": health_task,
        "web": web_research_task,
        "quality": quality_task,
    }


def build_writing_crew_optimized_old(
    topic: Topic,
    research_context: str
) -> Tuple[Crew, Dict[str, Task]]:
    """
    Build Phase 2: Writing Crew (Agents 6-11).
    
    Memory-optimized architecture for GitHub workflows.
    This crew handles content generation using research context string.
    
    Memory usage: ~5GB peak during execution.
    
    Agents:
    6. Content Planner - Create outline
    7. Technical Writer - Write article
    8. Code Validator - Check code quality
    9. Code Fixer - Fix issues
    10. Content Editor - Polish formatting
    11. Metadata Publisher - Generate SEO data
    
    Args:
        topic: Topic metadata
        research_context: Research data as string (from Phase 1)
    
    Returns:
        Tuple of (crew, tasks_dict)
        - crew: Writing crew with 6 agents
        - tasks_dict: Dict mapping task names to Task objects
    
    Example:
        >>> crew, tasks = build_writing_crew_optimized(topic, research_context)
        >>> result = crew.kickoff()
        >>> body = extract_task_output(tasks["fixing"], "fixer")
    """
    logger.info("🔧 Building writing crew (6 agents)...")
    
    # ========================================================================
    # Create Writing Agents Only
    # ========================================================================
    content_planner = create_content_planner()
    technical_writer = create_technical_writer()
    code_validator = create_code_validator()
    code_fixer = create_code_fixer()
    content_editor = create_content_editor()
    metadata_publisher = create_metadata_publisher()
    
    logger.info("   ✓ Created 6 writing agents")
    
    # ========================================================================
    # Build Writing Tasks with Injected Research Context
    # ========================================================================
    (planning_task, writing_task, validation_task,
     fixing_task, editing_task, metadata_task) = build_writing_tasks(
        topic, research_context,
        content_planner, technical_writer, code_validator,
        code_fixer, content_editor, metadata_publisher
    )
    
    logger.info("   ✓ Created 6 writing tasks")
    
    # ========================================================================
    # Assemble Writing Crew
    # ========================================================================
    crew = Crew(
        agents=[
            content_planner,
            technical_writer,
            code_validator,
            code_fixer,
            # content_editor,  # Optional: uncomment to enable editing
            metadata_publisher,
        ],
        tasks=[
            planning_task,
            writing_task,
            validation_task,
            fixing_task,
            # editing_task,  # Optional: uncomment to enable editing
            metadata_task,
        ],
        process=Process.sequential,
        verbose=True,
        max_rpm=15,
    )
    
    logger.info("   ✓ Assembled writing crew")
    logger.info("")
    
    return crew, {
        "planning": planning_task,
        "writing": writing_task,
        "validation": validation_task,
        "fixing": fixing_task,
        "editing": editing_task,
        "metadata": metadata_task,
    }


def build_writing_crew_optimized(
    topic: Topic,
    research_context: str
) -> Tuple[Crew, Dict[str, Task]]:
    """
    Build Phase 2: Writing Crew (Agents 6-11) with dynamic prompts.
    
    PRODUCTION v4.4.2: Enhanced with topic-specific prompts and quality awareness.
    
    Memory-optimized architecture for GitHub workflows.
    This crew handles content generation using research context string.
    
    Memory usage: ~5GB peak during execution.
    
    Agents:
    6. Content Planner - Create outline (topic-aware)
    7. Technical Writer - Write article (topic + quality aware)
    8. Code Validator - Check code quality (topic + API verification)
    9. Code Fixer - Fix issues (topic-aware)
    10. Content Editor - Polish formatting (topic-aware)
    11. Metadata Publisher - Generate SEO data (topic-aware)
    
    Args:
        topic: Topic metadata (includes title, tags, summary)
        research_context: Research data as string (from Phase 1)
    
    Returns:
        Tuple of (crew, tasks_dict)
        - crew: Writing crew with 6 agents
        - tasks_dict: Dict mapping task names to Task objects
    
    Example:
        >>> topic = select_next_topic()
        >>> research_context = "# RESEARCH CONTEXT: pandas..."
        >>> crew, tasks = build_writing_crew_optimized(topic, research_context)
        >>> result = crew.kickoff()
        >>> body = extract_task_output(tasks["fixing"], "fixer")
    """
    logger.info("🔧 Building writing crew (6 agents)...")
    
    # ========================================================================
    # Extract Quality Score from Research Context
    # ========================================================================
    import re
    quality_match = re.search(r'Quality Score[:\s]+([A-F])', research_context)
    quality_score = quality_match.group(1) if quality_match else "B"
    
    logger.info(f"   Quality Score: {quality_score}")
    logger.info(f"   Topic: {topic.title}")
    
    # ========================================================================
    # Create Writing Agents with Dynamic Parameters (v4.4.2)
    # ========================================================================
    content_planner = create_content_planner(topic.title)  # ✅ Dynamic
    technical_writer = create_technical_writer(topic.title, quality_score)  # ✅ Dynamic + Quality-aware
    code_validator = create_code_validator(topic.title)  # ✅ Dynamic + API verification
    code_fixer = create_code_fixer(topic.title)  # ✅ Dynamic
    content_editor = create_content_editor(topic.title)  # ✅ Dynamic
    metadata_publisher = create_metadata_publisher(topic.title)  # ✅ Dynamic
    
    logger.info("   ✓ Created 6 writing agents (dynamic prompts)")
    
    # ========================================================================
    # Build Writing Tasks with Injected Research Context
    # ========================================================================
    (planning_task, writing_task, validation_task,
     fixing_task, editing_task, metadata_task) = build_writing_tasks(
        topic, research_context,
        content_planner, technical_writer, code_validator,
        code_fixer, content_editor, metadata_publisher
    )
    
    logger.info("   ✓ Created 6 writing tasks (topic-specific)")
    
    # ========================================================================
    # Assemble Writing Crew
    # ========================================================================
    crew = Crew(
        agents=[
            content_planner,
            technical_writer,
            code_validator,
            code_fixer,
            # content_editor,  # Optional: uncomment to enable editing
            metadata_publisher,
        ],
        tasks=[
            planning_task,
            writing_task,
            validation_task,
            fixing_task,
            # editing_task,  # Optional: uncomment to enable editing
            metadata_task,
        ],
        process=Process.sequential,
        verbose=True,
        max_rpm=15,
    )
    
    logger.info("   ✓ Assembled writing crew")
    logger.info(f"   ✓ Configuration: {topic.title} @ Quality {quality_score}")
    logger.info("")
    
    return crew, {
        "planning": planning_task,
        "writing": writing_task,
        "validation": validation_task,
        "fixing": fixing_task,
        "editing": editing_task,
        "metadata": metadata_task,
    }


# ============================================================================
# MEMORY MANAGEMENT UTILITIES
# ============================================================================

def cleanup_phase_memory(crew, tasks, result) -> int:
    """
    Cleanup memory after Phase 1 (research).
    
    This is critical for the memory-optimized pipeline.
    Explicitly deletes Phase 1 objects and forces garbage collection.
    
    Args:
        crew: Research crew object to delete
        tasks: Research tasks dict to delete
        result: CrewAI result object to delete
    
    Returns:
        Number of objects collected by garbage collector
    
    Example:
        >>> collected = cleanup_phase_memory(research_crew, research_tasks, result)
        >>> logger.info(f"Cleaned up {collected} objects")
    """
    logger.info("🧹 Clearing Phase 1 Memory...")
    
    # Explicitly delete objects
    del crew
    del tasks
    del result
    
    # Force garbage collection
    collected = gc.collect()
    
    logger.info(f"   ✓ Garbage collected: {collected} objects")
    
    return collected


def estimate_memory_usage(mode: str = "standard") -> dict:
    """
    Estimate memory usage for different modes.
    
    Args:
        mode: 'standard' or 'optimized'
    
    Returns:
        Dict with memory estimates
    
    Example:
        >>> estimates = estimate_memory_usage("optimized")
        >>> print(f"Peak RAM: {estimates['peak_ram_gb']}GB")
    """
    if mode == "standard":
        return {
            "mode": "standard",
            "agents": 11,
            "peak_ram_gb": 9.0,
            "recommended_ram_gb": 12.0,
            "phases": 1,
            "description": "All agents loaded simultaneously",
        }
    else:
        return {
            "mode": "optimized",
            "agents": 11,
            "peak_ram_gb": 5.0,
            "recommended_ram_gb": 7.0,
            "phases": 2,
            "phase_1_ram_gb": 3.0,
            "phase_2_ram_gb": 5.0,
            "description": "Split-crew with garbage collection",
        }


# ============================================================================
# VALIDATION & DEBUGGING
# ============================================================================

def validate_crew_configuration(crew: Crew) -> bool:
    """
    Validate crew configuration before execution.
    
    Args:
        crew: CrewAI Crew object
    
    Returns:
        True if valid, False otherwise
    """
    try:
        assert len(crew.agents) > 0, "No agents in crew"
        assert len(crew.tasks) > 0, "No tasks in crew"
        assert len(crew.agents) == len(crew.tasks), "Agent/task count mismatch"
        
        for agent in crew.agents:
            assert hasattr(agent, 'role'), f"Agent missing role"
            assert hasattr(agent, 'llm'), f"Agent missing LLM"
        
        for task in crew.tasks:
            assert hasattr(task, 'description'), "Task missing description"
            assert hasattr(task, 'agent'), "Task missing agent"
        
        logger.info("✅ Crew configuration valid")
        return True
        
    except AssertionError as e:
        logger.error(f"❌ Crew configuration invalid: {e}")
        return False


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Standard mode
    "build_standard_crew",
    "build_all_tasks_standard",
    
    # Optimized mode
    "build_research_crew_optimized",
    "build_writing_crew_optimized",
    "cleanup_phase_memory",
    
    # Utilities
    "estimate_memory_usage",
    "validate_crew_configuration",
]