"""
Code Validation Utilities

This module provides functions for validating Python code in blog posts:
- Syntax validation using AST parsing
- Import completeness checking
- Placeholder detection
- Multi-block validation
- Quality scoring
"""
import ast
import re
from typing import List, Tuple, Dict, Optional

from blog_generator.config import logger


def validate_python_code(code: str) -> Tuple[bool, List[str]]:
    """
    Validate a single Python code block.
    
    Checks:
    1. Non-empty code
    2. Valid Python syntax (AST parsing)
    3. No shell commands in Python blocks
    4. No placeholders or TODOs
    
    Args:
        code: Python code string to validate
    
    Returns:
        Tuple of (is_valid, error_list)
        - is_valid: True if code passes all checks
        - error_list: List of error messages (empty if valid)
    
    Example:
        >>> code = "import os\\nprint('hello')"
        >>> is_valid, errors = validate_python_code(code)
        >>> print(f"Valid: {is_valid}")
        Valid: True
    """
    errors: List[str] = []
    
    # Check 1: Non-empty
    if not code or not code.strip():
        return False, ["Empty code block"]
    
    # Check 2: Valid Python syntax
    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, [f"Syntax error at line {e.lineno}: {e.msg}"]
    except Exception as e:
        return False, [f"Parse error: {str(e)}"]
    
    # Check 3: No shell commands
    shell_commands = re.search(
        r"^(pip|apt|brew|conda)\s+install",
        code,
        re.MULTILINE,
    )
    if shell_commands:
        errors.append("Shell commands found in Python block")
    
    # Check 4: No placeholders
    placeholder_patterns = [
        (r"\.\.\.+", "Ellipsis placeholder"),
        (r"TODO", "TODO comment"),
        (r"FIXME", "FIXME comment"),
        (r"your_\w+", "Generic placeholder (your_X)"),
        (r"<[A-Z_]+>", "Template placeholder (<VAR>)"),
    ]
    
    for pattern, description in placeholder_patterns:
        if re.search(pattern, code, re.MULTILINE):
            errors.append(f"Contains {description}")
    
    # Return results
    is_valid = len(errors) == 0
    return is_valid, errors


def validate_all_code_blocks(content: str) -> Tuple[bool, List[str], List[str]]:
    """
    Validate all Python code blocks in markdown content.
    
    Extracts all Python code blocks and validates each one.
    
    Args:
        content: Full markdown content with code blocks
    
    Returns:
        Tuple of (all_valid, issues_list, code_blocks)
        - all_valid: True if all blocks are valid
        - issues_list: List of all issues found
        - code_blocks: List of extracted code blocks
    
    Example:
        >>> content = '''
        ... ## Example
        ... ```python
        ... print("hello")
        ... ```
        ... '''
        >>> all_valid, issues, blocks = validate_all_code_blocks(content)
        >>> print(f"Found {len(blocks)} blocks, valid: {all_valid}")
    """
    # Extract all Python code blocks
    code_blocks = re.findall(
        r"```(?:python|py)?[ \t]*\n(.*?)```",
        content,
        re.DOTALL | re.IGNORECASE,
    )
    
    if not code_blocks:
        # No code blocks found - that's OK
        return True, [], []
    
    all_issues: List[str] = []
    all_valid = True
    
    # Validate each block
    for i, code in enumerate(code_blocks, 1):
        if not code.strip():
            continue  # Skip empty blocks
        
        is_valid, errors = validate_python_code(code)
        
        if not is_valid:
            all_valid = False
            all_issues.append(f"Block {i}:")
            all_issues.extend([f"  • {err}" for err in errors])
    
    return all_valid, all_issues, code_blocks


