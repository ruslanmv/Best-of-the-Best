"""
Generate index.json for blog posts to enable dynamic loading
"""

import json
from pathlib import Path
from datetime import datetime
import re


def extract_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown file"""
    frontmatter = {}

    # Check if file has frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter_text = parts[1].strip()

            # Parse simple YAML
            for line in frontmatter_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')

                    # Handle tags (array)
                    if key == 'tags':
                        # Extract tags from ["tag1", "tag2"] format
                        tags = re.findall(r'"([^"]*)"', value)
                        frontmatter[key] = tags
                    else:
                        frontmatter[key] = value

            # Get excerpt from content
            content_body = parts[2].strip()
            # Get first paragraph as excerpt
            paragraphs = [p.strip() for p in content_body.split('\n\n') if p.strip() and not p.strip().startswith('#')]
            if paragraphs:
                excerpt = paragraphs[0][:200] + '...' if len(paragraphs[0]) > 200 else paragraphs[0]
                frontmatter['excerpt'] = excerpt

    return frontmatter


def generate_posts_index():
    """Generate index.json file for all blog posts"""
    posts_dir = Path('blog/posts')
    posts_dir.mkdir(parents=True, exist_ok=True)

    posts = []

    # Scan all markdown files
    for md_file in posts_dir.glob('*.md'):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()

            frontmatter = extract_frontmatter(content)

            post_info = {
                'filename': md_file.name,
                'title': frontmatter.get('title', md_file.stem),
                'date': frontmatter.get('date', datetime.now().isoformat()),
                'author': frontmatter.get('author', 'AI Multi-Agent System'),
                'tags': frontmatter.get('tags', ['AI', 'Machine Learning']),
                'excerpt': frontmatter.get('excerpt', '')
            }

            posts.append(post_info)

        except Exception as e:
            print(f"Error processing {md_file}: {e}")

    # Write index.json
    index_file = posts_dir / 'index.json'
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated index with {len(posts)} posts")
    print(f"📝 Index file: {index_file}")

    return posts


if __name__ == '__main__':
    generate_posts_index()
