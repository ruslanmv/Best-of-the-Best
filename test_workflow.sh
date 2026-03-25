#!/usr/bin/env bash
# ===========================================================================
# test_workflow.sh - Local simulation of .github/workflows/daily-best-of-the-best.yml
#
# Usage:
#   ./test_workflow.sh              # Run all checks (dry-run, no LLM needed)
#   ./test_workflow.sh --full       # Run full generation (requires Ollama or API key)
#   ./test_workflow.sh --help       # Show usage
#
# This script mirrors the GitHub Actions workflow steps locally:
#   1. Validates dependencies and environment
#   2. Tests topic selection and coverage tracking
#   3. Tests code validation logic
#   4. Tests blog index generation and data feeds
#   5. Runs post-creation quality checks
#   6. (--full mode) Runs the actual blog generation with CrewAI + LLM
# ===========================================================================
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0
FULL_MODE=false

# Parse arguments
for arg in "$@"; do
    case "$arg" in
        --full) FULL_MODE=true ;;
        --help|-h)
            echo "Usage: $0 [--full] [--help]"
            echo ""
            echo "  --full    Run full blog generation (requires Ollama or LLM API key)"
            echo "  --help    Show this help message"
            echo ""
            echo "Without --full, runs all validation checks in dry-run mode (no LLM needed)."
            exit 0
            ;;
    esac
done

log_pass() { echo -e "${GREEN}✅ PASS${NC}: $1"; PASS=$((PASS + 1)); }
log_fail() { echo -e "${RED}❌ FAIL${NC}: $1"; FAIL=$((FAIL + 1)); }
log_warn() { echo -e "${YELLOW}⚠️  WARN${NC}: $1"; WARN=$((WARN + 1)); }
log_info() { echo -e "${BLUE}ℹ️  INFO${NC}: $1"; }
log_step() { echo ""; echo -e "${BLUE}━━━ Step $1: $2 ━━━${NC}"; }

# Change to repo root
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "============================================================"
echo "  Best-of-the-Best Workflow Test"
echo "  Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  Mode: $([ "$FULL_MODE" = true ] && echo 'FULL (with LLM)' || echo 'DRY-RUN (no LLM needed)')"
echo "============================================================"

# =========================================================================
# Step 1: Check Python and dependencies
# =========================================================================
log_step 1 "Check Python environment and dependencies"

if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version)
    log_pass "Python found: $PY_VER"
else
    log_fail "Python3 not found"
    exit 1
fi

# Check critical Python packages
MISSING_DEPS=()
for pkg in crewai litellm yaml requests bs4 PIL pandas numpy sklearn jinja2; do
    if python3 -c "import $pkg" 2>/dev/null; then
        : # pass
    else
        MISSING_DEPS+=("$pkg")
    fi
done