def check_imports_present(code: str) -> Tuple[bool, List[str]]:
    """
    Check if all used modules are imported.
    
    Args:
        code: Python code to check
    
    Returns:
        Tuple of (all_imported, missing_imports)
    
    Example:
        >>> code = "import os\\nprint(sys.argv)"
        >>> imported, missing = check_imports_present(code)
        >>> print(missing)
        ['sys']
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False, ["Code has syntax errors"]
    
    # Collect imported names
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module.split(".")[0])
    
    # Collect used names (approximation)
    used = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Get root name (e.g., 'np' from 'np.array')
            root = node
            while isinstance(root, ast.Attribute):
                root = root.value
            if isinstance(root, ast.Name):
                used.add(root.id)
    
    # Common stdlib modules that might not need explicit imports
    # (though they should still be imported)
    stdlib_modules = {
        'os', 'sys', 'json', 'time', 'datetime', 'random',
        're', 'math', 'collections', 'itertools', 'functools',
    }
    
    # Find potentially missing imports
    missing = []
    for name in used:
        # Skip if it's a builtin or already imported
        if name in imported:
            continue
        
        # Skip builtins
        if name in dir(__builtins__):
            continue
        
        # Skip private/dunder names
        if name.startswith('_'):
            continue
        
        # Skip single letter variables (likely local vars)
        if len(name) == 1:
            continue
        
        # Check if it looks like a module name
        if name in stdlib_modules or name.islower():
            missing.append(name)
    
    all_imported = len(missing) == 0
    return all_imported, missing


def check_variable_definitions(code: str) -> Tuple[bool, List[str]]:
    """
    Check if all variables are defined before use.
    
    Args:
        code: Python code to check
    
    Returns:
        Tuple of (all_defined, undefined_vars)
    
    Note:
        This is a best-effort check using AST analysis.
        May have false positives/negatives.
    
    Example:
        >>> code = "x = 5\\nprint(y)"
        >>> defined, undefined = check_variable_definitions(code)
        >>> print(undefined)
        ['y']
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False, ["Code has syntax errors"]
    
    # Track defined names
    defined = set()
    undefined = []
    
    for node in ast.walk(tree):
        # Variable assignments
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    defined.add(target.id)
        
        # Function/class definitions
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            defined.add(node.name)
        
        # Imports
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                defined.add(name)
        
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                defined.add(name)
        
        # For loops
        elif isinstance(node, ast.For):
            if isinstance(node.target, ast.Name):
                defined.add(node.target.id)
        
        # With statements
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars and isinstance(item.optional_vars, ast.Name):
                    defined.add(item.optional_vars.id)
    
    # Check for undefined usage
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            # Name is being loaded (used)
            if node.id not in defined and node.id not in dir(__builtins__):
                if node.id not in undefined:
                    undefined.append(node.id)
    
    all_defined = len(undefined) == 0
    return all_defined, undefined


def calculate_code_quality_score(
    code: str,
    check_syntax: bool = True,
    check_imports: bool = True,
    check_variables: bool = True,
    check_placeholders: bool = True,
) -> Tuple[float, Dict[str, any]]:
    """
    Calculate comprehensive code quality score.
    
    Args:
        code: Python code to score
        check_syntax: Enable syntax validation
        check_imports: Enable import checking
        check_variables: Enable variable definition checking
        check_placeholders: Enable placeholder detection
    
    Returns:
        Tuple of (score, details_dict)
        - score: 0-100 quality score
        - details_dict: Breakdown of checks
    
    Example:
        >>> code = "import numpy as np\\nx = np.array([1,2,3])"
        >>> score, details = calculate_code_quality_score(code)
        >>> print(f"Quality: {score}/100")
    """
    details = {
        'syntax_valid': False,
        'imports_complete': False,
        'variables_defined': False,
        'no_placeholders': False,
        'line_count': 0,
        'issues': [],
    }
    
    score = 0.0
    
    # Basic metrics
    details['line_count'] = len(code.split('\n'))
    
    # Syntax check (30 points)
    if check_syntax:
        is_valid, errors = validate_python_code(code)
        details['syntax_valid'] = is_valid
        if is_valid:
            score += 30
        else:
            details['issues'].extend(errors)
    
    # Import check (25 points)
    if check_imports:
        all_imported, missing = check_imports_present(code)
        details['imports_complete'] = all_imported
        if all_imported:
            score += 25
        else:
            details['issues'].append(f"Missing imports: {', '.join(missing)}")
            # Partial credit
            score += 25 * (1 - len(missing) * 0.2)
    
    # Variable definition check (25 points)
    if check_variables:
        all_defined, undefined = check_variable_definitions(code)
        details['variables_defined'] = all_defined
        if all_defined:
            score += 25
        else:
            details['issues'].append(f"Undefined variables: {', '.join(undefined)}")
            # Partial credit
            score += 25 * (1 - len(undefined) * 0.2)
    
    # Placeholder check (20 points)
    if check_placeholders:
        placeholder_patterns = [r"\.\.\.+", r"TODO", r"FIXME", r"your_\w+"]
        has_placeholders = any(
            re.search(p, code) for p in placeholder_patterns
        )
        details['no_placeholders'] = not has_placeholders
        if not has_placeholders:
            score += 20
        else:
            details['issues'].append("Contains placeholders or TODOs")
    
    # Ensure score is in range
    score = max(0.0, min(100.0, score))
    
    return score, details


