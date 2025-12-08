"""
Text Cleaning and Output Extraction Utilities

This module provides functions for:
- Cleaning LLM output (removing artifacts, normalizing formatting)
- Extracting task outputs from CrewAI Task objects
- Processing markdown content
- Removing unwanted formatting patterns
"""
import re
from typing import Any, Optional

from blog_generator.config import logger


def clean_content(body: str) -> str:
    """
    Clean and normalize blog post content.
    
    Removes excessive blank lines and ensures proper spacing.
    
    Args:
        body: Raw blog post content
    
    Returns:
        Cleaned content with normalized spacing
    
    Example:
        >>> clean_content("Line 1\\n\\n\\n\\n\\nLine 2")
        "Line 1\\n\\n\\nLine 2\\n"
    """
    if not body:
        return ""
    
    # Remove excessive blank lines (more than 3 consecutive)
    body = re.sub(r"\n{4,}", "\n\n\n", body)
    
    # Ensure trailing newline
    body = body.strip() + "\n"
    
    return body


def clean_llm_output(text: str) -> str:
    """
    Clean LLM output to produce proper Markdown.
    
    This function:
    1. Removes outer markdown code fences if present
    2. Preserves front matter (YAML between --- delimiters)
    3. Normalizes headings (converts **bold** to ## headings)
    4. Protects code blocks from modification
    5. Cleans up prose sections
    
    Args:
        text: Raw LLM output text
    
    Returns:
        Cleaned markdown text
    
    Example:
        >>> clean_llm_output("```markdown\\n## Title\\nContent\\n```")
        "## Title\\nContent\\n"
    """
    if not text:
        return ""
    
    # Remove BOM and whitespace
    text = text.replace("\ufeff", "").strip()
    
    # Remove outer markdown code fence if present
    outer = re.match(
        r"^```(?:markdown)?\s*(.*?)\s*```$",
        text.strip(),
        flags=re.DOTALL | re.IGNORECASE,
    )
    if outer:
        text = outer.group(1)
    
    # Separate front matter from body
    front_matter = ""
    body = text
    
    if text.startswith("---\n") or text.startswith("---\r\n"):
        lines = text.splitlines(keepends=True)
        end_idx = None
        
        # Find end of front matter
        for i in range(1, len(lines)):
            if lines[i].startswith("---"):
                end_idx = i
                break
        
        if end_idx is not None:
            front_matter = "".join(lines[: end_idx + 1])
            body = "".join(lines[end_idx + 1 :])
    
    def _clean_prose(prose: str) -> str:
        """
        Clean prose sections (text outside code blocks).
        
        Converts bold-only lines to headings and normalizes "Introduction".
        """
        # Convert standalone bold text to headings
        # Pattern: **Text** on its own line → ## Text
        prose = re.sub(
            r"^\s*\*\*(.*?)\*\*\s*$",
            r"## \1",
            prose,
            flags=re.MULTILINE,
        )
        
        # Convert standalone "Introduction" to heading
        prose = re.sub(
            r"^Introduction\s*$",
            r"## Introduction",
            prose,
            flags=re.MULTILINE | re.IGNORECASE,
        )
        
        return prose
    
    # Process body: clean prose but preserve code blocks
    code_fence_re = re.compile(r"```.*?```", re.DOTALL)
    cleaned_body_parts = []
    last_pos = 0
    
    # Split by code blocks and clean only prose
    for match in code_fence_re.finditer(body):
        # Clean prose before this code block
        prose_chunk = body[last_pos : match.start()]
        cleaned_body_parts.append(_clean_prose(prose_chunk))
        
        # Keep code block as-is
        cleaned_body_parts.append(match.group(0))
        
        last_pos = match.end()
    
    # Clean final prose chunk
    prose_chunk = body[last_pos:]
    cleaned_body_parts.append(_clean_prose(prose_chunk))
    
    # Reassemble
    cleaned_body = "".join(cleaned_body_parts).strip()
    result = (front_matter + cleaned_body).rstrip() + "\n"
    
    return result


def extract_task_output(task: Any, task_name: str) -> str:
    """
    Extract output string from a CrewAI Task object.
    
    Tries multiple methods to extract the output in order of preference:
    1. task.output.raw
    2. task.output.result
    3. task.output (if string)
    4. str(task.output)
    
    Args:
        task: CrewAI Task object with output
        task_name: Name of task (for logging)
    
    Returns:
        Extracted output string, or empty string if extraction fails
    
    Example:
        >>> output = extract_task_output(planning_task, "planning")
        >>> print(f"Planning output: {len(output)} chars")
    """
    # Validate input
    if not task:
        logger.warning(f"⚠️  Task {task_name} is None")
        return ""
    
    if not hasattr(task, "output"):
        logger.warning(f"⚠️  Task {task_name} has no 'output' attribute")
        return ""
    
    if task.output is None:
        logger.warning(f"⚠️  Task {task_name} has None output")
        return ""
    
    output = task.output
    
    # Define extraction methods in order of preference
    methods = [
        ("raw", lambda: getattr(output, "raw", None)),
        ("result", lambda: getattr(output, "result", None)),
        ("direct", lambda: output if isinstance(output, str) else None),
        ("str()", lambda: str(output)),
    ]
    
    # Try each method
    for method_name, method_func in methods:
        try:
            result = method_func()
            
            # Check if result is valid
            if result and isinstance(result, str) and len(result) > 50:
                logger.debug(
                    f"✓ Extracted from {task_name}.output.{method_name}: "
                    f"{len(result)} chars"
                )
                return result.strip()
        except Exception as e:
            logger.debug(f"Method {method_name} failed for {task_name}: {e}")
            continue
    
    # All methods failed
    logger.warning(
        f"⚠️  Failed to extract output from {task_name} "
        f"(tried {len(methods)} methods)"
    )
    return ""


