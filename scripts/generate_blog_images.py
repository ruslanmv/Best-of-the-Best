#!/usr/bin/env python3
"""
scripts/generate_blog_images.py

Generate header and teaser images for all blog posts that are missing them.
Creates professional gradient-style placeholder images using Pillow.

If PEXELS_API_KEY is set, downloads free stock photos from Pexels instead.

Usage:
    python scripts/generate_blog_images.py              # Generate placeholders
    PEXELS_API_KEY=xxx python scripts/generate_blog_images.py  # Download from Pexels
"""

import os
import re
import sys
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
POSTS_DIR = BASE_DIR / "blog" / "posts"
ASSETS_DIR = BASE_DIR / "assets" / "images"

# Color palettes for different topics
PALETTES = {
    "ai": [(30, 60, 114), (42, 82, 152), (70, 130, 180)],
    "ml": [(25, 25, 112), (65, 105, 225), (100, 149, 237)],
    "data": [(0, 100, 0), (34, 139, 34), (60, 179, 113)],
    "nlp": [(128, 0, 128), (148, 103, 189), (186, 85, 211)],
    "vision": [(139, 0, 0), (178, 34, 34), (220, 80, 80)],
    "web": [(255, 140, 0), (255, 165, 0), (255, 200, 50)],
    "default": [(44, 62, 80), (52, 73, 94), (90, 120, 150)],
}

# Topic keywords to palette mapping
TOPIC_PALETTE_MAP = {
    "llm": "ai", "langchain": "ai", "langgraph": "ai", "ollama": "ai",
    "langfun": "ai", "unsloth": "ai", "whisper": "ai", "bert": "nlp",
    "catboost": "ml", "xgboost": "ml", "tpot": "ml", "dopamine": "ml",
    "pyglove": "ml", "tensorflow": "ml", "scikit": "ml",
    "mmdet": "vision", "mmseg": "vision", "pybullet": "vision",
    "comfyui": "vision", "crawl4ai": "web", "folium": "data",
    "earthengine": "data", "autofaiss": "data", "gin": "ml",
    "llama": "ai", "video": "vision",
    # broader coverage so fewer topics fall back to the generic "default"
    "transformer": "ai", "gpt": "ai", "rag": "ai", "agent": "ai",
    "diffusion": "vision", "stable": "vision", "image": "vision", "yolo": "vision",
    "torch": "ml", "keras": "ml", "jax": "ml", "sklearn": "ml", "boost": "ml",
    "spacy": "nlp", "translation": "nlp", "embedding": "nlp", "lang": "nlp",
    "pandas": "data", "spark": "data", "duckdb": "data", "faiss": "data",
    "fastapi": "web", "flask": "web", "django": "web", "gradio": "web",
}


def get_palette(topic_id: str) -> List[Tuple[int, int, int]]:
    """Get color palette based on topic."""
    topic_lower = topic_id.lower()
    for keyword, palette_name in TOPIC_PALETTE_MAP.items():
        if keyword in topic_lower:
            return PALETTES[palette_name]
    return PALETTES["default"]


# Content category -> descriptive search terms. Obscure library names (e.g.
# "langfun", "transformerlens") don't match anything on stock-photo sites, so we
# drive the query from the topic CATEGORY instead, which yields images that
# actually relate to the post's subject area.
CATEGORY_TERMS = {
    "ai": "artificial intelligence neural network",
    "ml": "machine learning model training",
    "nlp": "language text processing communication",
    "vision": "computer vision digital imagery",
    "data": "data science analytics charts",
    "web": "software code developer interface",
    "default": "software engineering futuristic",
}


def get_category(topic_id: str) -> str:
    """Map a topic id to a content category (ai/ml/nlp/vision/data/web)."""
    topic_lower = topic_id.lower()
    for keyword, cat in TOPIC_PALETTE_MAP.items():
        if keyword in topic_lower:
            return cat
    return "default"


