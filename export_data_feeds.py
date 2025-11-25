#!/usr/bin/env python3
"""
Export README data to JSON and RSS feeds for consumption by other systems.
Creates API endpoints in blog/api/ directory for GitHub Pages.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuration
README_FILE = Path("README.md")
API_DIR = Path("blog/api")
GITHUB_REPO = "https://github.com/ruslanmv/Best-of-the-Best"
SITE_URL = "https://ruslanmv.github.io/Best-of-the-Best"


def extract_readme_data() -> Dict:
    """Extract all data from README.md."""
    if not README_FILE.exists():
        print("❌ README.md not found!")
        return {}

    with open(README_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    data = {
        'repositories': [],
        'papers': [],
        'packages': [],
        'last_updated': datetime.now().isoformat()
    }

    # Extract repositories
    repo_section_start = content.find('### Repositories')
    repo_section_end = content.find('### Papers')

    if repo_section_start != -1 and repo_section_end != -1:
        repo_section = content[repo_section_start:repo_section_end]
        repo_pattern = r'\| ([^|]+) \| (\d+) \| \[GitHub\]\((https://github\.com/[^)]+)\)'

        for match in re.finditer(repo_pattern, repo_section):
            data['repositories'].append({
                'name': match.group(1).strip(),
                'stars': int(match.group(2).strip()),
                'url': match.group(3).strip()
            })

    # Extract papers
    paper_section_start = content.find('### Papers')
    paper_section_end = content.find('### Packages')

    if paper_section_start != -1 and paper_section_end != -1:
        paper_section = content[paper_section_start:paper_section_end]
        lines = paper_section.split('\n')

        for line in lines:
            if line.startswith('|') and not line.startswith('|---'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4 and parts[1] and parts[2].isdigit():
                    # Extract DOI link if present
                    doi_match = re.search(r'doi\.org/([^)]+)', line)
                    url = f"https://doi.org/{doi_match.group(1)}" if doi_match else ""

                    data['papers'].append({
                        'name': parts[1],
                        'citations': int(parts[2]),
                        'url': url
                    })

    # Extract packages
    package_section_start = content.find('### Packages')

    if package_section_start != -1:
        # Find the end of packages section (next ### or end of relevant content)
        remaining_content = content[package_section_start:]
        next_section = remaining_content.find('# Some notebooks')
        if next_section == -1:
            next_section = len(remaining_content)

        package_section = remaining_content[:next_section]
        lines = package_section.split('\n')

        for line in lines:
            if line.startswith('|') and not line.startswith('|---'):
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 5 and parts[1] and parts[2].isdigit() and parts[3].isdigit():
                    # Extract PyPI URL
                    url_match = re.search(r'pypi\.org/([^/)]+)', line)
                    package_name = url_match.group(1) if url_match else parts[1]

                    data['packages'].append({
                        'name': parts[1],
                        'downloads_last_month': int(parts[2]),
                        'total_downloads': int(parts[3]),
                        'url': f"https://pypi.org/project/{package_name}/"
                    })

    return data


def create_json_feeds(data: Dict):
    """Create JSON API files."""
    API_DIR.mkdir(parents=True, exist_ok=True)

    # Main data file
    with open(API_DIR / 'data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Created {API_DIR / 'data.json'}")

    # Individual feeds
    with open(API_DIR / 'repositories.json', 'w', encoding='utf-8') as f:
        json.dump({
            'repositories': data['repositories'],
            'last_updated': data['last_updated']
        }, f, indent=2, ensure_ascii=False)
    print(f"✅ Created {API_DIR / 'repositories.json'}")

    with open(API_DIR / 'papers.json', 'w', encoding='utf-8') as f:
        json.dump({
            'papers': data['papers'],
            'last_updated': data['last_updated']
        }, f, indent=2, ensure_ascii=False)
    print(f"✅ Created {API_DIR / 'papers.json'}")

    with open(API_DIR / 'packages.json', 'w', encoding='utf-8') as f:
        json.dump({
            'packages': data['packages'],
            'last_updated': data['last_updated']
        }, f, indent=2, ensure_ascii=False)
    print(f"✅ Created {API_DIR / 'packages.json'}")


def create_rss_feed(data: Dict):
    """Create RSS feed for the data."""
    # Create RSS feed
    rss = ET.Element('rss', version='2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')

    channel = ET.SubElement(rss, 'channel')

    ET.SubElement(channel, 'title').text = 'Best of the Best AI - Daily Updates'
    ET.SubElement(channel, 'link').text = SITE_URL
    ET.SubElement(channel, 'description').text = 'Daily updates on top AI repositories, papers, and packages'
    ET.SubElement(channel, 'language').text = 'en-us'
    ET.SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')

    # Add atom:link for self-reference
    atom_link = ET.SubElement(channel, '{http://www.w3.org/2005/Atom}link')
    atom_link.set('href', f'{SITE_URL}/api/feed.xml')
    atom_link.set('rel', 'self')
    atom_link.set('type', 'application/rss+xml')

    # Add top repositories as items
    for repo in data['repositories'][:10]:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = f"⭐ {repo['name']} - {repo['stars']:,} stars"
        ET.SubElement(item, 'link').text = repo['url']
        ET.SubElement(item, 'description').text = f"GitHub repository with {repo['stars']:,} stars"
        ET.SubElement(item, 'pubDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        ET.SubElement(item, 'guid').text = repo['url']

    # Add top papers
    for paper in data['papers'][:10]:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = f"📄 {paper['name']} - {paper['citations']:,} citations"
        if paper['url']:
            ET.SubElement(item, 'link').text = paper['url']
        ET.SubElement(item, 'description').text = f"Research paper with {paper['citations']:,} citations"
        ET.SubElement(item, 'pubDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        if paper['url']:
            ET.SubElement(item, 'guid').text = paper['url']

    # Add top packages
    for package in data['packages'][:10]:
        item = ET.SubElement(channel, 'item')
        ET.SubElement(item, 'title').text = f"📦 {package['name']} - {package['downloads_last_month']:,} monthly downloads"
        ET.SubElement(item, 'link').text = package['url']
        ET.SubElement(item, 'description').text = f"PyPI package with {package['total_downloads']:,} total downloads"
        ET.SubElement(item, 'pubDate').text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')
        ET.SubElement(item, 'guid').text = package['url']

    # Pretty print XML
    xml_string = minidom.parseString(ET.tostring(rss)).toprettyxml(indent='  ')

    # Write RSS feed
    with open(API_DIR / 'feed.xml', 'w', encoding='utf-8') as f:
        f.write(xml_string)

    print(f"✅ Created {API_DIR / 'feed.xml'}")


def create_readme_api():
    """Create API documentation in README format."""
    api_readme = f"""# Best of the Best AI - Data API

