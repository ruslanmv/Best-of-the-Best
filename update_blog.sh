#!/usr/bin/env bash
# update_blog.sh
# Production-ready blog generation script with comprehensive diagnostics
#
# FEATURES:
# - Automatic Ollama setup and management
# - Pre-flight checks and validation
# - Progress tracking with timestamps
# - Error recovery and logging
# - Post-generation verification

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
OLLAMA_MODEL="${NEWS_LLM_MODEL:-ollama/llama3:8b}"
PYTHON="${PYTHON:-python3}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# ✅ FIXED: Script is at project root, don't go up a level!
PROJECT_ROOT="${SCRIPT_DIR}"

# Logging
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/update_blog_$(date +%Y%m%d_%H%M%S).log"

# Redirect all output to log file as well
exec > >(tee -a "${LOG_FILE}")
exec 2>&1

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   🏆 Best-of-the-Best Blog Generator v2.0${NC}"
echo -e "${BLUE}   Production Mode with Diagnostics${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}📋 Configuration:${NC}"
echo "   Project Root: ${PROJECT_ROOT}"
echo "   Ollama Host:  ${OLLAMA_HOST}"
echo "   Model:        ${OLLAMA_MODEL}"
echo "   Python:       ${PYTHON}"
echo "   Log File:     ${LOG_FILE}"
echo ""

# -------------------------------------------------------------------
# STEP 0: Pre-flight checks
# -------------------------------------------------------------------
echo -e "${YELLOW}🔍 Step 0: Pre-flight checks...${NC}"

# Check if in correct directory
if [ ! -f "${PROJECT_ROOT}/blog/README.md" ] && [ ! -d "${PROJECT_ROOT}/blog/api" ]; then
    echo -e "${RED}❌ Error: Not in project root or missing blog structure${NC}"
    echo "   Expected: ${PROJECT_ROOT}/blog/"
    echo "   Current:  $(pwd)"
    exit 1
fi

# Check required directories
for dir in "blog/api" "blog/posts" "data" "scripts"; do
    if [ ! -d "${PROJECT_ROOT}/${dir}" ]; then
        echo -e "${YELLOW}⚠️  Creating missing directory: ${dir}${NC}"
        mkdir -p "${PROJECT_ROOT}/${dir}"
    fi
done

# Verify API data exists
if [ ! -f "${PROJECT_ROOT}/blog/api/packages.json" ] && \
   [ ! -f "${PROJECT_ROOT}/blog/api/repositories.json" ]; then
    echo -e "${RED}❌ No API data found in blog/api/${NC}"
    echo "   Required: packages.json or repositories.json"
    echo "   Run data export first: make export"
    exit 1
fi

echo -e "${GREEN}✅ Pre-flight checks passed${NC}"
echo ""

# -------------------------------------------------------------------
# STEP 1: Check Ollama installation
# -------------------------------------------------------------------
echo -e "${YELLOW}📦 Step 1: Checking Ollama installation...${NC}"

if ! command -v ollama &> /dev/null; then
    echo -e "${RED}❌ Ollama is not installed${NC}"
    echo ""
    echo "Install Ollama:"
    echo "  • macOS/Linux: curl -fsSL https://ollama.com/install.sh | sh"
    echo "  • Or visit: https://ollama.com/download"
    echo ""
    exit 1
fi

OLLAMA_VERSION=$(ollama --version 2>/dev/null || echo "unknown")
echo -e "${GREEN}✅ Ollama installed: ${OLLAMA_VERSION}${NC}"
echo ""

# -------------------------------------------------------------------
# STEP 2: Check/Start Ollama server
# -------------------------------------------------------------------
echo -e "${YELLOW}🔌 Step 2: Checking Ollama server...${NC}"

OLLAMA_PID=""
if curl -fsSL "${OLLAMA_HOST}/api/tags" &> /dev/null; then
    echo -e "${GREEN}✅ Ollama server already running at ${OLLAMA_HOST}${NC}"