def create_gradient_image(
    width: int, height: int, colors: List[Tuple[int, int, int]],
    text: str = "", image_type: str = "header"
) -> Image.Image:
    """Create a professional gradient image with optional text overlay."""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # Create diagonal gradient
    c1, c2, c3 = colors[0], colors[1], colors[2] if len(colors) > 2 else colors[1]
    for y in range(height):
        for x in range(width):
            # Diagonal gradient
            t = (x / width * 0.6 + y / height * 0.4)
            if t < 0.5:
                t2 = t * 2
                r = int(c1[0] * (1 - t2) + c2[0] * t2)
                g = int(c1[1] * (1 - t2) + c2[1] * t2)
                b = int(c1[2] * (1 - t2) + c2[2] * t2)
            else:
                t2 = (t - 0.5) * 2
                r = int(c2[0] * (1 - t2) + c3[0] * t2)
                g = int(c2[1] * (1 - t2) + c3[1] * t2)
                b = int(c2[2] * (1 - t2) + c3[2] * t2)
            draw.point((x, y), fill=(r, g, b))

    # Add subtle pattern (grid dots)
    for y in range(0, height, 30):
        for x in range(0, width, 30):
            alpha = 20
            base_color = img.getpixel((x, y))
            dot_color = (
                min(255, base_color[0] + alpha),
                min(255, base_color[1] + alpha),
                min(255, base_color[2] + alpha),
            )
            draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=dot_color)

    # Add text if provided
    if text and image_type == "header":
        # Use default font (available everywhere)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        except (OSError, IOError):
            font = ImageFont.load_default()

        # Add semi-transparent overlay bar
        bar_height = 60
        bar_y = height - bar_height - 20
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            [0, bar_y, width, bar_y + bar_height],
            fill=(0, 0, 0, 100)
        )
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

        draw = ImageDraw.Draw(img)
        # Center text
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_x = (width - text_width) // 2
        text_y = bar_y + (bar_height - (bbox[3] - bbox[1])) // 2
        draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

    # Apply slight blur for smoother look
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    return img


