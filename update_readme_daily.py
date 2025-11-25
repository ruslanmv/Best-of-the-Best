#!/usr/bin/env python3
"""
Daily README updater with SQLite database tracking.
Fetches latest stats for repositories, papers, and packages, updates README.md,
and stores historical data in a database with automatic size management (max 100MB).
"""

import json
import sqlite3
import time
import os
import re
from datetime import datetime
from pathlib import Path
import requests
from typing import Dict, List, Tuple

# Configuration
DB_FILE = Path("data/tracking.db")
DB_MAX_SIZE_MB = 100
DATA_DIR = Path("data")
README_FILE = Path("README.md")

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)

# API Configuration
GITHUB_API = "https://api.github.com/repos/"
PYPI_API = "https://pypi.org/pypi/"


class DatabaseManager:
    """Manages SQLite database with automatic size control."""

    def __init__(self, db_path: Path, max_size_mb: int = 100):
        self.db_path = db_path
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.conn = None
        self.init_database()

    def init_database(self):
        """Initialize database with required tables."""
        self.conn = sqlite3.connect(self.db_path)
        cursor = self.conn.cursor()

        # Create tables for tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repository_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_name TEXT NOT NULL,
                stars INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_name TEXT NOT NULL,
                citations INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS package_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                package_name TEXT NOT NULL,
                downloads_last_month INTEGER NOT NULL,
                total_downloads INTEGER NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repo_timestamp
            ON repository_stats(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_paper_timestamp
            ON paper_stats(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_package_timestamp
            ON package_stats(timestamp)
        """)

        self.conn.commit()

    def check_and_trim_database(self):
        """Check database size and remove oldest records if exceeds limit."""
        if not self.db_path.exists():
            return

        current_size = os.path.getsize(self.db_path)
        print(f"Database size: {current_size / (1024*1024):.2f} MB")

        if current_size > self.max_size_bytes:
            print(f"Database exceeds {self.max_size_bytes / (1024*1024)} MB, trimming old records...")
            cursor = self.conn.cursor()

            # Calculate how many records to remove (remove ~20% to have buffer)
            for table in ['repository_stats', 'paper_stats', 'package_stats']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                records_to_remove = int(count * 0.2)

                if records_to_remove > 0:
                    cursor.execute(f"""
                        DELETE FROM {table}
                        WHERE id IN (
                            SELECT id FROM {table}
                            ORDER BY timestamp ASC
                            LIMIT {records_to_remove}
                        )
                    """)
                    print(f"Removed {records_to_remove} old records from {table}")

            self.conn.commit()
            # Vacuum to reclaim space
            cursor.execute("VACUUM")
            print("Database trimmed and optimized")

    def insert_repository_stats(self, repo_name: str, stars: int):
        """Insert repository statistics."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO repository_stats (repo_name, stars) VALUES (?, ?)",
            (repo_name, stars)
        )
        self.conn.commit()

    def insert_paper_stats(self, paper_name: str, citations: int):
        """Insert paper statistics."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO paper_stats (paper_name, citations) VALUES (?, ?)",
            (paper_name, citations)
        )
        self.conn.commit()

    def insert_package_stats(self, package_name: str, downloads_last_month: int, total_downloads: int):
        """Insert package statistics."""
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO package_stats (package_name, downloads_last_month, total_downloads) VALUES (?, ?, ?)",
            (package_name, downloads_last_month, total_downloads)
        )
        self.conn.commit()

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


def fetch_github_stars(repo_full_name: str) -> int:
    """Fetch current star count for a GitHub repository."""
    try:
        headers = {}
        # Use GitHub token if available
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            headers['Authorization'] = f'token {github_token}'

        response = requests.get(f"{GITHUB_API}{repo_full_name}", headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('stargazers_count', 0)
        else:
            print(f"Failed to fetch stars for {repo_full_name}: {response.status_code}")
            return 0
    except Exception as e:
        print(f"Error fetching stars for {repo_full_name}: {e}")
        return 0


def fetch_pypi_downloads(package_name: str) -> Tuple[int, int]:
    """Fetch download statistics for a PyPI package."""
    try:
        # Note: PyPI JSON API doesn't provide download stats directly
        # We'll keep the existing values from README as PyPI stats require pypistats API
        # which has rate limits. For now, return 0,0 and we'll extract from README
        return 0, 0
    except Exception as e:
        print(f"Error fetching downloads for {package_name}: {e}")
        return 0, 0


def extract_readme_tables() -> Dict:
    """Extract current tables from README.md."""
    if not README_FILE.exists():
        print("README.md not found!")
        return {}

    with open(README_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    data = {
        'repositories': [],
        'papers': [],
        'packages': []
    }

    # Extract repositories
    repo_pattern = r'\| ([^|]+) \| (\d+) \| \[GitHub\]\((https://github\.com/[^)]+)\)'
    for match in re.finditer(repo_pattern, content):
        repo_name = match.group(1).strip()
        stars = int(match.group(2).strip())
        url = match.group(3).strip()
        data['repositories'].append({
            'name': repo_name,
            'stars': stars,
            'url': url
        })

    # Extract papers
    paper_pattern = r'\| ([^|]+) \| (\d+) \|'
    in_papers_section = False
    for line in content.split('\n'):
        if '### Papers' in line:
            in_papers_section = True
            continue
        if in_papers_section and '### ' in line:
            in_papers_section = False
        if in_papers_section and line.startswith('|') and not line.startswith('|---'):
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4 and parts[1] and parts[2].isdigit():
                    data['papers'].append({
                        'name': parts[1],
                        'citations': int(parts[2])
                    })

    # Extract packages
    package_pattern = r'\| ([^|]+) \| (\d+) \| (\d+) \|'
    in_packages_section = False
    for line in content.split('\n'):
        if '### Packages' in line:
            in_packages_section = True
            continue
        if in_packages_section and '### ' in line:
            in_packages_section = False
        if in_packages_section and line.startswith('|') and not line.startswith('|---'):
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 5 and parts[1] and parts[2].isdigit() and parts[3].isdigit():
                    data['packages'].append({
                        'name': parts[1],
                        'downloads_last_month': int(parts[2]),
                        'total_downloads': int(parts[3])
                    })

    return data


def update_repository_stars(db: DatabaseManager, repositories: List[Dict]):
    """Update GitHub repository stars and store in database."""
    print("\nUpdating repository stars...")
    updated_repos = []

    for repo in repositories[:5]:  # Update top 5 to avoid rate limits
        repo_path = repo['url'].replace('https://github.com/', '')
        stars = fetch_github_stars(repo_path)

        if stars > 0:
            repo['stars'] = stars
            db.insert_repository_stats(repo['name'], stars)
            print(f"✓ {repo['name']}: {stars:,} stars")
        else:
            # Keep existing value
            db.insert_repository_stats(repo['name'], repo['stars'])
            print(f"✓ {repo['name']}: {repo['stars']:,} stars (cached)")

        updated_repos.append(repo)
        time.sleep(1)  # Rate limiting

    return updated_repos


def update_readme_content(data: Dict):
    """Update README.md with latest data."""
    if not README_FILE.exists():
        print("README.md not found!")
        return

    with open(README_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update the date in the header
    current_date = datetime.now().strftime("%B %Y")
    content = re.sub(
        r'# The best for now [A-Za-z]+ \d{4}:',
        f'# The best for now {current_date}:',
        content
    )

    # Note: Full table update would require regenerating entire sections
    # For now, we update the header date and database tracks the evolution

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print("\n✓ README.md updated with current date")


def main():
    """Main execution function."""
    print("=" * 60)
    print("Daily README.md Update & Database Tracking")
    print("=" * 60)

    # Initialize database
    db = DatabaseManager(DB_FILE, DB_MAX_SIZE_MB)

    # Extract current data from README
    print("\nExtracting data from README.md...")
    data = extract_readme_tables()
    print(f"Found {len(data['repositories'])} repositories")
    print(f"Found {len(data['papers'])} papers")
    print(f"Found {len(data['packages'])} packages")

    # Store current snapshot in database
    print("\nStoring data in tracking database...")
    for repo in data['repositories']:
        db.insert_repository_stats(repo['name'], repo['stars'])

    for paper in data['papers']:
        db.insert_paper_stats(paper['name'], paper['citations'])

    for package in data['packages']:
        db.insert_package_stats(
            package['name'],
            package['downloads_last_month'],
            package['total_downloads']
        )

    # Update repository stars (optional - comment out to avoid API rate limits)
    # update_repository_stars(db, data['repositories'])

    # Update README content (date)
    update_readme_content(data)

    # Check database size and trim if needed
    db.check_and_trim_database()

    # Close database
    db.close()

    print("\n" + "=" * 60)
    print("Update completed successfully!")
    print(f"Database location: {DB_FILE}")
    print(f"Database size: {os.path.getsize(DB_FILE) / (1024*1024):.2f} MB")
    print("=" * 60)


if __name__ == "__main__":
    main()
