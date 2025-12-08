#!/usr/bin/env python3
"""
test/test_finder.py - Tests for scripts/finder.py

Goals:
- Verify deep_find_documentation_impl integrates correctly with DeepFinder.
- Ensure success/partial/failure paths behave as expected.
- Ensure we never hit the network (all search/scrape calls are stubbed).
"""

import sys
import unittest
from pathlib import Path

# -----------------------------------------------------------------------------
# Make repo root importable and load scripts.finder
# -----------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from scripts import finder  # type: ignore
except ImportError:
    import finder  # type: ignore


class TestDeepFinder(unittest.TestCase):
    def setUp(self):
        # Save originals for restoration
        self.orig_search_web_impl = finder.search_web_impl
        self.orig_scrape_webpage_impl = finder.scrape_webpage_impl
        self.orig_min_code_blocks_target = finder.MIN_CODE_BLOCKS_TARGET
        self.orig_scrape_single_page = getattr(
            finder.DeepFinder, "_scrape_single_page", None
        )

        # Reduce noise in test output
        import logging
        logging.basicConfig(level=logging.WARNING)

    def tearDown(self):
        # Restore originals
        finder.search_web_impl = self.orig_search_web_impl
        finder.scrape_webpage_impl = self.orig_scrape_webpage_impl
        finder.MIN_CODE_BLOCKS_TARGET = self.orig_min_code_blocks_target
        if self.orig_scrape_single_page is not None:
            finder.DeepFinder._scrape_single_page = self.orig_scrape_single_page

    # ------------------------------------------------------------------ #
    # Helpers for stubbing search & scrape
    # ------------------------------------------------------------------ #
    @staticmethod
    def _fake_search_results_text(urls_with_titles):
        """
        Build a minimal fake search_web_impl result string that
        finder._get_search_results() can parse.

        Example line:
        **URL:** https://example.com/page
        """
        lines = [
            "# 🔍 Search Results: test",
            "",
            f"Found {len(urls_with_titles)} results:",
            "======================================================================",
            "",
        ]
        for i, (title, url) in enumerate(urls_with_titles, 1):
            lines.append(f"## Result {i}")
            lines.append(f"**Title:** {title}")
            lines.append(f"**URL:** {url}")
            lines.append(f"**Summary:** Fake summary")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Test: Success path with enough code blocks
    # ------------------------------------------------------------------ #
    def test_deep_find_success_with_multiple_code_blocks(self):
        """
        deep_find_documentation_impl should report SUCCESS when enough code
        blocks are found.
        """

        # Make target small so we don't need tons of fake blocks
        finder.MIN_CODE_BLOCKS_TARGET = 2

        # Stub search_web_impl to return a single valid URL on an allowed domain
        urls = [("XGBoost Tutorial", "https://readthedocs.org/projects/xgboost-tutorial/")]
        fake_search_text = self._fake_search_results_text(urls)

        def fake_search_web_impl(query: str) -> str:
            # Ignore query, always return same fake result
            return fake_search_text

        finder.search_web_impl = fake_search_web_impl

        # Stub scrape_webpage_impl to return content with multiple fenced code blocks
        def fake_scrape_webpage_impl(url: str) -> str:
            return """
            # XGBoost Tutorial

            Some introduction text.

            ```python
            import xgboost as xgb

            model = xgb.XGBClassifier()
            model.fit(X_train, y_train)
            ```

            Further docs.

            ```bash
            pip install xgboost
            ```

            And maybe another example:

            ```python
            preds = model.predict(X_test)
            print(preds[:5])
            ```
            """

        finder.scrape_webpage_impl = fake_scrape_webpage_impl

        # Run tool
        report = finder.deep_find_documentation_impl("xgboost python tutorial")

        # Assertions: should be a SUCCESS report with code examples
        self.assertIn("SUCCESS - Found", report)
        self.assertIn("Python Examples:", report)
        self.assertIn("Installation", report)  # header text may be slightly different
        self.assertIn("```python", report)
        self.assertIn("```bash", report)
        # Ensure it does NOT claim NO_CODE_EXAMPLES_FOUND
        self.assertNotIn("NO_CODE_EXAMPLES_FOUND", report)

    # ------------------------------------------------------------------ #
    # Test: Partial path when some code but below target
    # ------------------------------------------------------------------ #
    def test_deep_find_partial_when_below_target(self):
        """
        deep_find_documentation_impl should report PARTIAL when >0 code blocks
        but below MIN_CODE_BLOCKS_TARGET.
        """

        # Require more code than we will provide
        finder.MIN_CODE_BLOCKS_TARGET = 5

        # Stub search_web_impl to return one page
        urls = [("Example Tutorial", "https://readthedocs.org/projects/example/")]
        fake_search_text = self._fake_search_results_text(urls)

        def fake_search_web_impl(query: str) -> str:
            return fake_search_text

        finder.search_web_impl = fake_search_web_impl

        # IMPORTANT: Instead of relying on scrape_webpage_impl + CodeDetector,
        # we monkeypatch DeepFinder._scrape_single_page so that it *directly*
        # injects a small number of code blocks (< MIN_CODE_BLOCKS_TARGET).
        def fake_scrape_single_page(self, result_info):
            # Simulate scraping exactly 2 code blocks from this page
            self.total_pages_scraped += 1
            code_block_1 = {
                "language": "python",
                "code": "print('hello world')",
                "lines": 1,
                "source": "test_partial",
                "source_url": result_info["url"],
                "source_title": result_info.get("title", "Example Tutorial"),
            }
            code_block_2 = {
                "language": "bash",
                "code": "pip install example",
                "lines": 1,
                "source": "test_partial",
                "source_url": result_info["url"],
                "source_title": result_info.get("title", "Example Tutorial"),
            }
            self.all_code_blocks.append(code_block_1)
            self.all_code_blocks.append(code_block_2)

            self.all_sources.append(
                {
                    "url": result_info["url"],
                    "title": result_info.get("title", "Example Tutorial"),
                    "code_blocks": 2,
                }
            )
            # Indicate successful scrape
            return True

        finder.DeepFinder._scrape_single_page = fake_scrape_single_page

        # Run tool
        report = finder.deep_find_documentation_impl("example tutorial")

        # Now we expect the PARTIAL path because we created 2 blocks and the
        # target is 5.
        self.assertIn("Partial Results", report)
        self.assertIn("Found 2 code examples", report)
        self.assertIn("PROCEED with caution", report)
        self.assertIn("```python", report)
        self.assertIn("```bash", report)

    # ------------------------------------------------------------------ #
    # Test: Failure path when no code at all
    # ------------------------------------------------------------------ #
    def test_deep_find_failure_when_no_code_found(self):
        """
        deep_find_documentation_impl should report FAILED when no code blocks
        can be extracted from any page.
        """

        urls = [("No Code Here", "https://readthedocs.org/projects/no-code/")]
        fake_search_text = self._fake_search_results_text(urls)

        def fake_search_web_impl(query: str) -> str:
            return fake_search_text

        finder.search_web_impl = fake_search_web_impl

        # Scraper returns text with no fenced code at all
        def fake_scrape_webpage_impl(url: str) -> str:
            return """
            # No Code Documentation

            This documentation only contains prose and no code examples.

            It explains concepts but has no ``` fenced blocks.
            """

        finder.scrape_webpage_impl = fake_scrape_webpage_impl

        report = finder.deep_find_documentation_impl("no code tutorial")

        self.assertIn("Deep Search Failed", report)
        self.assertIn("NO_CODE_EXAMPLES_FOUND", report)
        self.assertIn("ABORT", report)

    # ------------------------------------------------------------------ #
    # Test: Input validation for empty topic
    # ------------------------------------------------------------------ #
    def test_deep_find_empty_topic(self):
        """
        deep_find_documentation_impl should return a clear error for empty topic.
        """
        report1 = finder.deep_find_documentation_impl("")
        report2 = finder.deep_find_documentation_impl("   ")

        self.assertIn("Error: Empty topic provided", report1)
        self.assertIn("Error: Empty topic provided", report2)


if __name__ == "__main__":
    # Allow running with: python test/test_finder.py
    unittest.main()
