#!/usr/bin/env python3
"""
scripts/image_tools.py

Production Image Tools for Blog Generation - FIXED v3.3
- Organized asset storage per blog post (no overwrites)
- Professional naming conventions
- Stock photo downloads from Pexels with custom filenames
- Architecture diagrams with graphviz
- Data visualization charts
- Website screenshots
- GitHub Actions / CI/CD compatible
"""

import os
import sys
import requests
import matplotlib
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from typing import Optional
import re

# Essential for headless environments
matplotlib.use('Agg')

# Silence matplotlib warnings
import warnings
warnings.filterwarnings('ignore', category=UserWarning, module='matplotlib')

# CrewAI tool decorator import
try:
    from crewai.tools import tool as _crewai_tool_decorator
except Exception:
    try:
        from crewai_tools import tool as _crewai_tool_decorator
    except Exception:
        def _crewai_tool_decorator(*args, **kwargs):
            def decorator(func):
                return func
            return decorator

# ============================================================================
# PATH MANAGEMENT - ORGANIZED BY BLOG POST
# ============================================================================
WORKSPACE = Path(os.getcwd())
BASE_ASSETS_DIR = WORKSPACE / "assets" / "images"
BASE_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# Global variable to store current blog context
_CURRENT_BLOG_CONTEXT = {
    "slug": None,
    "date": None,
    "topic": None,
}


def set_blog_context(slug: str, topic: str = None, date: str = None) -> Path:
    """
    Set the current blog context for organized asset storage.
    
    Creates directory structure: assets/images/YYYY-MM-DD-slug/
    
    Args:
        slug: Blog post slug (e.g., "package-scikit-learn")
        topic: Topic name for folder naming (optional)
        date: Date string YYYY-MM-DD (defaults to today)
    
    Returns:
        Path to the blog's asset directory
    
    Example:
        >>> set_blog_context("package-scikit-learn", date="2025-12-05")
        Path('assets/images/2025-12-05-package-scikit-learn')
    """
    global _CURRENT_BLOG_CONTEXT
    
    # Use provided date or default to today
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    # Clean slug for filesystem
    clean_slug = re.sub(r'[^a-z0-9-]', '', slug.lower())
    
    # Create folder name: YYYY-MM-DD-slug
    folder_name = f"{date}-{clean_slug}"
    
    # Create full path
    blog_assets_dir = BASE_ASSETS_DIR / folder_name
    blog_assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Update global context
    _CURRENT_BLOG_CONTEXT["slug"] = clean_slug
    _CURRENT_BLOG_CONTEXT["date"] = date
    _CURRENT_BLOG_CONTEXT["topic"] = topic or clean_slug
    
    return blog_assets_dir


def get_blog_assets_dir() -> Path:
    """
    Get the current blog's asset directory.
    Falls back to base directory if no context set.
    
    Returns:
        Path to current blog's assets or base assets directory
    """
    if _CURRENT_BLOG_CONTEXT["slug"]:
        date = _CURRENT_BLOG_CONTEXT["date"]
        slug = _CURRENT_BLOG_CONTEXT["slug"]
        folder = f"{date}-{slug}"
        return BASE_ASSETS_DIR / folder
    
    # Fallback to base directory
    return BASE_ASSETS_DIR


def get_professional_filename(base_name: str, asset_type: str, extension: str = "jpg") -> str:
    """
    Generate professional filename with blog context.
    
    Args:
        base_name: Base name (e.g., "header", "chart", "diagram")
        asset_type: Type descriptor (e.g., "ai-abstract", "accuracy-comparison")
        extension: File extension without dot
    
    Returns:
        Professional filename like "header-ai-abstract.jpg" or "chart-accuracy-comparison.png"
    
    Example:
        >>> get_professional_filename("chart", "accuracy-comparison", "png")
        'chart-accuracy-comparison.png'
    """
    # Clean components
    clean_base = re.sub(r'[^a-z0-9-]', '', base_name.lower())
    clean_type = re.sub(r'[^a-z0-9-]', '', asset_type.lower())
    
    # Combine
    if clean_type:
        filename = f"{clean_base}-{clean_type}.{extension}"
    else:
        filename = f"{clean_base}.{extension}"
    
    return filename


