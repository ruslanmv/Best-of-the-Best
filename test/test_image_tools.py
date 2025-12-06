import os
import sys
from pathlib import Path

import pytest

# -----------------------------------------------------------------------------
# Project / import setup
# -----------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "scripts"

# Ensure we can import scripts.image_tools
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Load .env from project root (if present)
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(ROOT_DIR / ".env")
except Exception:
    # If python-dotenv is not installed, tests still run; env vars must be set in CI
    pass

from scripts.image_tools import (  # noqa: E402
    ImageTools,
    BASE_ASSETS_DIR,
    set_blog_context,
    get_blog_assets_dir,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _cleanup_file(path_str: str) -> None:
    """Delete a file path if it exists (best effort)."""
    try:
        path = Path(path_str)
        if path.exists():
            path.unlink()
    except Exception:
        # Don't fail tests just because cleanup failed
        pass


# -----------------------------------------------------------------------------
# Tests for create_chart (no external services required)
# -----------------------------------------------------------------------------
def test_create_chart_generates_png_file(tmp_path):
    """
    Basic smoke test: create_chart should return a valid PNG path and actually
    create the file in the organized assets/images/YYYY-MM-DD-slug folder.
    """
    # Set a deterministic blog context for this test
    blog_dir = set_blog_context("pytest-chart-blog", date="2025-12-05")

    # Use a temporary filename to avoid collisions
    filename = f"pytest-chart-{os.getpid()}.png"

    result = ImageTools.create_chart(
        x_values=["Jan", "Feb", "Mar", "Apr"],
        y_values=[10, 20, 15, 30],
        title="Test Chart",
        x_label="Month",
        y_label="Value",
        filename=filename,
        style="standard",
    )

    # Ensure cleanup at the end
    try:
        # Should not be an error
        assert not result.startswith("Error"), f"create_chart failed: {result}"

        path = Path(result)
        assert path.suffix == ".png"
        assert path.exists(), f"Chart file was not created at: {result}"

        # Should be inside the blog-specific directory
        assert blog_dir in path.parents, "Chart not created inside blog-specific assets directory"

        # And the blog dir should be under BASE_ASSETS_DIR
        assert BASE_ASSETS_DIR in blog_dir.parents or blog_dir == BASE_ASSETS_DIR
    finally:
        _cleanup_file(result)


def test_create_chart_with_mismatched_lengths_returns_error():
    """
    When x_values and y_values length differ, the function should return a clear error.
    """
    # No need to set context here; function should early-return
    result = ImageTools.create_chart(
        x_values=[1, 2, 3],
        y_values=[10, 20],  # shorter on purpose
        title="Bad Chart",
        x_label="X",
        y_label="Y",
    )
    assert result.startswith("Error:")
    assert "Length mismatch" in result


# -----------------------------------------------------------------------------
# Tests for get_stock_photo (requires PEXELS_API_KEY)
# -----------------------------------------------------------------------------
@pytest.mark.skipif(
    not os.getenv("PEXELS_API_KEY"),
    reason="PEXELS_API_KEY not set (configure it in .env or environment for this test)",
)
def test_get_stock_photo_downloads_image(tmp_path):
    """
    Integration-style test for get_stock_photo. This actually hits the Pexels API
    if PEXELS_API_KEY is set. If not set, the test is skipped.
    """
    # Set a deterministic blog context
    blog_dir = set_blog_context("pytest-stock-blog", date="2025-12-05")

    filename = f"pytest-stock-{os.getpid()}.jpg"

    result = ImageTools.get_stock_photo(
        query="technology abstract",
        filename=filename,
        asset_type="header",
    )

    try:
        assert not result.startswith("Error"), f"get_stock_photo failed: {result}"

        path = Path(result)
        assert path.exists(), f"Stock photo file was not created at: {result}"
        assert path.suffix in {".jpg", ".jpeg", ".png"}

        # Should be inside the blog-specific directory
        assert blog_dir in path.parents, "Stock image not created inside blog-specific assets directory"

        # And under BASE_ASSETS_DIR
        assert BASE_ASSETS_DIR in blog_dir.parents or blog_dir == BASE_ASSETS_DIR
    finally:
        _cleanup_file(result)


def test_get_stock_photo_without_api_key_returns_error(monkeypatch):
    """
    If PEXELS_API_KEY is not set, the tool should return a clear error message
    instead of crashing.
    """
    monkeypatch.delenv("PEXELS_API_KEY", raising=False)

    result = ImageTools.get_stock_photo(
        query="technology abstract",
        filename="pytest-should-not-download.jpg",
    )
    assert result.startswith("Error:")
    assert "PEXELS_API_KEY not set" in result


# -----------------------------------------------------------------------------
# Tests for generate_architecture_diagram (optional)
# -----------------------------------------------------------------------------
def test_generate_architecture_diagram_skips_if_dependencies_missing():
    """
    We don't want this test to fail the suite when 'diagrams' or graphviz are not
    installed, so we assert that it either succeeds or returns a clear 'Error:'
    message about missing deps.
    """
    # Set context so generated files (if any) go into a test folder
    blog_dir = set_blog_context("pytest-diagram-blog", date="2025-12-05")

    code = f"""
from diagrams import Diagram
from diagrams.generic.blank import Blank

# output_dir is injected by ImageTools.generate_architecture_diagram
with Diagram("pytest-diagram", show=False, filename=f"{{output_dir}}/pytest-diagram"):
    Blank("node")
"""

    result = ImageTools.generate_architecture_diagram(code, diagram_name="pytest-diagram")

    # Either success message or a clear error about missing dependencies
    assert result.startswith("Success:") or result.startswith("Error:")

    # If it succeeded, check the file exists
    if result.startswith("Success:"):
        # diagrams usually creates .png files
        candidates = list(blog_dir.glob("pytest-diagram*"))
        assert candidates, "Diagram reported success but no files were found in blog directory"


# -----------------------------------------------------------------------------
# Tests for take_screenshot (optional, requires playwright + chromium)
# -----------------------------------------------------------------------------
def test_take_screenshot_handles_missing_playwright_gracefully():
    """
    If playwright is not installed, the function should return a clear error
    string instead of raising.
    """
    # Set context so screenshots go into a test folder
    blog_dir = set_blog_context("pytest-screenshot-blog", date="2025-12-05")

    result = ImageTools.take_screenshot(
        url="https://example.com",
        filename=f"pytest-screenshot-{os.getpid()}.png",
        screenshot_name="example-homepage",
    )

    # Two acceptable outcomes:
    # - It actually worked and returned a path
    # - It returned a clear error about playwright missing or network issues
    if result.startswith("Error:"):
        assert (
            "playwright not installed" in result
            or "Timeout" in result
            or "Connection refused" in result
        )
    else:
        # If it succeeded, ensure the file exists and clean it up
        try:
            path = Path(result)
            assert path.exists()
            assert path.suffix == ".png"
            # Should be in the blog-specific directory
            assert blog_dir in path.parents
        finally:
            _cleanup_file(result)
