"""
Writing Phase Tasks (Tasks 6-11) - Phase 2 of Split-Crew Architecture - PRODUCTION v4.4.2

IMPROVEMENTS:
- Dynamic prompts with topic name
- Enhanced API verification
- Code duplication prevention
- Low-quality content handling
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
    Build all writing phase tasks (Tasks 6-11) with dynamic prompts
    
    CHANGES v4.4.2:
    - All prompts use topic.title dynamically
    - Enhanced validation for API correctness
    - Code duplication detection
    - Low-quality content protocols
    """
    
    # Extract quality score from research context if available
    import re
    quality_match = re.search(r'Quality Score[:\s]+([A-F])', research_context)
    quality_score = quality_match.group(1) if quality_match else "B"
    
    # Task 6: Content Planning
    planning_task = Task(
        description=f"""
        Create detailed blog outline for: {topic.title}
        
        CRITICAL INSTRUCTIONS:
        1. Use EXACT version from 'Package Health Validator' in context
        2. If validator reports version 3.x, DO NOT use 1.x or outdated data
        3. Mark which sections have actual code examples available
        4. Ensure each code example demonstrates DIFFERENT functionality
        
        RESEARCH CONTEXT (from Phase 1):
        {research_context}
        
        OUTLINE STRUCTURE:
        
        1. **Introduction** (150 words)
            - What is {topic.title}?
            - Why {topic.title} matters
            - What readers will learn about {topic.title}
        
        2. **Overview** (200 words)
            - Key features of {topic.title}
            - Use cases for {topic.title}
            - Current version: [EXACT from validation]
        
        3. **Getting Started** (250 words)
            - Installation for {topic.title}
            - Quick example (complete, runnable code)
            - Mark if example available in research: [YES/NO]
        
        4. **Core Concepts** (300 words)
            - Main functionality of {topic.title}
            - API overview for {topic.title}
            - Example usage patterns
        
        5. **Practical Examples** (400 words)
            - Example 1: [Specific use case #1]
              * Mark if available: [YES/NO]
              * If YES: Note what it demonstrates
            - Example 2: [Different use case #2]
              * Mark if available: [YES/NO]
              * If YES: Note what it demonstrates differently
            - Each with COMPLETE, DISTINCT code
        
        6. **Best Practices** (150 words)
            - Tips for using {topic.title}
            - Recommendations for {topic.title}
            - Common pitfalls with {topic.title}
        
        7. **Conclusion** (100 words)
            - Summary of {topic.title} key points
            - Next steps for {topic.title} users
            - Resources:
              * If quality report has Markdown links with URLs:
                → Format as [Descriptive Name](URL)
                → Include top 1-2 most relevant
              * If NO URLs in research:
                → Omit Resources subsection entirely
        
        QUALITY-BASED INSTRUCTIONS:
        - If code examples limited: Note which sections need conceptual explanations
        - If version unclear: Mark for writer to add disclaimer
        - Mark deprecated features to AVOID
        
        OUTPUT:
        - Detailed Markdown outline
        - Clear markers for available vs. needed content
        - No commentary
        """,
        expected_output=(
            f"Detailed blog outline in Markdown for {topic.title} with:\n"
            "• Section 1: Introduction (150 words outline)\n"
            "• Section 2: Overview with version info (200 words outline)\n"
            "• Section 3: Getting Started with code availability marked (250 words outline)\n"
            "• Section 4: Core Concepts (300 words outline)\n"
            "• Section 5: Practical Examples with 2 DISTINCT use cases marked (400 words outline)\n"
            "• Section 6: Best Practices (150 words outline)\n"
            "• Section 7: Conclusion with conditional Resources (100 words outline)\n"
            "Total outline: 300+ words minimum"
        ),
        agent=content_planner,
    )
    
    # Task 7: Technical Writing
    writing_task = Task(
        description=f"""
        Write a complete Markdown blog article about: {topic.title}

        ⚠️ CRITICAL OUTPUT REQUIREMENT:
        You MUST output ACTUAL ARTICLE CONTENT starting with "## Introduction".
        DO NOT output meta-comments like "Your final answer must be..." or "Here is the article...".
        The FIRST LINE of your output must be: ## Introduction

        RESEARCH CONTEXT (from Phase 1):
        {research_context}

        CONTENT RULES:
        - Topic focus: {topic.title} ONLY
        - Use ONLY information from research context and outline
        - Do NOT invent libraries, versions, datasets, or APIs
        - If code examples limited, use conceptual explanations with disclaimers
        - Quality level: {quality_score} (check context for specific instructions)

        STRUCTURE REQUIREMENTS (exact sections):
        
        1. ## Introduction
           - Explain what {topic.title} is
           - Why {topic.title} matters
           - What readers learn about {topic.title}
           - Target: 150-200 words
        
        2. ## Overview
           - Key features of {topic.title} (bullet points)
           - Use cases for {topic.title}
           - Current version of {topic.title} (from research)
           - Target: 200-250 words
        
        3. ## Getting Started
           - Installation for {topic.title}
           - One complete, runnable code example for {topic.title}
           - If no code available: installation + disclaimer
           - Target: 250-300 words
        
        4. ## Core Concepts
           - Main functionality of {topic.title}
           - API overview of {topic.title}
           - How {topic.title} works conceptually
           - Target: 300-350 words
        
        5. ## Practical Examples
           - Example 1: [Use case] with {topic.title}
           - Example 2: [Different use case] with {topic.title}
           - Each must be SELF-CONTAINED and DISTINCT
           - Each must demonstrate DIFFERENT functionality
           - Target: 400-500 words
        
        6. ## Best Practices
           - Tips for {topic.title}
           - Recommendations for {topic.title}
           - Common pitfalls with {topic.title}
           - Target: 150-200 words
        
        7. ## Conclusion
           - Summary of {topic.title} key points
           - Next steps for learning {topic.title}
           - Resources (only if URLs in research context)
           - Target: 100-150 words

        FORMATTING RULES:
        - ## for main sections, ### for subsections
        - NO ===, --- or **bold** for headings
        - NO wrapping entire article in ``` code block
        - ```python for Python code
        - ```bash for shell commands

        CODE REQUIREMENTS (ANTI-HALLUCINATION):
        - Article about: {topic.title}
        - Code MUST use {topic.title} API or related official modules
        - Each code block: complete, runnable, self-contained
        - All imports at top of each block
        - All variables defined before use
        - NO placeholders (TODO, ..., your_X, YOUR_API_KEY)
        - **CRITICAL**: Use ONLY code patterns from research context
        - If uncertain about API: Use conceptual pseudo-code with disclaimer:
```python
          # Conceptual example for {topic.title} - verify with official docs
          from {topic.title} import main_function
          # ...
```
          > **Note**: Verify API with official documentation.

        CODE EXAMPLE DIFFERENTIATION:
        - Example 1 and Example 2 must be >75% different
        - Vary: use cases, inputs, parameters, processing, outputs
        - ❌ Same code with only comments changed
        - ✅ Distinct scenarios showing different features of {topic.title}

        TONE:
        - Professional and clear about {topic.title}
        - No first-person ("I", "we", "let's")
        - No AI meta-comments
        - No commentary like "This article will..."

        OUTPUT FORMAT (CRITICAL):
        - Start immediately with: ## Introduction
        - NO preamble before article
        - NO "Here is the article..." or similar
        - NO "Final Answer:" or meta-text
        - ONLY the article content in raw Markdown
        - Minimum 1200 words total about {topic.title}
        """,
        expected_output=(
            f"Complete Markdown blog article about {topic.title} with:\n"
            "1. ## Introduction (150-200 words)\n"
            "2. ## Overview (200-250 words with bullet points)\n"
            "3. ## Getting Started (250-300 words with installation + 1 code example)\n"
            "4. ## Core Concepts (300-350 words)\n"
            "5. ## Practical Examples (400-500 words with 2 DISTINCT, COMPLETE code examples)\n"
            "6. ## Best Practices (150-200 words)\n"
            "7. ## Conclusion (100-150 words with conditional Resources)\n\n"
            f"CRITICAL: Article MUST start with '## Introduction' as first line.\n"
            "No preamble, no meta-text, no 'Here is...'. Just article content."
        ),
        agent=technical_writer,
        context=[planning_task],
    )
    
    # Task 8: Code Validation
    validation_task = Task(
        description=f"""
        Validate ALL Python code blocks in the {topic.title} article.

        ARTICLE TOPIC: {topic.title}

        For EACH code block, check:

        1. **Library API Verification (CRITICAL)**
        - Article is about: {topic.title}
        - Code MUST import from {topic.title} or related official modules
        - **FAIL** if code uses a DIFFERENT library's API
        
        Example checks:
        ✅ Article: "{topic.title}", Code: `from {topic.title} import ...` → PASS
        ❌ Article: "bert-score", Code: `from transformers import BertModel` → FAIL
        
        If wrong library detected, report:
        "Block X: Uses [wrong_library] but article is about {topic.title}.
         Must use actual {topic.title} API."

        2. **Syntax Check**
        - Parse with Python AST for syntax errors

        3. **Semantic Reality Check**
        - Do imported classes/functions *actually exist* in {topic.title}?
        - **FAIL** invented APIs (e.g., `{topic.title}.ImaginaryClass`)
        - Compare against README/Health Report in research context

        4. **Imports Check**
        - All used modules imported?
        - Imports consistent with {topic.title}?

        5. **Variables Check**
        - All variables defined before use?
        - No placeholders (TODO, ..., your_X)?

        6. **Deprecation Check**
        - Flag deprecated APIs from package health report

        7. **Code Duplication Check**
        - Compare code blocks pairwise
        - If 2+ blocks are >90% identical:
          "Blocks X and Y are nearly identical (>90% similar).
           Each example should demonstrate DIFFERENT {topic.title} functionality:
           • Different use cases
           • Different parameters or configurations
           • Different features of {topic.title}
           Not just different comments or variable names."

        OUTPUT FORMAT (plain text):

        Validation Result: [PASS / FAIL]
        Code Blocks Checked: [count]
        Article Topic: {topic.title}
        
        Issues Found:
        [If FAIL, list specific issues]
        Block 1:
        • [Issue description with fix suggestion]
        
        Block 2:
        • [Issue description with fix suggestion]
        
        If no issues: "All blocks passed validation for {topic.title} article."
        """,
        expected_output=(
            f"Code validation report for {topic.title} with:\n"
            "• Validation Result: PASS or FAIL\n"
            "• Code Blocks Checked: [number]\n"
            f"• Library API verification for {topic.title}\n"
            "• Duplication check between examples\n"
            "• Issues Found: [detailed list if FAIL, or 'None' if PASS]\n"
            "Format: Plain text report, not Markdown"
        ),
        agent=code_validator,
        context=[writing_task],
    )
    
    # Task 9: Code Fixing
    fixing_task = Task(
        description=f"""
        Fix ALL code issues in the {topic.title} article found by validator.

        ARTICLE TOPIC: {topic.title}

        For each issue reported:
        • Add missing imports for {topic.title}
        • Define undefined variables
        • Remove placeholders (TODO, ..., your_X)
        • Fix syntax errors
        • Replace deprecated {topic.title} features
        • If wrong library API used:
          * Convert to correct {topic.title} API using research context
          * If uncertain, use conceptual pseudo-code with disclaimer

        CRITICAL RULES:

        1) If validation report says PASS:
           → Return article EXACTLY as-is
           → Do NOT modify anything
           → Do NOT add preamble

        2) If validation lists issues:
           → Fix ONLY reported problems
           → Keep all other content unchanged

        3) Topic constraints:
           • Never switch from {topic.title} to different library
           • Never change main topic from {topic.title}
           • Keep structure and narrative same

        STRICT OUTPUT RULES:
        • Return ONLY complete corrected article body as Markdown
        • Do NOT wrap entire answer in ``` fences
        • Only use ```python for individual code examples
        • Do NOT add preambles like "Here is..."
        • Do NOT add comments after article

        Return COMPLETE corrected {topic.title} article in raw Markdown.
        """,
        expected_output=(
            f"Complete corrected article about {topic.title} in raw Markdown:\n"
            "• If validation PASSED: Exact copy of original article\n"
            "• If validation FAILED: Article with ONLY reported issues fixed\n"
            "• Must start with '## Introduction'\n"
            "• Must contain all 7 sections\n"
            "• Minimum 1200 words\n"
            "• NO preamble, NO meta-text, NO code fences wrapping entire article"
        ),
        agent=code_fixer,
        context=[writing_task, validation_task],
    )
    
    # Task 10: Content Editing
    editing_task = Task(
        description=f"""
        Apply minimal Markdown formatting to the {topic.title} article.

        GOAL:
        - Improve readability by adjusting SPACING and MARKDOWN SYNTAX ONLY
        - Content about {topic.title} must remain EXACTLY the same

        YOU MUST NOT:
        - Delete text (sentences, bullets, sections)
        - Add new explanations or text
        - Paraphrase or rewrite
        - Change numbers, versions, function names, URLs
        - Change code inside ``` fences
        - Change order of paragraphs or sections

        YOU MAY:
        - Normalize spacing:
          * One blank line before/after headings
          * One blank line before/after code blocks
          * Remove excessive empty lines (>2 in a row)
        
        - Normalize headings:
          * Main sections MUST use ## (level 2):
            ## Introduction
            ## Overview
            ## Getting Started
            ## Core Concepts
            ## Practical Examples
            ## Best Practices
            ## Conclusion
          * Subsections use ### (level 3)
          * Convert **bold headings** to ## ATX style
          * Keep same words, adjust syntax only
        
        - Normalize code blocks:
          * Add language tags (```python, ```bash)
          * Do NOT modify code content itself

        ABSOLUTE FORMAT RULES:
        - First line MUST be heading or paragraph from original
          (no "Here is...", no "Final Answer:")
        - NEVER wrap entire article in ``` fence
        - Only use fenced blocks for individual code
        - NEVER add text before or after article

        Return COMPLETE {topic.title} article with same content, cleaner formatting.
        """,
        expected_output=(
            f"Article about {topic.title} with improved formatting:\n"
            "• Same content, words, and structure as input\n"
            "• Normalized spacing (1 line before/after headings and code blocks)\n"
            "• Consistent ATX headings (## for main sections, ### for subsections)\n"
            "• Code blocks with language tags\n"
            "• NO content changes, NO rewriting, NO deletions\n"
            "• Must start with '## Introduction'\n"
            "• NO preamble, NO meta-text"
        ),
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
        
        REQUIREMENTS:
        • Title: Must include "{topic.title}" keyword, ≤70 characters
        • Excerpt: Summarize value of {topic.title} content, ≤200 characters
        • Tags: 4-8 relevant tags for {topic.title} ecosystem (lowercase, hyphenated)
        
        Example formats:
        {{
        "title": "{topic.title}: Complete Guide with Python Examples",
        "excerpt": "Learn {topic.title} with complete code examples, best practices, and real-world use cases.",
        "tags": ["python", "{topic.title.lower().replace(' ', '-')}", "data-science", "tutorial"]
        }}
        
        CONSTRAINTS:
        • Focus ONLY on {topic.title} - no unrelated libraries/frameworks
        • Keep title concise (≤70 characters) focused on {topic.title}
        • Keep excerpt ≤200 characters, avoid marketing fluff
        • Tags must be directly relevant to {topic.title} and its ecosystem
        
        Output ONLY valid JSON. No preamble, no explanation, no extra text.
        """,
        expected_output=(
            f"Valid JSON object for {topic.title} with exactly 3 keys:\n"
            '{"title": "...", "excerpt": "...", "tags": [...]}\n'
            f"• title: Includes '{topic.title}', ≤70 characters\n"
            "• excerpt: ≤200 characters\n"
            f"• tags: 4-8 lowercase-hyphenated strings relevant to {topic.title}\n"
            "• NO preamble, NO explanation, ONLY JSON"
        ),
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