## Available Endpoints

All endpoints are available as static JSON files hosted on GitHub Pages.

Base URL: `{SITE_URL}/api/`

### 📊 Main Data Feed
- **URL**: `/api/data.json`
- **Description**: Complete dataset with all repositories, papers, and packages
- **Format**: JSON
- **Example**: `{SITE_URL}/api/data.json`

### ⭐ Repositories
- **URL**: `/api/repositories.json`
- **Description**: Top GitHub repositories with star counts
- **Format**: JSON
- **Fields**: `name`, `stars`, `url`

### 📄 Papers
- **URL**: `/api/papers.json`
- **Description**: Most cited research papers
- **Format**: JSON
- **Fields**: `name`, `citations`, `url`

### 📦 Packages
- **URL**: `/api/packages.json`
- **Description**: Top PyPI packages with download statistics
- **Format**: JSON
- **Fields**: `name`, `downloads_last_month`, `total_downloads`, `url`

### 📰 RSS Feed
- **URL**: `/api/feed.xml`
- **Description**: RSS feed for daily updates
- **Format**: RSS 2.0
- **Subscribe**: Add to your RSS reader

## Usage Examples

### JavaScript (Fetch API)
```javascript
// Fetch all data
fetch('{SITE_URL}/api/data.json')
  .then(response => response.json())
  .then(data => {{
    console.log('Repositories:', data.repositories);
    console.log('Papers:', data.papers);
    console.log('Packages:', data.packages);
  }});
```

### Python
```python
import requests

# Fetch repositories
response = requests.get('{SITE_URL}/api/repositories.json')
data = response.json()

for repo in data['repositories']:
    print(f"{{repo['name']}}: {{repo['stars']}} stars")
```

### cURL
```bash
# Download all data
curl {SITE_URL}/api/data.json

# Download specific category
curl {SITE_URL}/api/repositories.json
```

## Update Frequency

- Data is updated **daily** via GitHub Actions
- Last update timestamp is included in all JSON responses
- RSS feed reflects the latest changes

## License

Data is aggregated from public sources:
- GitHub API (repositories)
- Semantic Scholar (papers)
- PyPI (packages)

Please respect rate limits and terms of service of the original data sources.

## Questions or Issues?

Visit our [GitHub repository]({GITHUB_REPO}) to report issues or request features.

---

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

    with open(API_DIR / 'README.md', 'w', encoding='utf-8') as f:
        f.write(api_readme)

    print(f"✅ Created {API_DIR / 'README.md'}")


def main():
    """Main execution function."""
    print("=" * 60)
    print("Exporting Data Feeds for GitHub Pages")
    print("=" * 60)

    # Extract data from README
    print("\n📖 Reading README.md...")
    data = extract_readme_data()

    if not data or not data.get('repositories'):
        print("❌ No data extracted from README.md")
        return

    print(f"✅ Extracted {len(data['repositories'])} repositories")
    print(f"✅ Extracted {len(data['papers'])} papers")
    print(f"✅ Extracted {len(data['packages'])} packages")

    # Create JSON feeds
    print("\n📝 Creating JSON feeds...")
    create_json_feeds(data)

    # Create RSS feed
    print("\n📰 Creating RSS feed...")
    create_rss_feed(data)

    # Create API documentation
    print("\n📚 Creating API documentation...")
    create_readme_api()

    print("\n" + "=" * 60)
    print("✅ Data feeds exported successfully!")
    print(f"📁 API directory: {API_DIR}")
    print(f"🌐 Access via: {SITE_URL}/api/")
    print("=" * 60)


if __name__ == "__main__":
    main()
