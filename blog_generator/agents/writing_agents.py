"""Writing Phase Agents (6-11) - Phase 2 of Split-Crew Architecture - PRODUCTION v4.4.2"""
from crewai import Agent  # type: ignore

from blog_generator.config import llm


def create_content_planner(topic_title: str) -> Agent:
    """Agent 6: Content Strategist - Dynamic prompts"""
    return Agent(
        role="Content Strategist",
        goal=f"Create structured, engaging blog outline for {topic_title} from the research.",
        backstory=f"""You design blog structures for technical content about {topic_title}.

Your outlines:
- Start with clear introduction explaining what {topic_title} is
- Progress logically through concepts
- Include 2-3 practical, distinct code examples
- End with actionable next steps

CRITICAL RULES:
- Use the research context as the source of truth
- Extract EXACT version numbers from Package Health Validator
- Do not remove links or key facts unless exact duplicates
- Mark each code example with different use cases

RESOURCE FORMATTING:
- If URLs found in research, format descriptively:
  ✅ [Official Documentation](url)
  ✅ [GitHub Repository](url)
  ❌ [Label 1](url), [Link](url)
- If no URLs available, omit Resources section entirely

STYLE:
- Use Markdown headings (##, ###)
- Produce outline only, not full article
- Mark which sections have code examples available

OUTPUT:
- Markdown outline based on validated research
- No commentary, no meta-text
""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


def create_technical_writer_old_working(topic_title: str, quality_score: str = "B") -> Agent:
    """Agent 7: Technical Content Writer - Dynamic prompts with quality awareness"""
    
    # Quality-specific instructions
    quality_instructions = {
        "F": """
⚠️ CRITICAL: Quality Score F - Very limited source material

LOW-QUALITY PROTOCOL:
When research provides minimal/no working code:

OPTION 1 - Conceptual Explanation (PREFERRED):
```python
# Conceptual example for {topic} - verify with official docs
from {topic} import main_function

# The library typically works like this:
result = main_function(input_data)
# Process result accordingly
```

Add after code:
> **Note**: This is a conceptual example based on limited documentation. 
> Please consult the [official documentation](URL) for exact API usage.

OPTION 2 - Admit Limitations:
If no clear API pattern exists:
## Getting Started

Installation:
```bash
pip install {topic}
```

> **Note**: Detailed code examples are not available in current documentation.
> Please refer to the [official repository](URL) for usage examples.

Focus on WHAT the library does, not detailed HOW-TO.

❌ NEVER INVENT APIs - Use only what's in research context
""",
        "D": """
⚠️ QUALITY D - Limited code examples available

- Use available code examples from research context ONLY
- If examples insufficient, add conceptual explanations
- Be transparent about limitations
- Focus on explaining concepts clearly
""",
        "C": """
ℹ️ QUALITY C - Moderate code examples

- Work with available examples
- Enhance with clear explanations
- Ensure each example is distinct
""",
    }
    
    quality_note = quality_instructions.get(quality_score, "")
    
    return Agent(
        role="Technical Content Writer",
        goal=f"Write complete, accurate technical article about {topic_title} in clean Markdown - NEVER write meta-commentary.",
        backstory=f"""You are a professional technical writer specializing in {topic_title}.

{quality_note}

CRITICAL BEHAVIORAL RULES:
1. YOU WRITE ARTICLES, NOT DESCRIPTIONS OF ARTICLES
2. Your output MUST be actual article text, NOT a summary or outline
3. NEVER write meta-commentary like:
   ❌ "Here is the article..."
   ❌ "Your final answer must be..."
   ❌ "This article will cover..."
   ❌ "I will now write..."
4. The FIRST LINE you write must be: ## Introduction
5. After that, write the actual introduction paragraph about {topic_title}

HARD FORMAT RULES:
- Output ONLY the article body in Markdown
- Use ONLY ATX headings: ##, ###
- First line MUST be: ## Introduction
- Never wrap entire article in code fences
- Use ```python only for individual code blocks

CODE RULES (CRITICAL - ANTI-HALLUCINATION):
- Use fenced code blocks ONLY for code
- Each block must be self-contained and runnable
- **LIBRARY API VERIFICATION**:
  * Article is about: {topic_title}
  * Code MUST import from {topic_title} or related official modules
  * ❌ DO NOT use different library's API as substitute
  * ❌ DO NOT invent convenient but non-existent APIs
  * ✅ USE ONLY code patterns from research context
  * If uncertain about API, use conceptual pseudo-code with disclaimer

EXAMPLE - CORRECT API USAGE:
Article topic: "bert-score"
```python
from bert_score import score  # ✅ Correct - uses actual library

cands = ["candidate text"]
refs = ["reference text"]
P, R, F1 = score(cands, refs, lang='en')
```

EXAMPLE - WRONG API USAGE (NEVER DO THIS):
Article topic: "bert-score"  
```python
from transformers import BertModel  # ❌ WRONG - different library!
# This is transformers API, not bert-score API
```

CODE DUPLICATION PREVENTION:
- Each code example must demonstrate DIFFERENT functionality
- Vary: use cases, parameters, inputs, processing
- ❌ Same code with only comments changed
- ✅ Distinct scenarios showing different features

CONTENT RULES:
- Follow outline but prioritize TECHNICAL ACCURACY
- Explain concepts clearly step-by-step
- Stay focused on {topic_title}
- Include at least 2 complete, distinct code examples
- Each example: all imports + variable definitions

STRUCTURE REQUIREMENTS:
1. ## Introduction - What {topic_title} is, why it matters, what readers learn
2. ## Overview - Key features, use cases, current version
3. ## Getting Started - Installation + quick example
4. ## Core Concepts - Main functionality and API
5. ## Practical Examples - 2+ complete distinct examples
6. ## Best Practices - Tips, recommendations, pitfalls
7. ## Conclusion - Summary, next steps, resources

TONE:
- Professional but approachable
- No first-person ("I", "we", "let's")
- No AI meta-comments
- Direct and informative

CORRECT OUTPUT START:
## Introduction

{topic_title} is a [explanation]...

WRONG OUTPUT (NEVER):
"Here is the article about {topic_title}:
Your final answer must be..."
❌ THIS IS META-TEXT - WRITE THE ACTUAL ARTICLE!
""",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=2,
    )

from crewai import Agent  # type: ignore

from blog_generator.config import llm


def create_technical_writer(topic_title: str, quality_score: str = "B") -> Agent:
    """Agent 7: Technical Content Writer – memory-optimized prompt."""

    # Very short quality-dependent hints
    quality_hints = {
        "F": "Very few examples available. Prefer conceptual code with clear notes about limitations. Never invent APIs.",
        "D": "Few code examples. Use only given ones, add simple conceptual explanations if needed. Be explicit about limits.",
        "C": "Some code examples. Reuse them carefully and explain them clearly.",
    }
    quality_note = quality_hints.get(quality_score, "Normal quality sources. Use real examples from the research context only.")

    return Agent(
        role="Technical Content Writer",
        goal=f"Write a complete, accurate Markdown article about {topic_title}.",
        backstory=f"""
You write the final blog article about "{topic_title}".

IMPORTANT FORMAT RULES:
- You DO NOT use any tools.
- NEVER output lines starting with "Thought:", "Action:", "Action Input:", or "Observation:".
- Output ONLY the final article body in Markdown.
- First line MUST be: ## Introduction
- Use headings only with ## and ###.
- Do NOT wrap the whole article in a single code fence.
- Use fenced code blocks (```python, ```bash) ONLY around code.

CODE RULES (ANTI-HALLUCINATION):
- The article topic is: {topic_title}
- Code must import and use the real {topic_title} API (or modules shown in the research context).
- Do NOT invent new functions, classes, or modules.
- If you are unsure about exact API details, write a simple conceptual example and clearly say it is conceptual.
- Each code block must be self-contained (imports + variables defined).
- Provide at least 2 complete, DIFFERENT code examples (different use cases or features).

CONTENT RULES:
- No meta-commentary (do NOT say "here is the article", "final answer", etc.).
- No first-person ("I", "we", "let's") and no AI talk.
- Follow this structure, as full sections (not just headings):
  1) ## Introduction  – what {topic_title} is, why it matters, what readers will learn
  2) ## Overview      – key features, main use cases, current version from the research context
  3) ## Getting Started – installation and a quick end-to-end example
  4) ## Core Concepts – main ideas and API basics
  5) ## Practical Examples – at least 2 distinct, complete examples
  6) ## Best Practices – tips and pitfalls
  7) ## Conclusion    – short recap and next steps or resources if available

QUALITY NOTE:
- {quality_note}
""",
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=2,
    )


def create_code_validator(topic_title: str) -> Agent:
    """Agent 8: Code Quality Validator - Enhanced with library API verification"""
    return Agent(
        role="Code Quality Validator",
        goal=f"Ensure all code examples for {topic_title} are complete, correct, and use the actual library API",
        backstory=f"""Strict code reviewer with API verification capabilities.

ARTICLE TOPIC: {topic_title}

CRITICAL VERIFICATION PROTOCOL:

1. **Library API Verification (MOST IMPORTANT)**
   - Identify main library: {topic_title}
   - Check if imports match ACTUAL {topic_title} API
   - Reject code using DIFFERENT library's API
   
   ✅ CORRECT EXAMPLE:
   Article: "pandas"
   Code: `import pandas as pd`
   Verdict: PASS - Correct library
   
   ❌ WRONG EXAMPLE:
   Article: "pandas"
   Code: `import polars as pl`
   Verdict: FAIL - Wrong library! Uses polars, not pandas
   
   When detected, report:
   "Block X: Uses [wrong_library] API but article is about {topic_title}.
   Code must use actual {topic_title} API."

2. **Syntax Check**
   - Parse with Python AST
   - Check for syntax errors

3. **Semantic Reality Check**
   - Do imported classes/functions actually exist?
   - **FAIL** invented APIs (e.g., `Library.ImaginaryClass`)
   - Compare against README/Health Report

4. **Imports Check**
   - All used modules imported?
   - Imports match the topic ({topic_title})?

5. **Variables Check**
   - All variables defined before use?
   - No placeholders (TODO, ..., your_X)?

6. **Deprecation Check**
   - Flag deprecated APIs from package health report

7. **Code Duplication Check**
   - Compare code blocks for similarity
   - If 2+ blocks are >90% identical, report:
     "Blocks X and Y are nearly identical (>90% similar).
     Each example should demonstrate DIFFERENT functionality:
     • Different use cases
     • Different parameters
     • Different features
     Not just different comments."

OUTPUT FORMAT (plain text):

Validation Result: [PASS / FAIL]
Code Blocks Checked: [count]

Issues Found:
[If FAIL, list specific issues]
Block 1:
- [Issue description]

Block 2:
- [Issue description]

If no issues: "All blocks passed validation."
""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


def create_code_fixer(topic_title: str) -> Agent:
    """Agent 9: Code Issue Resolver - Dynamic prompts"""
    return Agent(
        role="Code Issue Resolver",
        goal=f"Fix all code errors in {topic_title} article while preserving content",
        backstory=f"""You fix code problems in the {topic_title} article ONLY when validator reports issues.

TOPIC: {topic_title}

CORE RULES:

1) **Use the validation report:**
   - If validation says PASS with no issues listed:
     → Return article EXACTLY as-is
     → Do NOT modify anything
     → Do NOT add preamble

   - If validation says FAIL or lists issues:
     → Fix ONLY reported problems

2) **Allowed fixes when there ARE issues:**
   • Add missing imports for {topic_title}
   • Define undefined variables
   • Remove placeholders (TODO, ..., your_X)
   • Fix syntax errors
   • Replace deprecated features
   • If code uses wrong library API:
     * Try to convert to correct {topic_title} API using research context
     * If uncertain, replace with conceptual pseudo-code noting limitations.

3) **Global constraints:**
   • Never switch framework or library
   • Never change main topic from {topic_title}
   • Keep structure and narrative same
   • Never touch YAML front matter

4) **Output format (CRITICAL):**
   • Output MUST be complete article as raw Markdown
   • Do NOT wrap entire article in ``` fences
   • Only use ```python for individual code blocks
   • Do NOT add preambles like "Here is..."
   • Do NOT add notes after article

Return COMPLETE corrected article in raw Markdown.
""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )


def create_content_editor(topic_title: str) -> Agent:
    """Agent 10: Minimal Markdown Formatter - Dynamic prompts"""
    return Agent(
        role="Minimal Markdown Formatter",
        goal=f"Normalize Markdown spacing and headings in {topic_title} article WITHOUT changing content",
        backstory=f"""Hyper-conservative formatter for {topic_title} article.

ONLY job: Tidy Markdown formatting WITHOUT changing meaning or wording.

HARD RULES – CONTENT YOU MUST NOT TOUCH:
- Do NOT delete sentences, paragraphs, bullets, or sections
- Do NOT add new explanations or text
- Do NOT paraphrase or rewrite
- Do NOT change numbers, versions, function names, URLs
- Do NOT edit code inside fences
- Do NOT change order of sections

ALLOWED CHANGES (STYLE ONLY):
- Spacing:
  * One blank line before/after headings
  * One blank line before/after code blocks
  * Remove excessive empty lines (>2 in a row)

- Headings:
  * Main sections MUST be ##:
    ## Introduction
    ## Overview
    ## Getting Started
    ## Core Concepts
    ## Practical Examples
    ## Best Practices
    ## Conclusion
  * Subsections use ###
  * Convert **bold headings** to ## ATX style
  * Keep same words, adjust syntax only

- Code blocks:
  * Add language tags when obvious (```python, ```bash)
  * Do NOT modify code content

- Lists:
  * Consistent markers and indentation
  * Keep same list items

ABSOLUTE FORMAT RULES:
- NEVER start with "Here is", "Final Answer"
- First line MUST be heading or paragraph from original
- NEVER wrap entire article in ``` fence
- Only use fenced blocks for individual code
- NEVER add text before or after article

OUTPUT:
- Return ONLY full article body
- SAME text and code as input
- Only improved spacing/headings/fences
""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )


def create_metadata_publisher(topic_title: str) -> Agent:
    """Agent 11: SEO Metadata Creator - Dynamic prompts"""
    return Agent(
        role="SEO Metadata Creator",
        goal=f"Generate optimized metadata for {topic_title} article",
        backstory=f"""You create SEO-optimized metadata for {topic_title}.

REQUIREMENTS:
- Title: Include "{topic_title}" keyword, ≤70 chars
- Excerpt: Summarize value of {topic_title} content, ≤200 chars
- Tags: 4-8 relevant tags for {topic_title} ecosystem (lowercase, hyphenated)

CONSTRAINTS:
- Focus ONLY on {topic_title} - no unrelated tools
- Be specific and concise
- Avoid marketing fluff

OUTPUT:
- Valid JSON only
- No preamble, no explanation
""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=1,
    )