else
    echo -e "${YELLOW}⚠️  Starting Ollama server...${NC}"
    
    # Start Ollama in background
    ollama serve > "${LOG_DIR}/ollama_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
    OLLAMA_PID=$!
    
    echo "   PID: ${OLLAMA_PID}"
    echo "   Waiting for startup..."
    
    # Wait up to 60 seconds
    for i in {1..60}; do
        if curl -fsSL "${OLLAMA_HOST}/api/tags" &> /dev/null; then
            echo -e "${GREEN}✅ Ollama server started successfully${NC}"
            break
        fi
        
        if [ $i -eq 60 ]; then
            echo -e "${RED}❌ Ollama server failed to start${NC}"
            echo "   Check log: ${LOG_DIR}/ollama_*.log"
            exit 1
        fi
        
        echo -n "."
        sleep 1
    done
    echo ""
fi
echo ""

# -------------------------------------------------------------------
# STEP 3: Verify/Pull model
# -------------------------------------------------------------------
echo -e "${YELLOW}🧠 Step 3: Checking model availability...${NC}"

MODEL_NAME="${OLLAMA_MODEL#ollama/}"

if ollama list | grep -q "${MODEL_NAME}"; then
    echo -e "${GREEN}✅ Model ${MODEL_NAME} is available${NC}"
else
    echo -e "${YELLOW}⚠️  Model ${MODEL_NAME} not found. Pulling...${NC}"
    echo "   This may take several minutes for first-time download"
    echo ""
    
    if ollama pull "${MODEL_NAME}"; then
        echo -e "${GREEN}✅ Model ${MODEL_NAME} pulled successfully${NC}"
    else
        echo -e "${RED}❌ Failed to pull model ${MODEL_NAME}${NC}"
        exit 1
    fi
fi
echo ""

# -------------------------------------------------------------------
# STEP 4: Check Python environment
# -------------------------------------------------------------------
echo -e "${YELLOW}🐍 Step 4: Checking Python environment...${NC}"

if ! command -v "${PYTHON}" &> /dev/null; then
    echo -e "${RED}❌ Python not found: ${PYTHON}${NC}"
    exit 1
fi

PYTHON_VERSION=$(${PYTHON} --version 2>&1)
echo "   ${PYTHON_VERSION}"

# Check required packages
MISSING_PACKAGES=()
for package in crewai litellm; do
    if ! ${PYTHON} -c "import ${package}" 2>/dev/null; then
        MISSING_PACKAGES+=("${package}")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Installing missing packages: ${MISSING_PACKAGES[*]}${NC}"
    
    if [ -f "${SCRIPT_DIR}/requirements.txt" ]; then
        ${PYTHON} -m pip install -q -r "${SCRIPT_DIR}/requirements.txt"
    else
        ${PYTHON} -m pip install -q crewai litellm
    fi
    
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ All dependencies present${NC}"
fi
echo ""

