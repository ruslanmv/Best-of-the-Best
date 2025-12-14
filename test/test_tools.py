#!/usr/bin/env python3
"""
test/test_tools.py

Smoke & health checks for the core "Phase 1" tools used in the
Best-of-the-Best research workflow.
"""

import sys
import time
from pathlib import Path
from typing import Callable

# =============================================================================
# PATH SETUP
# =============================================================================

CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Try to import search & finder
try:
    from scripts import search  # type: ignore
except ImportError:
    import search  # type: ignore

try:
    from scripts import finder  # type: ignore
except ImportError:
    import finder  # type: ignore


# =============================================================================
# SIMPLE TEST RESULT AGGREGATOR
# =============================================================================

class TestResults:
    def __init__(self) -> None:
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.failures = []

    def record(
        self,
        name: str,
        ok: bool,
        message: str = "",
        skipped: bool = False,
    ) -> None:
        self.total += 1
        icon = "🟢" if ok and not skipped else "🔴" if not skipped else "⚪"
        status = "PASS" if ok and not skipped else "FAIL" if not skipped else "SKIP"
        print(f"{icon} {status:4} | {name:45} | {message}")

        if skipped:
            self.skipped += 1
            return

        if ok:
            self.passed += 1
        else:
            self.failed += 1
            self.failures.append(f"{name}: {message}")

    def summary(self) -> bool:
        print("\n" + "=" * 80)
        print("📊 TOOL HEALTH SUMMARY")
        print("=" * 80)
        print(f"Total Tests:  {self.total}")
        print(f"✅ Passed:    {self.passed}")
        print(f"🔴 Failed:    {self.failed}")
        print(f"⚪ Skipped:   {self.skipped}")

        effective_total = max(1, self.total - self.skipped)
        success_rate = self.passed / effective_total * 100.0
        print(f"Success Rate: {success_rate:.1f}%")

        if self.failures:
            print("\n❌ FAILED TESTS:")
            for f in self.failures:
                print(f"   - {f}")

        print("=" * 80)
        return self.failed == 0


results = TestResults()
CI_MODE = "--ci" in sys.argv


