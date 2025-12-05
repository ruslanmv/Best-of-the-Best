#!/usr/bin/env python3
"""
scripts/diagnose_blog_system.py

Diagnostic tool for troubleshooting blog generation issues.
Checks paths, data files, permissions, and system configuration.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI colors
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
MAGENTA = "\033[0;35m"
CYAN = "\033[0;36m"
NC = "\033[0m"  # No Color


def print_header(text: str) -> None:
    """Print section header."""
    print(f"\n{BLUE}{'='*70}{NC}")
    print(f"{BLUE}{text}{NC}")
    print(f"{BLUE}{'='*70}{NC}\n")


def print_check(label: str, status: bool, message: str = "") -> None:
    """Print check result."""
    icon = f"{GREEN}✅{NC}" if status else f"{RED}❌{NC}"
    print(f"{icon} {label}")
    if message:
        print(f"   {message}")


def check_python_packages() -> Dict[str, bool]:
    """Check required Python packages."""
    packages = {}
    for pkg in ["crewai", "litellm", "langchain", "pathlib"]:
        try:
            __import__(pkg)
            packages[pkg] = True
        except ImportError:
            packages[pkg] = False
    return packages


def check_paths() -> Dict[str, Tuple[bool, str]]:
    """Check critical paths."""
    current_dir = Path(__file__).resolve().parent
    
    # OLD BUG: base_dir = current_dir.parents[1]
    # FIXED: base_dir = current_dir.parent
    base_dir = current_dir.parent
    
    paths = {
        "Current Script Dir": (current_dir, current_dir.exists()),
        "Base Dir (FIXED)": (base_dir, base_dir.exists()),
        "blog/": (base_dir / "blog", (base_dir / "blog").exists()),
        "blog/posts/": (base_dir / "blog" / "posts", (base_dir / "blog" / "posts").exists()),
        "blog/api/": (base_dir / "blog" / "api", (base_dir / "blog" / "api").exists()),
        "data/": (base_dir / "data", (base_dir / "data").exists()),
        "scripts/": (current_dir, current_dir.exists()),
    }
    
    return {k: (v[1], str(v[0])) for k, v in paths.items()}


def check_data_files(base_dir: Path) -> Dict[str, Tuple[bool, int]]:
    """Check API data files."""
    api_dir = base_dir / "blog" / "api"
    
    files = {
        "packages.json": api_dir / "packages.json",
        "repositories.json": api_dir / "repositories.json",
        "papers.json": api_dir / "papers.json",
        "research.json": api_dir / "research.json",
        "tutorials.json": api_dir / "tutorials.json",
        "data.json": api_dir / "data.json",
    }
    
    results = {}
    for name, path in files.items():
        if path.exists():
            try:
                with path.open() as f:
                    data = json.load(f)
                    # Count items
                    if isinstance(data, list):
                        count = len(data)
                    elif isinstance(data, dict):
                        count = sum(len(v) for v in data.values() if isinstance(v, list))
                    else:
                        count = 0
                    results[name] = (True, count)
            except Exception as e:
                results[name] = (False, f"Error: {e}")
        else:
            results[name] = (False, "Not found")
    
    return results


def check_coverage(base_dir: Path) -> Tuple[bool, int, List[str]]:
    """Check blog coverage."""
    coverage_file = base_dir / "data" / "blog_coverage.json"
    
    if not coverage_file.exists():
        return (False, 0, [])
    
    try:
        with coverage_file.open() as f:
            data = json.load(f)
            recent = [
                f"{e.get('date', 'unknown')}: {e.get('kind', '?')} - {e.get('filename', '?')}"
                for e in data[-5:]
            ]
            return (True, len(data), recent)
    except Exception as e:
        return (False, 0, [f"Error: {e}"])


def check_blog_posts(base_dir: Path) -> Tuple[int, List[str]]:
    """Check existing blog posts."""
    posts_dir = base_dir / "blog" / "posts"
    
    if not posts_dir.exists():
        return (0, [])
    
    posts = list(posts_dir.glob("*.md"))
    posts.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    recent = [f"{p.name} ({p.stat().st_size} bytes)" for p in posts[:5]]
    return (len(posts), recent)


def main() -> None:
    """Run all diagnostics."""
    print_header("🔍 Blog System Diagnostics")
    
    # Python environment
    print_header("🐍 Python Environment")
    packages = check_python_packages()
    for pkg, installed in packages.items():
        print_check(pkg, installed, "" if installed else "Not installed")
    
    if not all(packages.values()):
        print(f"\n{YELLOW}Install missing packages:{NC}")
        print("   pip install crewai litellm\n")
    
    # Path verification
    print_header("📁 Path Configuration")
    current_dir = Path(__file__).resolve().parent
    base_dir = current_dir.parent
    
    print(f"Script location: {__file__}")
    print(f"Current dir:     {current_dir}")
    print(f"Base dir:        {base_dir}")
    print()
    
    paths = check_paths()
    for label, (exists, path) in paths.items():
        print_check(label, exists, path)
    
    # Critical path issues
    if not paths["blog/posts/"][0]:
        print(f"\n{RED}❌ CRITICAL: blog/posts/ directory missing!{NC}")
        print(f"   Create it: mkdir -p {base_dir}/blog/posts\n")
    
    if not paths["blog/api/"][0]:
        print(f"\n{RED}❌ CRITICAL: blog/api/ directory missing!{NC}")
        print(f"   Create it: mkdir -p {base_dir}/blog/api\n")
    
    # Data files
    print_header("📊 API Data Files")
    data_files = check_data_files(base_dir)
    
    has_any_data = False
    for name, (exists, count) in data_files.items():
        if exists:
            has_any_data = True
            print_check(name, True, f"{count} items")
        else:
            print_check(name, False, str(count))
    
    if not has_any_data:
        print(f"\n{RED}❌ No API data files found!{NC}")
        print("   Generate data first:")
        print("   - Run export script: python export_data_feeds.py")
        print("   - Or manually create blog/api/packages.json\n")
    
    # Coverage tracking
    print_header("📈 Coverage Tracking")
    coverage_exists, coverage_count, recent_coverage = check_coverage(base_dir)
    
    if coverage_exists:
        print_check("Coverage file", True, f"{coverage_count} entries")
        if recent_coverage:
            print(f"\n{CYAN}Recent coverage:{NC}")
            for entry in recent_coverage:
                print(f"   • {entry}")
    else:
        print_check("Coverage file", False, "Will be created on first run")
    
    # Blog posts
    print_header("📝 Blog Posts")
    post_count, recent_posts = check_blog_posts(base_dir)
    
    if post_count > 0:
        print_check(f"Total posts", True, f"{post_count} posts found")
        if recent_posts:
            print(f"\n{CYAN}Recent posts:{NC}")
            for post in recent_posts:
                print(f"   • {post}")
    else:
        print_check("Blog posts", False, "No posts found yet")
    
    # Summary
    print_header("📋 Summary")
    
    issues = []
    
    if not all(packages.values()):
        issues.append("Missing Python packages")
    
    if not paths["blog/posts/"][0]:
        issues.append("blog/posts/ directory missing")
    
    if not paths["blog/api/"][0]:
        issues.append("blog/api/ directory missing")
    
    if not has_any_data:
        issues.append("No API data files")
    
    if issues:
        print(f"{RED}⚠️  Issues found:{NC}")
        for issue in issues:
            print(f"   • {issue}")
        print()
        print(f"{YELLOW}Fix these issues before running blog generation.{NC}\n")
        sys.exit(1)
    else:
        print(f"{GREEN}✅ All checks passed!{NC}")
        print(f"{GREEN}   System ready for blog generation.{NC}\n")
        
        print(f"{CYAN}Next steps:{NC}")
        print(f"   1. Run: bash update_blog.sh")
        print(f"   2. Or:  python scripts/generate_daily_blog.py\n")


if __name__ == "__main__":
    main()