if [ ${#MISSING_DEPS[@]} -eq 0 ]; then
    log_pass "All critical Python dependencies available"
else
    log_fail "Missing Python packages: ${MISSING_DEPS[*]}"
    echo "  Run: pip install -r scripts/requirements.txt"
fi

# =========================================================================
# Step 2: Check required directories and files
# =========================================================================
log_step 2 "Check required directories and data files"

for dir in blog/posts blog/api data assets/images; do
    if [ -d "$dir" ]; then
        log_pass "Directory exists: $dir"
    else
        log_warn "Directory missing: $dir (will be created)"
        mkdir -p "$dir"
    fi
done

for file in blog/api/packages.json blog/api/repositories.json README.md; do
    if [ -f "$file" ]; then
        log_pass "Data file exists: $file"
    else
        log_warn "Data file missing: $file"
    fi
done

# =========================================================================
# Step 3: Check LLM availability
# =========================================================================
log_step 3 "Check LLM provider availability"

LLM_AVAILABLE=false

# Check Ollama
if command -v ollama &>/dev/null; then
    if curl -fsS "http://127.0.0.1:11434/api/tags" &>/dev/null; then
        MODELS=$(curl -s "http://127.0.0.1:11434/api/tags" | python3 -c "import sys,json; models=json.load(sys.stdin).get('models',[]); print(', '.join(m['name'] for m in models))" 2>/dev/null || echo "?")
        log_pass "Ollama is running. Available models: $MODELS"
        LLM_AVAILABLE=true
    else
        log_warn "Ollama installed but not running. Start with: ollama serve"
    fi
else
    log_info "Ollama not installed (needed for local LLM)"
fi

# Check API keys
if [ -n "${OPENAI_API_KEY:-}" ]; then
    log_pass "OPENAI_API_KEY is set"
    LLM_AVAILABLE=true
elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    log_pass "ANTHROPIC_API_KEY is set"
    LLM_AVAILABLE=true
else
    log_info "No cloud API keys set (OPENAI_API_KEY, ANTHROPIC_API_KEY)"
fi

if [ "$LLM_AVAILABLE" = false ]; then
    log_warn "No LLM provider available. Full generation will not work."
    if [ "$FULL_MODE" = true ]; then
        log_fail "Cannot run --full mode without an LLM provider"
        echo "  Options:"
        echo "    1. Install and start Ollama: curl -fsSL https://ollama.com/install.sh | sh && ollama serve & ollama pull llama3:8b"
        echo "    2. Set OPENAI_API_KEY and NEWS_LLM_MODEL=openai/gpt-4o-mini"
        echo "    3. Run without --full for dry-run checks only"
        exit 1
    fi
fi

# =========================================================================
# Step 4: Test script syntax
# =========================================================================
log_step 4 "Validate Python script syntax"

for script in scripts/generate_daily_blog.py scripts/llm_client.py scripts/search.py blog/generate_index.py export_data_feeds.py; do
    if [ -f "$script" ]; then
        if python3 -c "import ast; ast.parse(open('$script').read())" 2>/dev/null; then
            log_pass "Syntax OK: $script"
        else
            log_fail "Syntax error in: $script"
        fi
    fi
done

# =========================================================================
# Step 5: Test topic selection and coverage tracking
# =========================================================================
log_step 5 "Test topic selection and coverage tracking"

TOPIC_OUTPUT=$(python3 -c "
import sys, os
os.environ.setdefault('NEWS_LLM_MODEL', 'ollama/llama3:8b')
sys.path.insert(0, 'scripts')
from generate_daily_blog import select_next_topic, load_coverage
coverage = load_coverage()
print(f'COVERAGE_COUNT={len(coverage)}')
topic = select_next_topic()
print(f'TOPIC_KIND={topic.kind}')
print(f'TOPIC_ID={topic.id}')
print(f'TOPIC_TITLE={topic.title}')
print(f'TOPIC_TAGS={topic.tags}')
print(f'TOPIC_SUMMARY={topic.summary[:80] if topic.summary else \"(none)\"}')
" 2>/dev/null) || TOPIC_OUTPUT=""

if [ -n "$TOPIC_OUTPUT" ]; then
    eval "$(echo "$TOPIC_OUTPUT" | grep '^COVERAGE_COUNT=')"
    eval "$(echo "$TOPIC_OUTPUT" | grep '^TOPIC_KIND=')"
    eval "$(echo "$TOPIC_OUTPUT" | grep '^TOPIC_ID=')"
    eval "$(echo "$TOPIC_OUTPUT" | grep '^TOPIC_TITLE=')"

    log_pass "Topic selected: $TOPIC_TITLE (kind=$TOPIC_KIND, id=$TOPIC_ID)"
    log_info "Coverage entries: ${COVERAGE_COUNT:-?}"

    # Check that tags are not generic
    if echo "$TOPIC_OUTPUT" | grep -q "TOPIC_TAGS=\['python', 'package', 'pypi'\]"; then
        log_fail "Topic has generic tags (fix needed in select_next_topic)"
    elif echo "$TOPIC_OUTPUT" | grep -q "TOPIC_TAGS=\['github', 'repository'\]"; then
        log_fail "Topic has generic repo tags (fix needed in select_next_topic)"
    else
        log_pass "Topic tags are specific (not generic placeholders)"
    fi

    # Check summary is not generic
    if echo "$TOPIC_OUTPUT" | grep -q 'TOPIC_SUMMARY=Python package:'; then
        log_fail "Topic summary is generic 'Python package: ...' (fix needed)"
    elif echo "$TOPIC_OUTPUT" | grep -q 'TOPIC_SUMMARY=GitHub repository'; then
        log_fail "Topic summary is generic 'GitHub repository' (fix needed)"
    else
        log_pass "Topic summary is descriptive (not a generic placeholder)"
    fi
else
    log_fail "Topic selection failed (could not import generate_daily_blog)"
fi

# =========================================================================
# Step 6: Test code validation functions
# =========================================================================
log_step 6 "Test code validation logic"

python3 -c "
import sys
sys.path.insert(0, 'scripts')
from generate_daily_blog import validate_python_code, validate_all_code_blocks

# Test 1: Valid code
valid, errors = validate_python_code('import os\nprint(os.getcwd())')
assert valid, f'Valid code reported as invalid: {errors}'
print('PASS: Valid code accepted')

# Test 2: Syntax error
valid, errors = validate_python_code('def foo(:\n  pass')
assert not valid, 'Syntax error not detected'
print('PASS: Syntax error detected')

# Test 3: Shell command in Python block
valid, errors = validate_python_code('pip install requests')
assert not valid, 'Shell command not detected'
print('PASS: Shell command in Python block detected')

# Test 4: Placeholder detection
valid, errors = validate_python_code('x = TODO')
assert not valid, 'Placeholder not detected'
print('PASS: Placeholder (TODO) detected')

# Test 5: Full article validation
article = '''## Test
\`\`\`python
import os
print(os.getcwd())
\`\`\`
'''
all_valid, issues, blocks = validate_all_code_blocks(article)
assert all_valid, f'Valid article failed: {issues}'
print('PASS: Full article validation works')

print('ALL_VALIDATION_TESTS_PASSED')
" 2>/dev/null && log_pass "All code validation tests passed" || log_fail "Code validation tests failed"

# =========================================================================
# Step 7: Test clean_content and clean_llm_output functions
# =========================================================================
log_step 7 "Test content cleaning functions"

python3 -c "
import sys
sys.path.insert(0, 'scripts')
from generate_daily_blog import clean_content, clean_llm_output

# Test: Remove 'Final Answer' artifact
text = 'Final Answer:\n\n## Introduction\nThis is the article.'
cleaned = clean_content(text)
assert 'Final Answer' not in cleaned, f'Final Answer not removed: {cleaned[:50]}'
print('PASS: Final Answer artifact removed')

# Test: Remove \"I now can give a great answer\"
text = 'I now can give a great answer\n\n## Introduction\nContent here.'
cleaned = clean_content(text)
assert 'I now can give' not in cleaned, f'AI artifact not removed: {cleaned[:50]}'
print('PASS: AI preamble artifact removed')

# Test: Remove \"Here is the complete corrected article\"
text = 'The complete corrected article with all fixes applied\n\n## Introduction\nContent.'
cleaned = clean_content(text)
assert 'complete corrected' not in cleaned, f'Corrected article preamble not removed: {cleaned[:60]}'
print('PASS: Corrected article preamble removed')

# Test: clean_llm_output unwraps markdown fence
text = '\`\`\`markdown\n## Introduction\nContent\n\`\`\`'
cleaned = clean_llm_output(text)
assert not cleaned.strip().startswith('\`\`\`'), f'Markdown fence not unwrapped: {cleaned[:30]}'
print('PASS: Markdown fence unwrapped')

print('ALL_CLEANING_TESTS_PASSED')
" 2>/dev/null && log_pass "All content cleaning tests passed" || log_fail "Content cleaning tests failed"

# =========================================================================
# Step 8: Test blog index generation
# =========================================================================
log_step 8 "Test blog index generation"

if python3 blog/generate_index.py 2>/dev/null; then
    log_pass "blog/generate_index.py ran successfully"
    if [ -f "blog/posts/index.json" ]; then
        INDEX_COUNT=$(python3 -c "import json; print(len(json.load(open('blog/posts/index.json'))))" 2>/dev/null || echo "0")
        log_pass "Index generated: $INDEX_COUNT entries in blog/posts/index.json"
    else
        log_warn "blog/posts/index.json not created"
    fi
else
    log_fail "blog/generate_index.py failed"
fi

# =========================================================================
# Step 9: Test data feeds export
# =========================================================================
log_step 9 "Test data feeds export"

if python3 export_data_feeds.py 2>/dev/null; then
    log_pass "export_data_feeds.py ran successfully"
    for feed_file in blog/api/data.json blog/api/feed.xml; do
        if [ -f "$feed_file" ]; then
            log_pass "Feed file exists: $feed_file"
        else
            log_warn "Feed file missing: $feed_file"
        fi
    done
else
    log_fail "export_data_feeds.py failed"
fi

# =========================================================================
# Step 10: Validate existing blog posts
# =========================================================================
log_step 10 "Validate existing blog posts"

POST_COUNT=0
ISSUES_COUNT=0

for post in blog/posts/*.md; do
    [ "$(basename "$post")" = "index.json" ] && continue
    [ ! -f "$post" ] && continue
    POST_COUNT=$((POST_COUNT + 1))

    # Check front matter
    if ! head -1 "$post" | grep -q "^---$"; then
        log_fail "Invalid front matter: $(basename "$post")"
        ISSUES_COUNT=$((ISSUES_COUNT + 1))
        continue
    fi

    # Check for AI artifacts (match only standalone lines, not in-context usage)
    if grep -qP '^\s*(\*\*)?Final Answer(\*\*)?\s*[:.]?\s*$' "$post" 2>/dev/null; then
        log_fail "AI artifact 'Final Answer' line in: $(basename "$post")"
        ISSUES_COUNT=$((ISSUES_COUNT + 1))
    fi

    if grep -qi "I now can give a great answer" "$post" 2>/dev/null; then
        log_fail "AI artifact 'I now can give...' in: $(basename "$post")"
        ISSUES_COUNT=$((ISSUES_COUNT + 1))
    fi

    if grep -qi "Code Issue Resolver" "$post" 2>/dev/null; then
        log_fail "Leaked system prompt in: $(basename "$post")"
        ISSUES_COUNT=$((ISSUES_COUNT + 1))
    fi

    # Check for placeholders
    if grep -qP '\[insert|TODO|your_\w+|\[Topic\]' "$post" 2>/dev/null; then
        log_fail "Placeholder text in: $(basename "$post")"
        ISSUES_COUNT=$((ISSUES_COUNT + 1))
    fi

    # Check word count
    WORDS=$(grep -v "^---" "$post" | wc -w | xargs)
    if [ "$WORDS" -lt 200 ]; then
        log_warn "Short post ($WORDS words): $(basename "$post")"
    fi
done

if [ "$ISSUES_COUNT" -eq 0 ]; then
    log_pass "All $POST_COUNT blog posts passed quality checks"
else
    log_fail "$ISSUES_COUNT issues found across $POST_COUNT posts"
fi

# =========================================================================
# Step 11: Duplicate topic check
# =========================================================================
log_step 11 "Check for duplicate topics in recent posts"

DUPES_FOUND=0
RECENT_TOPICS=()

for post in $(ls -t blog/posts/*.md 2>/dev/null | grep -v index | head -10); do
    TOPIC_ID=$(grep "^topic_id:" "$post" | head -1 | sed 's/topic_id: *"\?\([^"]*\)"\?/\1/')
    if [ -n "$TOPIC_ID" ]; then
        for existing in "${RECENT_TOPICS[@]:-}"; do
            if [ "$existing" = "$TOPIC_ID" ]; then
                log_fail "Duplicate topic: $TOPIC_ID ($(basename "$post"))"
                DUPES_FOUND=$((DUPES_FOUND + 1))
            fi
        done
        RECENT_TOPICS+=("$TOPIC_ID")
    fi
done

if [ "$DUPES_FOUND" -eq 0 ]; then
    log_pass "No duplicate topics in recent posts"
fi

# =========================================================================
# Step 12: Full generation (only with --full)
# =========================================================================
if [ "$FULL_MODE" = true ]; then
    log_step 12 "Full blog generation (with LLM)"

    # Ensure directories exist
    mkdir -p blog/api blog/posts data assets/images logs

    # Set default env vars if not already set
    export NEWS_LLM_MODEL="${NEWS_LLM_MODEL:-ollama/llama3:8b}"
    export LITELLM_REQUEST_TIMEOUT="${LITELLM_REQUEST_TIMEOUT:-300}"
    export LITELLM_NUM_RETRIES="${LITELLM_NUM_RETRIES:-2}"

    log_info "LLM Model: $NEWS_LLM_MODEL"
    log_info "Timeout: ${LITELLM_REQUEST_TIMEOUT}s"

    echo ""
    echo "Running: python3 scripts/generate_daily_blog.py"
    echo "This may take 10-30 minutes depending on your LLM..."
    echo ""

    if python3 scripts/generate_daily_blog.py 2>&1 | tee logs/test_generation.log; then
        log_pass "Blog generation completed"

        # Find the newest post
        LATEST_POST=$(ls -t blog/posts/*.md 2>/dev/null | grep -v index | head -1)

        if [ -n "$LATEST_POST" ]; then
            log_pass "New post created: $(basename "$LATEST_POST")"

            # Word count check
            WORD_COUNT=$(grep -v "^---" "$LATEST_POST" | wc -w | xargs)
            echo "  Words: $WORD_COUNT"

            if [ "$WORD_COUNT" -lt 100 ]; then
                log_fail "Post too short: $WORD_COUNT words"
            elif [ "$WORD_COUNT" -lt 800 ]; then
                log_warn "Post seems short: $WORD_COUNT words (< 800)"
            else
                log_pass "Post length OK: $WORD_COUNT words"
            fi

            # Code block check
            CODE_BLOCKS=$(grep -c '```python' "$LATEST_POST" || echo "0")
            echo "  Code blocks: $CODE_BLOCKS"

            if [ "$CODE_BLOCKS" -eq 0 ]; then
                log_warn "No Python code blocks found"
            else
                log_pass "$CODE_BLOCKS Python code block(s) found"
            fi

            # AI artifact check
            if grep -qi "Final Answer\|I now can give\|Code Issue Resolver\|Thought:" "$LATEST_POST"; then
                log_fail "AI artifacts found in generated post"
            else
                log_pass "No AI artifacts in generated post"
            fi

            # Show first 20 lines
            echo ""
            echo "  --- First 20 lines of generated post ---"
            head -20 "$LATEST_POST" | sed 's/^/  /'
            echo "  --- (end preview) ---"
        else
            log_fail "No blog post file was created"
        fi

        # Rebuild index
        python3 blog/generate_index.py 2>/dev/null && log_pass "Blog index rebuilt" || log_warn "Blog index rebuild failed"
        python3 export_data_feeds.py 2>/dev/null && log_pass "Data feeds rebuilt" || log_warn "Data feeds rebuild failed"
    else
        log_fail "Blog generation failed (see logs/test_generation.log)"
    fi
else
    log_step 12 "Full generation (SKIPPED - use --full to enable)"
    log_info "Skipping actual blog generation (no --full flag)"
fi

# =========================================================================
# Summary
# =========================================================================
echo ""
echo "============================================================"
echo "  Test Results Summary"
echo "============================================================"
echo -e "  ${GREEN}Passed${NC}: $PASS"
echo -e "  ${RED}Failed${NC}: $FAIL"
echo -e "  ${YELLOW}Warnings${NC}: $WARN"
echo "============================================================"

if [ "$FAIL" -gt 0 ]; then
    echo -e "${RED}Some tests failed. Review the output above.${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