class ImageTools:
    """Production-ready image tools with organized asset management."""

    # =========================================================================
    # Stock Photo Download
    # =========================================================================
    @staticmethod
    def get_stock_photo(
        query: str, 
        filename: Optional[str] = None,
        asset_type: str = "stock"
    ) -> str:
        """
        Downloads a stock photo from Pexels API with organized storage.
        
        Args:
            query: Search query (e.g., "artificial intelligence abstract")
            filename: Custom filename (e.g., "header-ai-abstract.jpg")
                     If None, generates professional filename
            asset_type: Asset type for auto-naming (e.g., "header", "teaser")
        
        Returns:
            Absolute path to downloaded image, or error message starting with "Error:"
        
        Environment:
            PEXELS_API_KEY: Your Pexels API key (get free at https://www.pexels.com/api)
        
        Example:
            >>> set_blog_context("package-scikit-learn", date="2025-12-05")
            >>> ImageTools.get_stock_photo("ai abstract", asset_type="header")
            '/path/to/assets/images/2025-12-05-package-scikit-learn/header-ai-abstract.jpg'
        """
        api_key = os.getenv("PEXELS_API_KEY")

        if not api_key:
            return "Error: PEXELS_API_KEY not set. Get free key at https://www.pexels.com/api/"

        # Clean query
        safe_query = "".join(c for c in query if c.isalnum() or c in (' ', '-', '_')).strip()

        if not safe_query:
            return "Error: Invalid search query"

        headers = {"Authorization": api_key}
        url = "https://api.pexels.com/v1/search"
        params = {
            "query": query,
            "per_page": 1,
            "orientation": "landscape",
            "size": "large",
        }

        try:
            # Search for image
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            if not data.get("photos"):
                return f"Error: No images found for '{query}'"

            # Get high-quality image URL
            image_url = data["photos"][0]["src"]["large2x"]

            # Download image
            img_response = requests.get(image_url, timeout=30)
            img_response.raise_for_status()

            # Get blog-specific directory
            blog_dir = get_blog_assets_dir()

            # Determine output filename
            if filename:
                safe_filename = filename if filename.endswith(('.jpg', '.jpeg', '.png')) else f"{filename}.jpg"
            else:
                # Generate professional filename
                query_slug = safe_query.replace(' ', '-')[:30]  # Limit length
                safe_filename = get_professional_filename(asset_type, query_slug, "jpg")

            # Full path
            filepath = blog_dir / safe_filename

            with open(filepath, 'wb') as f:
                f.write(img_response.content)

            return str(filepath.absolute())

        except requests.exceptions.Timeout:
            return "Error: Pexels API timeout (check network connection)"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                return "Error: Invalid PEXELS_API_KEY"
            elif e.response.status_code == 429:
                return "Error: Pexels API rate limit reached (200 requests/hour)"
            else:
                return f"Error: Pexels API returned {e.response.status_code}"
        except Exception as e:
            return f"Error: {type(e).__name__}: {str(e)}"

    # =========================================================================
    # Architecture Diagram
    # =========================================================================
    @staticmethod
    def generate_architecture_diagram(python_code: str, diagram_name: str = "architecture") -> str:
        """
        Generates architecture diagrams with organized storage.
        
        Args:
            python_code: Python code using 'diagrams' library
            diagram_name: Name for the diagram (e.g., "web-service", "database-schema")
        
        Returns:
            Success message or error starting with "Error:"
        
        IMPORTANT: Update the code to use blog-specific directory:
            with Diagram("Title", show=False, filename=f"{output_dir}/diagram-name"):
        
        Example:
            >>> set_blog_context("package-kubernetes")
            >>> code = '''
            ... from diagrams import Diagram
            ... output_dir = "assets/images/2025-12-05-package-kubernetes"
            ... with Diagram("K8s", show=False, filename=f"{output_dir}/diagram-k8s"):
            ...     pass
            ... '''
            >>> ImageTools.generate_architecture_diagram(code, "k8s-architecture")
        """
        try:
            try:
                import diagrams  # noqa: F401
            except ImportError:
                return "Error: 'diagrams' library not installed. Install: pip install diagrams"

            import shutil
            if not shutil.which('dot'):
                return "Error: Graphviz not installed. Install: apt-get install graphviz"

            # Get blog-specific directory
            blog_dir = get_blog_assets_dir()
            
            # Inject blog directory into execution context
            exec_globals = {
                '__name__': '__main__',
                'output_dir': str(blog_dir),
                'blog_assets_dir': str(blog_dir),
            }
            
            exec(python_code, exec_globals)

            return f"Success: Diagram '{diagram_name}' generated in {blog_dir.relative_to(WORKSPACE)}"

        except ImportError as e:
            missing = str(e).split("'")[1] if "'" in str(e) else "unknown"
            return f"Error: Missing module '{missing}'. Install: pip install {missing}"
        except SyntaxError as e:
            return f"Error: Invalid Python syntax at line {e.lineno}: {e.msg}"
        except Exception as e:
            error_type = type(e).__name__
            return f"Error: {error_type}: {str(e)}"

    # =========================================================================
    # Data Chart
    # =========================================================================
    @staticmethod
    def create_chart(
        x_values: list,
        y_values: list,
        title: str,
        x_label: str,
        y_label: str,
        filename: Optional[str] = None,
        chart_name: str = "chart",
        style: str = "standard",
    ) -> str:
        """
        Creates line charts with organized storage.
        
        Args:
            x_values: X-axis values
            y_values: Y-axis values
            title: Chart title
            x_label: X-axis label
            y_label: Y-axis label
            filename: Custom filename (auto-generated if None)
            chart_name: Descriptive name (e.g., "accuracy-comparison", "sales-growth")
            style: "standard" or "xkcd"
        
        Returns:
            Absolute path to chart, or error message
        
        Example:
            >>> set_blog_context("package-sklearn")
            >>> ImageTools.create_chart(
            ...     x_values=[1, 2, 3], y_values=[0.8, 0.9, 0.95],
            ...     title="Model Accuracy", x_label="Epoch", y_label="Accuracy",
            ...     chart_name="accuracy-comparison"
            ... )
            '/path/to/assets/images/2025-12-05-package-sklearn/chart-accuracy-comparison.png'
        """
        if not x_values or not y_values:
            return "Error: Empty data values"

        if len(x_values) != len(y_values):
            return f"Error: Length mismatch (x={len(x_values)}, y={len(y_values)})"

        try:
            # Get blog-specific directory
            blog_dir = get_blog_assets_dir()

            # Determine filename
            if filename:
                safe_filename = filename if filename.endswith('.png') else f"{filename}.png"
            else:
                # Professional filename
                clean_name = re.sub(r'[^a-z0-9-]', '', chart_name.lower())
                safe_filename = get_professional_filename("chart", clean_name, "png")

            filepath = blog_dir / safe_filename

            # Create chart
            if style == "xkcd":
                try:
                    with plt.xkcd():
                        ImageTools._plot_chart(x_values, y_values, title, x_label, y_label, filepath)
                except Exception:
                    print("⚠️  XKCD style unavailable, using standard", file=sys.stderr)
                    ImageTools._plot_chart(x_values, y_values, title, x_label, y_label, filepath)
            else:
                ImageTools._plot_chart(x_values, y_values, title, x_label, y_label, filepath)

            return str(filepath.absolute())

        except Exception as e:
            return f"Error: {type(e).__name__}: {str(e)}"

    @staticmethod
    def _plot_chart(x, y, title, xlabel, ylabel, path):
        """Internal helper for chart creation"""
        plt.figure(figsize=(10, 6))
        plt.plot(x, y, marker='o', linewidth=2, markersize=8)
        plt.title(title, fontsize=16, fontweight='bold')
        plt.xlabel(xlabel, fontsize=12)
        plt.ylabel(ylabel, fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close()

    # =========================================================================
    # Website Screenshot
    # =========================================================================
    @staticmethod
    def take_screenshot(
        url: str, 
        filename: Optional[str] = None,
        screenshot_name: str = "screenshot"
    ) -> str:
        """
        Captures website screenshots with organized storage.
        
        Args:
            url: Website URL
            filename: Custom filename (auto-generated if None)
            screenshot_name: Descriptive name (e.g., "github-profile", "docs-homepage")
        
        Returns:
            Absolute path to screenshot, or error message
        
        Example:
            >>> set_blog_context("package-requests")
            >>> ImageTools.take_screenshot(
            ...     "https://requests.readthedocs.io",
            ...     screenshot_name="docs-homepage"
            ... )
            '/path/to/assets/images/2025-12-05-package-requests/screenshot-docs-homepage.png'
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return "Error: playwright not installed. Install: pip install playwright && playwright install chromium"

        if not url.startswith(('http://', 'https://')):
            return f"Error: Invalid URL '{url}'"

        try:
            # Get blog-specific directory
            blog_dir = get_blog_assets_dir()

            # Determine filename
            if filename:
                safe_filename = filename if filename.endswith('.png') else f"{filename}.png"
            else:
                clean_name = re.sub(r'[^a-z0-9-]', '', screenshot_name.lower())
                safe_filename = get_professional_filename("screenshot", clean_name, "png")

            filepath = blog_dir / safe_filename

            # Take screenshot
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
                )

                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                )

                page = context.new_page()
                page.goto(url, timeout=30000, wait_until='networkidle')
                page.screenshot(path=str(filepath), full_page=False)

                browser.close()

            return str(filepath.absolute())

        except Exception as e:
            error_msg = str(e)
            if 'timeout' in error_msg.lower():
                return f"Error: Timeout loading {url}"
            elif 'refused' in error_msg.lower():
                return f"Error: Connection refused to {url}"
            else:
                return f"Error: {type(e).__name__}: {error_msg}"


# =============================================================================
# CrewAI-EXPOSED tools
# =============================================================================
@_crewai_tool_decorator("Search and Download Stock Photo")
def get_stock_photo_tool(query: str, filename: Optional[str] = None, asset_type: str = "stock") -> str:
    """Downloads stock photo to blog-specific directory."""
    return ImageTools.get_stock_photo(query=query, filename=filename, asset_type=asset_type)


@_crewai_tool_decorator("Generate Architecture Diagram")
def generate_architecture_diagram_tool(python_code: str, diagram_name: str = "architecture") -> str:
    """Generates architecture diagram in blog-specific directory."""
    return ImageTools.generate_architecture_diagram(python_code=python_code, diagram_name=diagram_name)


@_crewai_tool_decorator("Create Data Chart")
def create_chart_tool(
    x_values: list,
    y_values: list,
    title: str,
    x_label: str,
    y_label: str,
    filename: Optional[str] = None,
    chart_name: str = "chart",
    style: str = "standard",
) -> str:
    """Creates data chart in blog-specific directory."""
    return ImageTools.create_chart(
        x_values=x_values, y_values=y_values, title=title,
        x_label=x_label, y_label=y_label, filename=filename,
        chart_name=chart_name, style=style
    )


@_crewai_tool_decorator("Take Website Screenshot")
def take_screenshot_tool(url: str, filename: Optional[str] = None, screenshot_name: str = "screenshot") -> str:
    """Takes website screenshot in blog-specific directory."""
    return ImageTools.take_screenshot(url=url, filename=filename, screenshot_name=screenshot_name)


# Export for CrewAI
image_toolkit = [
    get_stock_photo_tool,
    generate_architecture_diagram_tool,
    create_chart_tool,
    take_screenshot_tool,
]


# =============================================================================
# CLI Testing
# =============================================================================
if __name__ == "__main__":
    print("Image Tools v3.3 - Organized Asset Management")
    print("=" * 70)

    # Load environment
    env_path = WORKSPACE / ".env"
    try:
        from dotenv import load_dotenv
        if env_path.exists():
            load_dotenv(env_path)
            print(f"\n✓ Loaded environment from {env_path}")
        else:
            print(f"\n⚠ .env file not found at {env_path}")
    except ImportError:
        print("\n⚠ python-dotenv not installed; skipping .env loading")

    # Test with blog context
    print("\n" + "=" * 70)
    print("Testing with blog context: package-scikit-learn")
    print("=" * 70)
    
    # Set context
    blog_dir = set_blog_context("package-scikit-learn", date="2025-12-05")
    print(f"\n✓ Blog assets directory: {blog_dir}")
    print(f"  Relative: {blog_dir.relative_to(WORKSPACE)}")

    # Test 1: Stock photo with professional naming
    print("\n1. Testing stock photo (professional naming)...")
    result = ImageTools.get_stock_photo(
        "technology abstract",
        asset_type="header"
    )
    print(f"   Result: {result}")
    if not result.startswith("Error"):
        rel_path = Path(result).relative_to(WORKSPACE)
        print(f"   ✓ Saved to: {rel_path}")

    # Test 2: Chart with descriptive name
    print("\n2. Testing chart creation...")
    result = ImageTools.create_chart(
        x_values=["Jan", "Feb", "Mar", "Apr"],
        y_values=[10, 25, 20, 35],
        title="Monthly Sales Growth",
        x_label="Month",
        y_label="Sales ($K)",
        chart_name="sales-growth"
    )
    print(f"   Result: {result}")
    if not result.startswith("Error"):
        rel_path = Path(result).relative_to(WORKSPACE)
        print(f"   ✓ Saved to: {rel_path}")

    # Test 3: List created files
    print("\n3. Files in blog directory:")
    if blog_dir.exists():
        files = list(blog_dir.glob("*"))
        if files:
            for f in files:
                print(f"   • {f.name} ({f.stat().st_size} bytes)")
        else:
            print("   (no files yet)")
    
    # Test 4: Different blog context
    print("\n" + "=" * 70)
    print("Testing with different blog: package-tensorflow")
    print("=" * 70)
    
    blog_dir2 = set_blog_context("package-tensorflow", date="2025-12-06")
    print(f"\n✓ Blog assets directory: {blog_dir2.relative_to(WORKSPACE)}")
    
    result = ImageTools.get_stock_photo(
        "deep learning",
        asset_type="header"
    )
    print(f"   Result: {result}")
    if not result.startswith("Error"):
        print(f"   ✓ Saved to: {Path(result).relative_to(WORKSPACE)}")

    # Summary
    print("\n" + "=" * 70)
    print("Directory structure:")
    print("=" * 70)
    for item in sorted(BASE_ASSETS_DIR.iterdir()):
        if item.is_dir():
            file_count = len(list(item.glob("*")))
            print(f"   📁 {item.name}/ ({file_count} files)")

    print("\n✓ Testing complete!")
    print(f"Base assets directory: {BASE_ASSETS_DIR}")