# -------------------------------------------------------------------
# STEP 5: Generate blog post
# -------------------------------------------------------------------
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}✍️  Step 5: Generating blog post...${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

export NEWS_LLM_MODEL="${OLLAMA_MODEL}"
export OLLAMA_HOST="${OLLAMA_HOST}"

START_TIME=$(date +%s)

cd "${PROJECT_ROOT}"

if ${PYTHON} scripts/generate_daily_blog.py; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    echo -e "${GREEN}✅ Blog post generated (${DURATION}s)${NC}"
else
    echo ""
    echo -e "${RED}❌ Blog generation failed${NC}"
    echo "   Check log: ${LOG_FILE}"
    exit 1
fi
echo ""

# -------------------------------------------------------------------
# STEP 6: Verify output
# -------------------------------------------------------------------
echo -e "${YELLOW}🔍 Step 6: Verifying output...${NC}"

LATEST_POST=$(ls -t "${PROJECT_ROOT}"/blog/posts/*.md 2>/dev/null | grep -v index | head -1)

if [ -z "${LATEST_POST}" ]; then
    echo -e "${RED}❌ No blog post found in blog/posts/${NC}"
    echo "   Expected format: blog/posts/YYYY-MM-DD-*.md"
    echo "   Check: ls -la ${PROJECT_ROOT}/blog/posts/"
    exit 1
fi

echo -e "${GREEN}✅ Blog post found: $(basename "${LATEST_POST}")${NC}"

# Validate file structure
if ! head -1 "${LATEST_POST}" | grep -q "^---$"; then
    echo -e "${RED}❌ Invalid Jekyll front matter${NC}"
    exit 1
fi

WORD_COUNT=$(grep -v "^---" "${LATEST_POST}" | wc -w | xargs)
if [ "${WORD_COUNT}" -lt 100 ]; then
    echo -e "${RED}❌ Post too short: ${WORD_COUNT} words${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Post validation passed (${WORD_COUNT} words)${NC}"
echo ""

# -------------------------------------------------------------------
# STEP 7: Update blog index
# -------------------------------------------------------------------
if [ -f "${PROJECT_ROOT}/blog/generate_index.py" ]; then
    echo -e "${YELLOW}📑 Step 7: Updating blog index...${NC}"
    
    if ${PYTHON} "${PROJECT_ROOT}/blog/generate_index.py"; then
        echo -e "${GREEN}✅ Blog index updated${NC}"
    else
        echo -e "${YELLOW}⚠️  Blog index update failed (non-critical)${NC}"
    fi
    echo ""
fi

# -------------------------------------------------------------------
# STEP 8: Export API feeds (optional)
# -------------------------------------------------------------------
if [ -f "${PROJECT_ROOT}/export_data_feeds.py" ]; then
    echo -e "${YELLOW}📊 Step 8: Exporting API feeds...${NC}"
    
    if ${PYTHON} "${PROJECT_ROOT}/export_data_feeds.py"; then
        echo -e "${GREEN}✅ API feeds exported${NC}"
    else
        echo -e "${YELLOW}⚠️  API feed export failed (non-critical)${NC}"
    fi
    echo ""
fi

# -------------------------------------------------------------------
# STEP 9: Summary
# -------------------------------------------------------------------
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ Blog Generation Complete!${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Extract metadata from post
if [ -n "${LATEST_POST}" ]; then
    TITLE=$(grep "^title:" "${LATEST_POST}" | head -1 | sed 's/title: *"\(.*\)"/\1/')
    DATE=$(grep "^date:" "${LATEST_POST}" | head -1 | sed 's/date: *//')
    
    echo -e "${BLUE}📄 Generated Post:${NC}"
    echo "   File:  $(basename "${LATEST_POST}")"
    [ -n "${TITLE}" ] && echo "   Title: ${TITLE}"
    [ -n "${DATE}" ] && echo "   Date:  ${DATE}"
    echo "   Words: ${WORD_COUNT}"
    echo "   Path:  ${LATEST_POST}"
    echo ""
fi

# Coverage stats
if [ -f "${PROJECT_ROOT}/data/blog_coverage.json" ]; then
    COVERAGE_COUNT=$(${PYTHON} -c "import json; print(len(json.load(open('${PROJECT_ROOT}/data/blog_coverage.json'))))" 2>/dev/null || echo "?")
    echo -e "${BLUE}📈 Coverage Stats:${NC}"
    echo "   Total posts: ${COVERAGE_COUNT}"
    echo "   Coverage:    ${PROJECT_ROOT}/data/blog_coverage.json"
    echo ""
fi

# Next steps
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "   • Review:  cat '${LATEST_POST}'"
echo "   • Preview: cd '${PROJECT_ROOT}' && jekyll serve"
echo "   • Commit:  git add blog/posts/ data/ && git commit -m '📝 New blog post'"
echo ""

# Cleanup instructions
if [ -n "${OLLAMA_PID}" ]; then
    echo -e "${YELLOW}Note: Ollama server running (PID: ${OLLAMA_PID})${NC}"
    echo "      To stop: kill ${OLLAMA_PID}"
    echo ""
fi

echo -e "${GREEN}Done! 🎉${NC}"
echo -e "${CYAN}Log saved: ${LOG_FILE}${NC}"
echo ""

exit 0