def remove_markdown_artifacts(text: str) -> str:
    """
    Remove common markdown artifacts from LLM output.
    
    Removes:
    - Preambles like "Here is...", "Here's...", "This is..."
    - Outer code fences around entire documents
    - Meta-commentary
    
    Args:
        text: Text with potential artifacts
    
    Returns:
        Cleaned text
    
    Example:
        >>> remove_markdown_artifacts("Here is the article:\\n\\n## Title")
        "## Title"
    """
    if not text:
        return ""
    
    # Remove common preambles
    preamble_patterns = [
        r"^Here is the (?:article|post|content|document).*?:\s*\n+",
        r"^Here's (?:the|a|an) .*?:\s*\n+",
        r"^This is (?:the|a|an) .*?:\s*\n+",
        r"^I've (?:created|written|prepared) .*?:\s*\n+",
    ]
    
    for pattern in preamble_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)
    
    # Remove outer code fence if wrapping entire content
    text = re.sub(
        r"^```(?:markdown|md)?\s*\n(.*)\n```\s*$",
        r"\1",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    
    return text.strip()


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.
    
    - Converts multiple spaces to single space
    - Removes trailing whitespace from lines
    - Normalizes line endings
    - Preserves intentional spacing in code blocks
    
    Args:
        text: Text with irregular whitespace
    
    Returns:
        Text with normalized whitespace
    """
    if not text:
        return ""
    
    # Split into code blocks and prose
    code_fence_re = re.compile(r"```.*?```", re.DOTALL)
    parts = []
    last_pos = 0
    
    for match in code_fence_re.finditer(text):
        # Normalize prose
        prose = text[last_pos : match.start()]
        
        # Remove trailing whitespace from lines
        prose = "\n".join(line.rstrip() for line in prose.split("\n"))
        
        # Normalize multiple spaces to single (except line breaks)
        prose = re.sub(r"[^\S\n]+", " ", prose)
        
        parts.append(prose)
        
        # Keep code block as-is
        parts.append(match.group(0))
        
        last_pos = match.end()
    
    # Final prose chunk
    prose = text[last_pos:]
    prose = "\n".join(line.rstrip() for line in prose.split("\n"))
    prose = re.sub(r"[^\S\n]+", " ", prose)
    parts.append(prose)
    
    return "".join(parts)


def strip_yaml_frontmatter(text: str) -> tuple[str, str]:
    """
    Separate YAML front matter from content.
    
    Args:
        text: Markdown text potentially with front matter
    
    Returns:
        Tuple of (frontmatter, content)
        If no front matter, returns ("", original_text)
    
    Example:
        >>> fm, content = strip_yaml_frontmatter("---\\ntitle: Test\\n---\\nContent")
        >>> print(f"Title in frontmatter: {'title' in fm}")
        True
    """
    if not text or not (text.startswith("---\n") or text.startswith("---\r\n")):
        return "", text
    
    lines = text.splitlines(keepends=True)
    end_idx = None
    
    # Find end of front matter
    for i in range(1, len(lines)):
        if lines[i].startswith("---"):
            end_idx = i
            break
    
    if end_idx is None:
        return "", text
    
    front_matter = "".join(lines[: end_idx + 1])
    content = "".join(lines[end_idx + 1 :])
    
    return front_matter, content


def ensure_proper_markdown_structure(text: str) -> str:
    """
    Ensure markdown has proper structure.
    
    - First non-empty line should be a heading or paragraph
    - Proper spacing around headings and code blocks
    - No multiple consecutive blank lines
    
    Args:
        text: Markdown text
    
    Returns:
        Properly structured markdown
    """
    if not text:
        return ""
    
    lines = text.split("\n")
    result_lines = []
    prev_was_blank = False
    
    for line in lines:
        is_blank = not line.strip()
        
        # Don't allow more than 2 consecutive blank lines
        if is_blank:
            if not prev_was_blank or len(result_lines) == 0:
                result_lines.append("")
            prev_was_blank = True
        else:
            result_lines.append(line)
            prev_was_blank = False
    
    return "\n".join(result_lines).strip() + "\n"


# ============================================================================
# CONVENIENCE FUNCTION - Full Pipeline
# ============================================================================

def clean_article_output(raw_output: str, task_name: str = "unknown") -> str:
    """
    Complete cleaning pipeline for article output.
    
    Applies all cleaning steps in optimal order:
    1. Remove markdown artifacts
    2. Clean LLM output
    3. Normalize whitespace
    4. Ensure proper structure
    5. Final content cleaning
    
    Args:
        raw_output: Raw output from LLM/agent
        task_name: Name of task (for logging)
    
    Returns:
        Fully cleaned article text
    
    Example:
        >>> raw = "Here is the article:\\n\\n```markdown\\n## Title\\nContent\\n```"
        >>> clean = clean_article_output(raw, "writer")
        >>> print(clean)
        ## Title
        Content
    """
    if not raw_output:
        logger.warning(f"⚠️  Empty output from {task_name}")
        return ""
    
    logger.debug(f"Cleaning {task_name} output: {len(raw_output)} chars")
    
    # Step 1: Remove artifacts
    text = remove_markdown_artifacts(raw_output)
    
    # Step 2: Clean LLM output
    text = clean_llm_output(text)
    
    # Step 3: Normalize whitespace
    text = normalize_whitespace(text)
    
    # Step 4: Ensure structure
    text = ensure_proper_markdown_structure(text)
    
    # Step 5: Final content cleaning
    text = clean_content(text)
    
    logger.debug(f"Cleaned {task_name} output: {len(text)} chars")
    
    return text