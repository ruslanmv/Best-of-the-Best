#!/usr/bin/env python3
"""
Enhanced README updater that updates the actual data tables.
Fetches live data from GitHub API and updates README.md tables.
"""

import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple
import requests

# Configuration
README_FILE = Path("README.md")
DB_FILE = Path("data/tracking.db")
GITHUB_API = "https://api.github.com/repos/"

# Get GitHub token from environment
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')


def fetch_github_stars(repo_full_name: str) -> int:
    """Fetch current star count for a GitHub repository."""
    try:
        headers = {}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'

        response = requests.get(f"{GITHUB_API}{repo_full_name}", headers=headers, timeout=10)
        if response.status_code == 200:
            stars = response.json().get('stargazers_count', 0)
            print(f"✓ {repo_full_name}: {stars:,} stars")
            return stars
        else:
            print(f"⚠ Failed to fetch {repo_full_name}: {response.status_code}")
            return 0
    except Exception as e:
        print(f"❌ Error fetching {repo_full_name}: {e}")
        return 0


def extract_repositories_from_readme() -> List[Dict]:
    """Extract repository list from README.md."""
    if not README_FILE.exists():
        return []

    with open(README_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    repos = []
    repo_section_start = content.find('### Repositories')
    repo_section_end = content.find('### Papers')

    if repo_section_start != -1 and repo_section_end != -1:
        repo_section = content[repo_section_start:repo_section_end]
        repo_pattern = r'\| ([^|]+) \| (\d+) \| \[GitHub\]\((https://github\.com/([^)]+))\)'

        for match in re.finditer(repo_pattern, repo_section):
            repos.append({
                'name': match.group(1).strip(),
                'stars': int(match.group(2).strip()),
                'url': match.group(3).strip(),
                'repo_path': match.group(4).strip()
            })

    return repos


def update_repository_stars(repositories: List[Dict], limit: int = 10) -> List[Dict]:
    """Update star counts for top N repositories."""
    print(f"\n📊 Updating top {limit} repositories...")

    updated_repos = []
    for i, repo in enumerate(repositories[:limit]):
        stars = fetch_github_stars(repo['repo_path'])

        if stars > 0:
            repo['stars'] = stars
        else:
            print(f"  Using cached value: {repo['stars']:,}")

        updated_repos.append(repo)

        # Rate limiting
        if i < limit - 1:
            time.sleep(1)

    return updated_repos


def rebuild_readme_table(repositories: List[Dict]) -> str:
    """Rebuild the repositories table with updated data."""
    # Sort by stars (descending)
    sorted_repos = sorted(repositories, key=lambda x: x['stars'], reverse=True)

    table_lines = [
        "| Repository | Stars | Link |",
        "|---|---|---|"
    ]

    for repo in sorted_repos:
        table_lines.append(
            f"| {repo['name']} | {repo['stars']} | [GitHub]({repo['url']}) |"
        )

    return '\n'.join(table_lines)


def update_readme_content(updated_table: str) -> bool:
    """Update README.md with new table and current date."""
    if not README_FILE.exists():
        print("❌ README.md not found!")
        return False

    with open(README_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update date in header
    current_date = datetime.now().strftime("%B %Y")
    content = re.sub(
        r'# The best for now [A-Za-z]+ \d{4}:',
        f'# The best for now {current_date}:',
        content
    )

    # Find and replace repositories table
    repo_section_start = content.find('### Repositories')
    repo_section_end = content.find('### Papers')

    if repo_section_start != -1 and repo_section_end != -1:
        # Find the table start and end
        section_content = content[repo_section_start:repo_section_end]
        table_start = section_content.find('| Repository | Stars | Link |')

        if table_start != -1:
            # Calculate absolute positions
            abs_table_start = repo_section_start + table_start
            abs_table_end = content.find('\n### Papers')

            # Find the actual end of the table (last table row before next section)
            table_content = content[abs_table_start:abs_table_end]
            lines = table_content.split('\n')

            # Find where table ends (first non-table line)
            table_line_count = 0
            for line in lines:
                if line.strip().startswith('|'):
                    table_line_count += 1
                else:
                    break

            # Calculate table end position
            table_end_pos = abs_table_start
            for i in range(table_line_count):
                table_end_pos = content.find('\n', table_end_pos) + 1

            # Replace the table
            before_table = content[:abs_table_start]
            after_table = content[table_end_pos:]

            new_content = before_table + updated_table + '\n\n' + after_table

            # Write updated content
            with open(README_FILE, 'w', encoding='utf-8') as f:
                f.write(new_content)

            print(f"\n✅ README.md updated successfully!")
            return True

    print("⚠ Could not find repositories table in README.md")
    return False


def main():
    """Main execution function."""
    print("=" * 70)
    print("Enhanced README.md Table Updater")
    print("=" * 70)

    # Extract repositories from README
    print("\n📖 Reading repositories from README.md...")
    repositories = extract_repositories_from_readme()

    if not repositories:
        print("❌ No repositories found in README.md")
        return

    print(f"✅ Found {len(repositories)} repositories")

    # Update star counts for top repositories
    updated_repos = update_repository_stars(repositories, limit=10)

    # Merge updated repos with the rest
    all_repos = updated_repos + repositories[len(updated_repos):]

    # Rebuild table
    print("\n📝 Rebuilding README table...")
    updated_table = rebuild_readme_table(all_repos)

    # Update README
    print("\n💾 Updating README.md...")
    success = update_readme_content(updated_table)

    if success:
        print("\n" + "=" * 70)
        print("✅ README.md tables updated successfully!")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("⚠ README.md update completed with warnings")
        print("=" * 70)


if __name__ == "__main__":
    main()