def get_code_block_summary(content: str) -> Dict[str, any]:
    """
    Get summary statistics for all code blocks in content.
    
    Args:
        content: Markdown content with code blocks
    
    Returns:
        Dict with summary statistics
    
    Example:
        >>> summary = get_code_block_summary(article_content)
        >>> print(f"Total blocks: {summary['total_blocks']}")
        >>> print(f"Valid blocks: {summary['valid_blocks']}")
    """
    all_valid, issues, code_blocks = validate_all_code_blocks(content)
    
    # Calculate quality scores
    quality_scores = []
    for code in code_blocks:
        if code.strip():
            score, _ = calculate_code_quality_score(code)
            quality_scores.append(score)
    
    summary = {
        'total_blocks': len(code_blocks),
        'valid_blocks': len(code_blocks) - len([i for i in issues if 'Block' in i]),
        'all_valid': all_valid,
        'total_issues': len(issues),
        'average_quality': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
        'min_quality': min(quality_scores) if quality_scores else 0,
        'max_quality': max(quality_scores) if quality_scores else 0,
        'total_lines': sum(len(code.split('\n')) for code in code_blocks),
    }
    
    return summary


# ============================================================================
# VALIDATION REPORT GENERATION
# ============================================================================

def generate_validation_report(content: str, verbose: bool = False) -> str:
    """
    Generate human-readable validation report.
    
    Args:
        content: Markdown content to validate
        verbose: Include detailed information
    
    Returns:
        Formatted validation report as string
    
    Example:
        >>> report = generate_validation_report(article_content)
        >>> print(report)
        Validation Result: PASS
        Code Blocks Checked: 3
        All blocks passed validation.
    """
    all_valid, issues, code_blocks = validate_all_code_blocks(content)
    
    report_lines = []
    
    # Header
    report_lines.append(f"Validation Result: {'PASS' if all_valid else 'FAIL'}")
    report_lines.append(f"Code Blocks Checked: {len(code_blocks)}")
    report_lines.append("")
    
    # Issues
    if issues:
        report_lines.append("Issues Found:")
        report_lines.extend(issues)
    else:
        report_lines.append("All blocks passed validation.")
    
    # Verbose details
    if verbose:
        report_lines.append("")
        report_lines.append("=== Detailed Analysis ===")
        
        for i, code in enumerate(code_blocks, 1):
            if not code.strip():
                continue
            
            report_lines.append(f"\nBlock {i}:")
            score, details = calculate_code_quality_score(code)
            report_lines.append(f"  Quality Score: {score:.1f}/100")
            report_lines.append(f"  Lines: {details['line_count']}")
            report_lines.append(f"  Syntax: {'✓' if details['syntax_valid'] else '✗'}")
            report_lines.append(f"  Imports: {'✓' if details['imports_complete'] else '✗'}")
            report_lines.append(f"  Variables: {'✓' if details['variables_defined'] else '✗'}")
            
            if details['issues']:
                report_lines.append("  Issues:")
                for issue in details['issues']:
                    report_lines.append(f"    • {issue}")
    
    return "\n".join(report_lines)