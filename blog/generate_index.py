"""
generate_api_data.py (or generate_index.py)

Unified Data Generator for Best-of-the-Best Dashboard.
1. Reads "Truth Data" from data/*.json.
2. Reads "Content Data" from blog/posts/*.md.
3. Merges, sorts, and normalizes them.
4. Outputs standardized JSON APIs to blog/api/*.json.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# --- Configuration ---
# Detect root directory to ensure we find 'data/' correctly
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
POSTS_DIR = BASE_DIR / "blog" / "posts"
API_DIR = BASE_DIR / "blog" / "api"

# Ensure output dir exists
API_DIR.mkdir(parents=True, exist_ok=True)

# --- Helper Functions ---

def load_items_from_json(filepath):
    """
    Loads a JSON file and intelligently extracts a list of items.
    Handles direct lists and wrapper dicts.
    """
    if not filepath.exists():
        # Fallback: try relative to current working directory
        filepath = Path("data") / filepath.name
        if not filepath.exists():
            return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Case 1: The file is directly a list [{}, {}]
        if isinstance(data, list):
            return data
        
        # Case 2: The file is a dictionary (wrapper) {"papers": [{}, {}]}
        if isinstance(data, dict):
            known_keys = [
                "papers", "research", 
                "courses", "cources", 
                "tutorials", 
                "notebooks", 
                "repositories", "packages"
            ]
            for key in known_keys:
                if key in data and isinstance(data[key], list):
                    return data[key]
                    
        return []
    except Exception as e:
        print(f"⚠️  Warning: Could not parse {filepath}: {e}")
        return []

def load_citations_map(filepath):
    """
    Specific loader for data/citations.json: { "Title": ["url", count], ... }
    """
    if not filepath.exists():
        filepath = Path("data") / filepath.name
        if not filepath.exists():
            return []
            
    items = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict):
                for title, info in data.items():
                    if isinstance(info, list) and len(info) >= 1:
                        items.append({
                            "title": title,
                            "url": info[0],
                            "citations": info[1] if len(info) > 1 else 0,
                            "tags": ["Research", "Citation"]
                        })
    except Exception as e:
        print(f"⚠️  Error loading citations {filepath}: {e}")
    return items

def normalize_item(item, default_category, default_tags):
    """
    Converts diverse raw data formats into the standard Dashboard Item Schema.
    """
    # CRITICAL FIX: Guard against non-dict items (strings/integers) in the list
    if not isinstance(item, dict):
        return None

    # 1. Title
    title = item.get("title") or item.get("name") or "Untitled Resource"
    
    # 2. URL Strategy
    # Priority: Explicit URL -> Colab -> Parsed from 'links' list -> #
    url = item.get("url") or item.get("link") or item.get("colab")
    
    if not url and "links" in item and isinstance(item["links"], list):
        # links format: [["type", "url", ...], ["git", "url", ...]]
        for link_entry in item["links"]:
            if isinstance(link_entry, list) and len(link_entry) >= 2:
                link_type = link_entry[0]
                link_url = link_entry[1]
                # Prioritize project/demo/arxiv links, fallback to git
                if link_type in ["project", "demo", "arxiv", "paper", "pypi"]:
                    url = link_url
                    break
                if not url: # Take the first one if nothing better found
                    url = link_url

    if not url:
        url = "#"
    
    # 3. Date
    raw_date = item.get("date") or item.get("published_at") or item.get("update")
    if isinstance(raw_date, (int, float)):
        date = datetime.fromtimestamp(raw_date).isoformat()
    elif raw_date:
        date = str(raw_date)
    else:
        date = datetime.now().isoformat()
    
    # 4. Author
    raw_author = item.get("author") or item.get("provider") or item.get("publisher")
    if isinstance(raw_author, list) and len(raw_author) > 0:
        if isinstance(raw_author[0], list) and len(raw_author[0]) > 0:
            author = raw_author[0][0] # [["Name", "Url"]] -> "Name"
        elif isinstance(raw_author[0], str):
            author = raw_author[0]
        else:
            author = "AI Agent"
    elif isinstance(raw_author, str):
        author = raw_author
    else:
        author = "AI Agent"
    
    # 5. Tags
    raw_tags = item.get("tags", [])
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]
    final_tags = list(set(raw_tags + default_tags))
    
    # 6. Excerpt
    excerpt = item.get("excerpt") or item.get("description") or item.get("summary") or ""
    if excerpt:
        excerpt = excerpt[:200] + "..." if len(excerpt) > 200 else excerpt

    return {
        "title": title,
        "url": url,
        "date": date,
        "author": author,
        "tags": final_tags,
        "category": default_category,
        "excerpt": excerpt
    }

def process_markdown_posts():
    """Scans blog/posts/*.md for manual content."""
    posts = []
    if not POSTS_DIR.exists():
        return posts
        
    for md_file in POSTS_DIR.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            frontmatter = {}
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    yaml_block = parts[1]
                    for line in yaml_block.split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            frontmatter[k.strip()] = v.strip().strip('"\'')
            
            tags = frontmatter.get("tags", "general")
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.replace("[", "").replace("]", "").split(",")]
            
            cat = "general"
            lower_tags = [t.lower() for t in tags]
            if any(x in lower_tags for x in ['course', 'education']): cat = "courses"
            elif any(x in lower_tags for x in ['paper', 'research', 'arxiv']): cat = "research"
            elif any(x in lower_tags for x in ['tutorial', 'guide', 'code']): cat = "tutorials"
            elif any(x in lower_tags for x in ['notebook', 'jupyter', 'colab']): cat = "notebooks"
            
            posts.append({
                "title": frontmatter.get("title", md_file.stem),
                "url": f"posts/{md_file.stem}.html",
                "date": frontmatter.get("date", datetime.now().isoformat()),
                "author": frontmatter.get("author", "Editor"),
                "tags": tags,
                "category": cat,
                "excerpt": frontmatter.get("excerpt", "")
            })
        except Exception as e:
            print(f"Skipping {md_file}: {e}")
    return posts

# --- Main Logic ---

def main():
    print("🚀 Starting Data Feed Generation...")
    
    # 1. Load Raw Data
    raw_courses   = load_items_from_json(DATA_DIR / "courses.json") 
    raw_courses  += load_items_from_json(DATA_DIR / "cources.json") 
    
    raw_research  = load_items_from_json(DATA_DIR / "research.json")
    raw_research += load_items_from_json(DATA_DIR / "papers.json")
    raw_research += load_citations_map(DATA_DIR / "citations.json")
    
    raw_tutorials = load_items_from_json(DATA_DIR / "tutorials.json")
    
    # 2. Normalize Data
    courses = [normalize_item(i, "courses", ["Course"]) for i in raw_courses if i]
    research = [normalize_item(i, "research", ["Paper"]) for i in raw_research if i]
    
    # Normalize tutorials (keep them all as tutorials initially)
    tutorials = [normalize_item(i, "tutorials", ["Tutorial"]) for i in raw_tutorials if i]
    
    # Filter None/invalid items
    courses = [x for x in courses if x]
    research = [x for x in research if x]
    tutorials = [x for x in tutorials if x]

    # 3. Special Handling: Notebooks
    # Strategy: 
    # - If data/notebooks.json exists, use it.
    # - PLUS: Identify notebooks hidden inside tutorials and COPY them to notebooks list.
    #   (This fixes the issue where tutorials became 0 because they were moved)
    
    notebooks = []
    
    # Load explicit notebooks
    raw_nb_file = load_items_from_json(DATA_DIR / "notebooks.json")
    if raw_nb_file:
        explicit_notebooks = [normalize_item(i, "notebooks", ["Notebook"]) for i in raw_nb_file if i]
        notebooks.extend([x for x in explicit_notebooks if x])

    # Extract implicit notebooks from tutorials (COPY, do not move)
    for t in tutorials:
        title_lower = t['title'].lower()
        url_lower = t['url'].lower()
        # Check if it looks like a notebook
        if 'notebook' in title_lower or 'colab' in url_lower or 'jupyter' in title_lower:
            # Create a copy for the notebook category
            nb_copy = t.copy()
            nb_copy['category'] = 'notebooks'
            if 'Notebook' not in nb_copy['tags']:
                nb_copy['tags'] = nb_copy['tags'] + ['Notebook']
            notebooks.append(nb_copy)

    # 4. Merge with Manual Blog Posts
    blog_posts = process_markdown_posts()
    for post in blog_posts:
        if post['category'] == 'courses': courses.append(post)
        elif post['category'] == 'research': research.append(post)
        elif post['category'] == 'tutorials': tutorials.append(post)
        elif post['category'] == 'notebooks': notebooks.append(post)
    
    # 5. Sort by Date
    def sort_key(x): return x.get('date', '0000')
    
    courses.sort(key=sort_key, reverse=True)
    research.sort(key=sort_key, reverse=True)
    tutorials.sort(key=sort_key, reverse=True)
    notebooks.sort(key=sort_key, reverse=True)
    
    # 6. Deduplicate Research
    seen_urls = set()
    unique_research = []
    for r in research:
        if r['url'] not in seen_urls and r['url'] != "#":
            unique_research.append(r)
            seen_urls.add(r['url'])
    research = unique_research

    # Deduplicate Notebooks (since we might have overlaps)
    seen_nb_urls = set()
    unique_notebooks = []
    for n in notebooks:
        if n['url'] not in seen_nb_urls and n['url'] != "#":
            unique_notebooks.append(n)
            seen_nb_urls.add(n['url'])
    notebooks = unique_notebooks

    dashboard_data = {
        "stats": {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "total_courses": len(courses),
            "total_papers": len(research),
            "total_tutorials": len(tutorials)
        },
        "trending": (research[:2] + tutorials[:2] + courses[:1]),
        "courses": courses,
        "research": research,
        "tutorials": tutorials,
        "notebooks": notebooks,
        "all_posts": blog_posts
    }
    
    # 7. Write Files
    def write_json(path, data):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✅ Generated {path} ({len(data) if isinstance(data, list) else 'Object'})")

    write_json(API_DIR / "courses.json", courses)
    write_json(API_DIR / "research.json", research)
    write_json(API_DIR / "tutorials.json", tutorials)
    write_json(API_DIR / "notebooks.json", notebooks)
    write_json(API_DIR / "dashboard.json", dashboard_data)

    # 8. Call HTML Generator
    try:
        import generate_index_html
        print("🌍 Running HTML Blog Index Generator...")
        generate_index_html.main()
    except ImportError:
        print("⚠️  Warning: generate_index_html.py not found. Skipping HTML index generation.")


if __name__ == "__main__":
    main()