def separator(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


# =============================================================================
# HELPER: CALL CREWAI TOOL OR PLAIN FUNCTION
# =============================================================================

def _call_tool(tool_obj, *args, **kwargs):
    """
    Call either:
      - a plain function, or
      - a CrewAI Tool-like object with .run() / .invoke().
    """
    # If it's already directly callable (plain function or a callable wrapper)
    if callable(tool_obj):
        return tool_obj(*args, **kwargs)

    # CrewAI tools are usually not callable but have .run() or .invoke()
    for attr in ("run", "invoke"):
        if hasattr(tool_obj, attr):
            method = getattr(tool_obj, attr)
            if callable(method):
                return method(*args, **kwargs)

    raise TypeError("Tool object is not callable and has no run/invoke method")


# =============================================================================
# NON-NETWORK / PURE UNIT TESTS
# =============================================================================

def test_tool_presence_and_docs() -> None:
    separator("UNIT TESTS: Tool Presence & Documentation")

    required_funcs = {
        "scrape_readme": getattr(search, "scrape_readme", None),
        "get_package_health": getattr(search, "get_package_health", None),
        "search_web": getattr(search, "search_web", None),
        "scrape_webpage": getattr(search, "scrape_webpage", None),
        "deep_find_documentation_impl": getattr(
            finder, "deep_find_documentation_impl", None
        ),
    }

    for name, func in required_funcs.items():
        if func is None:
            results.record(
                f"Presence: {name}",
                False,
                "Function/Tool missing",
            )
            continue

        results.record(
            f"Presence: {name}",
            True,
            "Found Tool or function",
        )

        # For Tool objects, description is usually on .description
        doc = getattr(func, "__doc__", "") or getattr(func, "description", "") or ""
        results.record(
            f"Docs: {name}",
            len(doc.strip()) >= 40,
            f"Doc length={len(doc.strip())}",
        )


def test_code_detector_basic() -> None:
    separator("UNIT TESTS: CodeDetector Basics")

    markdown = """
    # Demo

    ```python
    import xgboost as xgb

    def train():
        return xgb
    ```
    """
    blocks = search.CodeDetector.extract_from_markdown(markdown)
    ok = (
        len(blocks) == 1
        and blocks[0]["language"] == "python"
        and "import xgboost" in blocks[0]["code"]
        and "def train():" in blocks[0]["code"]
    )
    msg = f"Found {len(blocks)} blocks" if blocks else "No blocks found"
    results.record("CodeDetector: Basic Python Block", ok, msg)


def test_stub_detection_basic() -> None:
    text_stub = "See documentation at https://example.com"
    text_real = """
    # Usage

    ```python
    import foo
    foo.run()
    ```
    """

    is_stub = search.is_stub_readme(text_stub)
    is_real_stub = search.is_stub_readme(text_real)

    results.record(
        "Stub Detection: Short Redirect",
        is_stub is True,
        "Correctly detected stub README",
    )
    results.record(
        "Stub Detection: README With Code",
        is_real_stub is False,
        "Did not flag README with code as stub",
    )


def test_deep_finder_empty_topic() -> None:
    report1 = finder.deep_find_documentation_impl("")
    report2 = finder.deep_find_documentation_impl("   ")

    ok1 = "Error: Empty topic provided" in report1
    ok2 = "Error: Empty topic provided" in report2

    results.record(
        "DeepFinder: Empty Topic (blank)",
        ok1,
        "Returned clear error for empty string",
    )
    results.record(
        "DeepFinder: Empty Topic (whitespace)",
        ok2,
        "Returned clear error for whitespace-only",
    )


# =============================================================================
# NETWORK / INTEGRATION SMOKE TESTS
# =============================================================================

def network_test(name: str):
    def wrapper(fn: Callable[[], None]) -> Callable[[], None]:
        def inner() -> None:
            if CI_MODE:
                results.record(
                    name,
                    True,
                    "Skipped in CI mode (--ci)",
                    skipped=True,
                )
                return
            try:
                fn()
            except Exception as e:
                results.record(name, False, f"Exception: {str(e)[:80]}")
        return inner
    return wrapper


@network_test("Tool Smoke: scrape_readme(xgboost)")
def test_scrape_readme_tool() -> None:
    tool_obj = search.scrape_readme
    # Use underlying impl directly if you prefer:
    # tool_obj = search.scrape_readme_impl
    result = _call_tool(tool_obj, "xgboost")
    text = str(result)

    ok = "README for:" in text or "XGBoost" in text or "xgboost" in text.lower()
    results.record(
        "Tool Smoke: scrape_readme(xgboost)",
        ok,
        f"Length={len(text)}",
    )


@network_test("Tool Smoke: get_package_health(xgboost)")
def test_get_package_health_tool() -> None:
    tool_obj = search.get_package_health
    # or: tool_obj = search.get_package_health_impl
    result = _call_tool(tool_obj, "xgboost")
    text = str(result)

    has_version = "Latest Version" in text or "version" in text.lower()
    has_blocks = "Total Blocks Found:" in text or "Total Blocks" in text

    ok = has_version and len(text) > 200
    results.record(
        "Tool Smoke: get_package_health(xgboost)",
        ok,
        f"Has version={has_version}, has blocks={has_blocks}",
    )


@network_test("Tool Smoke: search_web('xgboost python documentation')")
def test_search_web_tool() -> None:
    tool_obj = search.search_web
    result = _call_tool(tool_obj, "xgboost python documentation")
    text = str(result)

    has_result = "## Result" in text or "Result 1" in text
    has_url = "http" in text.lower() or "**URL:**" in text

    ok = len(text) > 100 and (has_result or has_url)
    results.record(
        "Tool Smoke: search_web(xgboost docs)",
        ok,
        f"Length={len(text)}, has_result={has_result}, has_url={has_url}",
    )


@network_test("Tool Smoke: scrape_webpage(xgboost docs homepage)")
def test_scrape_webpage_tool() -> None:
    tool_obj = search.scrape_webpage
    url = "https://xgboost.readthedocs.io/en/latest/"
    result = _call_tool(tool_obj, url)
    text = str(result)

    ok = len(text) > 200 and ("xgboost" in text.lower())
    results.record(
        "Tool Smoke: scrape_webpage(latest docs)",
        ok,
        f"Length={len(text)}",
    )


@network_test("Tool Smoke: deep_find_documentation_impl('xgboost tutorial')")
def test_deep_find_documentation_tool() -> None:
    text = finder.deep_find_documentation_impl("xgboost python tutorial")

    ok = len(text) > 200 and (
        "SUCCESS" in text
        or "Partial Results" in text
        or "Deep Search Failed" in text
    )
    results.record(
        "Tool Smoke: deep_find_documentation_impl",
        ok,
        f"Length={len(text)}",
    )


# =============================================================================
# MAIN RUNNER
# =============================================================================

def run_all() -> int:
    print("\n" + "=" * 80)
    print("🚀 PHASE-1 TOOL HEALTH CHECK")
    print("=" * 80)
    print(f"Project Root: {ROOT_DIR}")
    print(f"Mode: {'CI (network tests skipped)' if CI_MODE else 'Full'}")
    print("=" * 80)

    # Non-network tests
    test_tool_presence_and_docs()
    test_code_detector_basic()
    test_stub_detection_basic()
    test_deep_finder_empty_topic()

    # Network / integration smoke tests
    test_scrape_readme_tool()
    time.sleep(0.5)
    test_get_package_health_tool()
    time.sleep(0.5)
    test_search_web_tool()
    time.sleep(0.5)
    test_scrape_webpage_tool()
    time.sleep(0.5)
    test_deep_find_documentation_tool()

    ok = results.summary()
    if ok:
        print("\n✅ TOOL LAYER LOOKS HEALTHY – SAFE TO RUN PHASE 1 PIPELINE")
        return 0
    else:
        print("\n❌ TOOL PROBLEMS DETECTED – FIX BEFORE RUNNING PIPELINE")
        return 1


if __name__ == "__main__":
    sys.exit(run_all())
