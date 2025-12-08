"""
Writing Phase Tasks (Tasks 6-11) - Phase 2 of Split-Crew Architecture

These tasks handle the writing phase:
6. Content Planning - Create outline
7. Technical Writing - Write article
8. Code Validation - Check code quality
9. Code Fixing - Fix issues
10. Content Editing - Polish formatting
11. Metadata Publishing - Generate SEO data
"""
from typing import Tuple
from crewai import Task, Agent  # type: ignore

from blog_generator.core.models import Topic


def build_writing_tasks(
    topic: Topic,
    research_context: str,
    content_planner: Agent,
    technical_writer: Agent,
    code_validator: Agent,
    code_fixer: Agent,
    content_editor: Agent,
    metadata_publisher: Agent,
) -> Tuple[Task, Task, Task, Task, Task, Task]:
    """
    Build all writing phase tasks (Tasks 6-11)
    
    Args:
        topic: Topic metadata
        research_context: Research data from Phase 1 as string
        content_planner: Agent 6
        technical_writer: Agent 7
        code_validator: Agent 8
        code_fixer: Agent 9
        content_editor: Agent 10
        metadata_publisher: Agent 11
    
    Returns:
        Tuple of 6 tasks
    """
    
    # Task 6: Content Planning
    planning_task = Task(
        description=f"""
        Create detailed blog outline for: {topic.title}
        
        CRITICAL INSTRUCTION: 
        You MUST use the EXACT version number found by the 'Package Health Validator' in the context. 
        If the validator reports version 3.x, DO NOT use version 1.x or outdated data.
        
        RESEARCH CONTEXT (from Phase 1):
        {research_context}
        
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
    )
    
    # Task 7: Technical Writing
    writing_task = Task(
        description=f"""
        Write a Markdown blog article about: {topic.title}

        Use ONLY the information from the research context and outline.
        Do NOT invent new libraries, versions, datasets, or APIs.

        RESEARCH CONTEXT (from Phase 1):
        {research_context}

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
        context=[planning_task],
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
        context=[writing_task],
    )
    
    # Task 9: Code Fixing
    fixing_task = Task(
        description="""
        Fix ALL code issues found by the validator.

        For each issue reported in the validation report:
        • Add missing imports for modules that are already used
        • Define undefined variables in the simplest way consistent with nearby code
        • Remove or replace placeholders (TODO, ..., your_X) with working code
        • Fix syntax errors
        • Replace deprecated features using the research context

        CRITICAL RULES:

        1) If validation report says PASS:
           → Return the article from the writer EXACTLY as-is
           → Do NOT modify anything
           → Do NOT add preamble or commentary

        2) If validation report lists issues:
           → Fix ONLY the reported problems
           → Keep all other content unchanged

        3) Never switch to a different framework or library
        4) Never add examples that change the main topic
        5) Keep structure and narrative the same

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
    
    # Task 10: Content Editing
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
    
    return (
        planning_task,
        writing_task,
        validation_task,
        fixing_task,
        editing_task,
        metadata_task,
    )