def download_pexels_image(
    query: str, width: int, height: int, output_path: Path, variety_key: str = ""
) -> bool:
    """Download a free image from Pexels API.

    `variety_key` (e.g. the topic id) selects WHICH photo from the result page is
    used, so different posts don't collide on the identical image even when their
    queries are similar.
    """
    api_key = os.getenv("PEXELS_API_KEY")
    if not api_key or not REQUESTS_AVAILABLE:
        return False

    try:
        headers = {"Authorization": api_key}
        # Deterministic page from the query keeps results stable per category…
        seed = int(hashlib.md5(query.encode()).hexdigest()[:8], 16) % 20 + 1

        response = requests.get(
            "https://api.pexels.com/v1/search",
            headers=headers,
            params={
                "query": query,
                "per_page": 15,
                "page": seed,
                "orientation": "landscape" if width > height else "portrait",
            },
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()

        photos = data.get("photos", [])
        if not photos:
            return False

        # …while variety_key picks a distinct photo per post, avoiding duplicates.
        idx = int(hashlib.md5((variety_key or query).encode()).hexdigest()[:8], 16) % len(photos)
        photo = photos[idx]
        img_url = photo["src"].get("large2x") or photo["src"].get("large") or photo["src"]["original"]

        # Download the image
        img_response = requests.get(img_url, timeout=30)
        img_response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(img_response.content)

        # Resize to exact dimensions
        img = Image.open(output_path)
        img = img.resize((width, height), Image.LANCZOS)
        img.save(output_path, "JPEG", quality=85)

        return True

    except Exception as e:
        print(f"  Pexels download failed for '{query}': {e}")
        return False


def extract_post_metadata(post_path: Path) -> Dict:
    """Extract metadata from a blog post's front matter."""
    content = post_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.split("\n")

    metadata = {}
    in_frontmatter = False

    for line in lines[:50]:
        if line.strip() == "---":
            if in_frontmatter:
                break
            in_frontmatter = True
            continue

        if in_frontmatter:
            match = re.match(r'^(\w[\w_-]*)\s*:\s*"?([^"]*)"?\s*$', line)
            if match:
                metadata[match.group(1)] = match.group(2).strip()

    return metadata


def get_search_query(topic_id: str, topic_kind: str) -> Dict[str, str]:
    """Generate descriptive, category-aware search queries for each image type.

    Driven by the topic CATEGORY (ai/ml/nlp/vision/data/web) rather than the raw
    library name, so the stock photos actually relate to the post's subject —
    instead of the previous generic "artificial intelligence technology modern"
    that returned unrelated images (drones, music apps, buildings, …).
    """
    terms = CATEGORY_TERMS.get(get_category(topic_id), CATEGORY_TERMS["default"])
    return {
        "header-ai-abstract": f"abstract {terms} technology",
        "header-data-science": f"data science visualization {terms}",
        "header-cloud": "cloud computing data center technology",
        "teaser-ai": f"{terms} technology concept",
    }


def process_post(post_path: Path) -> int:
    """Process a single blog post and generate missing images. Returns count of images created."""
    metadata = extract_post_metadata(post_path)
    topic_id = metadata.get("topic_id", "")
    topic_kind = metadata.get("topic_kind", "")
    title = metadata.get("title", "")

    if not topic_id:
        return 0

    # Determine the image directory from the post's header image path
    content = post_path.read_text(encoding="utf-8", errors="ignore")
    header_match = re.search(r'overlay_image:\s*(/assets/images/[^/]+)/(.+)', content)
    teaser_match = re.search(r'teaser:\s*(/assets/images/[^/]+)/(.+)', content)

    if not header_match:
        return 0

    img_dir_rel = header_match.group(1).lstrip("/")
    img_dir = BASE_DIR / img_dir_rel

    # Collect all image files referenced in this post
    referenced_images = set()
    for match in re.finditer(r'/assets/images/[^/]+/([^\s"]+)', content):
        referenced_images.add(match.group(1))

    # Standard images every post should have
    standard_images = {
        "header-ai-abstract.jpg": (1920, 600),
        "header-data-science.jpg": (1920, 600),
        "header-cloud.jpg": (1920, 600),
        "teaser-ai.jpg": (600, 400),
    }

    palette = get_palette(topic_id)
    created = 0
    queries = get_search_query(topic_id, topic_kind)

    for img_name, (w, h) in standard_images.items():
        img_path = img_dir / img_name
        if img_path.exists():
            continue

        img_dir.mkdir(parents=True, exist_ok=True)

        # Try Pexels first (variety_key keeps each post's image distinct)
        query = queries.get(img_name.replace(".jpg", ""), f"technology abstract {topic_id}")
        if download_pexels_image(query, w, h, img_path, variety_key=f"{topic_id}:{img_name}"):
            print(f"  Downloaded from Pexels: {img_name}")
            created += 1
            time.sleep(0.5)  # Rate limit
            continue

        # Fall back to generated gradient image
        display_text = title if "header" in img_name else ""
        img = create_gradient_image(w, h, palette, display_text, "header" if "header" in img_name else "teaser")
        img.save(img_path, "JPEG", quality=90)
        print(f"  Generated: {img_name}")
        created += 1

    return created


def main():
    print("=" * 60)
    print("Blog Post Image Generator")
    print("=" * 60)

    pexels_key = os.getenv("PEXELS_API_KEY")
    if pexels_key:
        print(f"Mode: Pexels API (with gradient fallback)")
    else:
        print(f"Mode: Generated gradient images (set PEXELS_API_KEY for stock photos)")
    print()

    posts = sorted(POSTS_DIR.glob("*.md"))
    total_created = 0
    posts_fixed = 0

    for post_path in posts:
        if post_path.name == "index.json":
            continue

        metadata = extract_post_metadata(post_path)
        topic_id = metadata.get("topic_id", "unknown")
        print(f"Processing: {post_path.name} (topic: {topic_id})")

        created = process_post(post_path)
        if created > 0:
            total_created += created
            posts_fixed += 1
            print(f"  -> Created {created} image(s)")
        else:
            print(f"  -> All images present")

    print()
    print("=" * 60)
    print(f"Done! Created {total_created} images for {posts_fixed} posts.")
    print("=" * 60)


if __name__ == "__main__":
    main()
