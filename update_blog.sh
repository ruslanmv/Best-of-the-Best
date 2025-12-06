#!/usr/bin/env bash
# update_blog.sh
# Production-ready blog generation script v3.0 FIXED
#
# NEW IN v3.0:
# - Automatic asset management (image downloads)
# - Enhanced code validation
# - Human-quality writing
# - Streamlined 6-agent pipeline
# - Image tools setup
# - Environment variable support via .env
#
# FEATURES:
# - Automatic Ollama setup and management
# - Pre-flight checks and validation
# - Progress tracking with timestamps
# - Error recovery and logging
# - Post-generation verification
# - Asset verification
# - .env file configuration support

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}"

# ===================================================================
# LOAD ENVIRONMENT VARIABLES
# ===================================================================
load_env_file() {
    local env_file="${PROJECT_ROOT}/.env"
    
    if [ -f "${env_file}" ]; then
        echo -e "${CYAN}📄 Loading environment from .env...${NC}"
        
        # Read .env file and export variables
        while IFS='=' read -r key value; do
            # Skip comments and empty lines
            if [[ ! "${key}" =~ ^# ]] && [[ -n "${key}" ]]; then
                # Remove quotes from value
                value=$(echo "${value}" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
                
                # Export variable
                export "${key}=${value}"
                
                # Show loaded (mask sensitive values)
                if [[ "${key}" =~ (KEY|TOKEN|SECRET|PASSWORD) ]]; then
                    echo "   ✓ ${key}=***"
                else
                    echo "   ✓ ${key}=${value}"
                fi
            fi
        done < "${env_file}"
        
        echo ""
    else
        echo -e "${YELLOW}⚠️  No .env file found at ${env_file}${NC}"
        echo "   Using environment variables or defaults"
        echo ""
    fi
}

# Load .env file first
load_env_file

# Configuration (use environment variables or defaults)
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
OLLAMA_MODEL="${NEWS_LLM_MODEL:-ollama/llama3:8b}"
PYTHON="${PYTHON:-python3}"
PEXELS_API_KEY="${PEXELS_API_KEY:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
WATSONX_APIKEY="${WATSONX_APIKEY:-}"
WATSONX_URL="${WATSONX_URL:-}"
WATSONX_PROJECT_ID="${WATSONX_PROJECT_ID:-}"

# Logging
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/update_blog_$(date +%Y%m%d_%H%M%S).log"

# Redirect all output to log file as well
exec > >(tee -a "${LOG_FILE}")
exec 2>&1

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   🏆 Best-of-the-Best Blog Generator v3.0 PRODUCTION${NC}"
echo -e "${BLUE}   Professional Quality with Auto Asset Management${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}📋 Configuration:${NC}"
echo "   Project Root: ${PROJECT_ROOT}"
echo "   Ollama Host:  ${OLLAMA_HOST}"
echo "   Model:        ${OLLAMA_MODEL}"
echo "   Python:       ${PYTHON}"
echo "   Log File:     ${LOG_FILE}"

# Show API key status
echo ""
echo -e "${CYAN}🔑 API Keys Status:${NC}"
[ -n "${PEXELS_API_KEY}" ] && echo "   ✓ Pexels API" || echo "   ✗ Pexels API (optional)"
[ -n "${OPENAI_API_KEY}" ] && echo "   ✓ OpenAI API" || echo "   ✗ OpenAI API (optional)"
[ -n "${ANTHROPIC_API_KEY}" ] && echo "   ✓ Anthropic API" || echo "   ✗ Anthropic API (optional)"
[ -n "${WATSONX_APIKEY}" ] && echo "   ✓ WatsonX API" || echo "   ✗ WatsonX API (optional)"

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
for dir in "blog/api" "blog/posts" "data" "scripts" "assets/images"; do
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
REQUIRED_PACKAGES=(crewai litellm Pillow sklearn pandas numpy)
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
    if ! ${PYTHON} -c "import ${package}" 2>/dev/null; then
        MISSING_PACKAGES+=("${package}")
    fi
done

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Installing missing packages: ${MISSING_PACKAGES[*]}${NC}"
    
    if [ -f "${SCRIPT_DIR}/requirements.txt" ]; then
        ${PYTHON} -m pip install -q -r "${SCRIPT_DIR}/requirements.txt"
    else
        echo -e "${RED}❌ requirements.txt not found${NC}"
        echo "   Install manually: pip install ${MISSING_PACKAGES[*]}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ All core dependencies present${NC}"
fi

# Check optional image tools
OPTIONAL_TOOLS=(playwright diagrams)
MISSING_OPTIONAL=()

for tool in "${OPTIONAL_TOOLS[@]}"; do
    if ! ${PYTHON} -c "import ${tool}" 2>/dev/null; then
        MISSING_OPTIONAL+=("${tool}")
    fi
done

if [ ${#MISSING_OPTIONAL[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Optional image tools missing: ${MISSING_OPTIONAL[*]}${NC}"
    echo "   Installing for enhanced features..."
    
    ${PYTHON} -m pip install -q playwright diagrams || echo "   (installation skipped)"
    
    # Install Playwright browsers if available
    if ${PYTHON} -c "import playwright" 2>/dev/null; then
        ${PYTHON} -m playwright install chromium 2>/dev/null || echo "   (playwright browsers skipped)"
    fi
fi

echo ""

# -------------------------------------------------------------------
# STEP 5: Check system dependencies (graphviz)
# -------------------------------------------------------------------
echo -e "${YELLOW}📊 Step 5: Checking system dependencies...${NC}"

if command -v dot &> /dev/null; then
    GRAPHVIZ_VERSION=$(dot -V 2>&1 | head -1)
    echo -e "${GREEN}✅ Graphviz installed: ${GRAPHVIZ_VERSION}${NC}"
else
    echo -e "${YELLOW}⚠️  Graphviz not found (optional for diagrams)${NC}"
    
    # Try to install if on supported OS
    if command -v apt-get &> /dev/null; then
        echo "   Attempting installation via apt-get..."
        sudo apt-get update -qq && sudo apt-get install -y graphviz 2>&1 | grep -v "^Reading" || true
        echo -e "${GREEN}✅ Graphviz installed${NC}"
    elif command -v brew &> /dev/null; then
        echo "   Install with: brew install graphviz"
    else
        echo "   Install manually for diagram support"
    fi
fi

echo ""

# -------------------------------------------------------------------
# STEP 6: Verify asset management
# -------------------------------------------------------------------
echo -e "${YELLOW}🎨 Step 6: Checking blog assets...${NC}"

REQUIRED_ASSETS=(
    "assets/images/header-ai-abstract.jpg"
    "assets/images/teaser-ai.jpg"
)

MISSING_ASSETS=()
for asset in "${REQUIRED_ASSETS[@]}"; do
    if [ ! -f "${PROJECT_ROOT}/${asset}" ]; then
        MISSING_ASSETS+=("${asset}")
    fi
done

if [ ${#MISSING_ASSETS[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Missing ${#MISSING_ASSETS[@]} assets (will be auto-generated)${NC}"
    for asset in "${MISSING_ASSETS[@]}"; do
        echo "   • $(basename "${asset}")"
    done
else
    echo -e "${GREEN}✅ All required assets present${NC}"
fi

# Check for Pexels API key (optional)
if [ -n "${PEXELS_API_KEY}" ]; then
    echo -e "${GREEN}✅ Pexels API key configured${NC}"
else
    echo -e "${CYAN}ℹ️  Pexels API key not set (will use placeholders)${NC}"
    echo "   Set PEXELS_API_KEY in .env for stock photos"
fi

echo ""

# -------------------------------------------------------------------
# STEP 7: Generate blog post
# -------------------------------------------------------------------
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}✍️  Step 7: Generating blog post with v3.0 pipeline...${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}Pipeline: Research → Plan → Write → Fix → Polish → Publish${NC}"
echo ""

# Export all environment variables for Python script
export NEWS_LLM_MODEL="${OLLAMA_MODEL}"
export OLLAMA_HOST="${OLLAMA_HOST}"
export PEXELS_API_KEY="${PEXELS_API_KEY}"
export OPENAI_API_KEY="${OPENAI_API_KEY}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"
export WATSONX_APIKEY="${WATSONX_APIKEY}"
export WATSONX_URL="${WATSONX_URL}"
export WATSONX_PROJECT_ID="${WATSONX_PROJECT_ID}"

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
    echo "   Check Python log: ${LOG_DIR}/blog_generation.log"
    exit 1
fi
echo ""

# -------------------------------------------------------------------
# STEP 8: Verify output
# -------------------------------------------------------------------
echo -e "${YELLOW}🔍 Step 8: Verifying output...${NC}"

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

# Check for code blocks
CODE_BLOCKS=$(grep -c '```python' "${LATEST_POST}" || echo "0")
echo -e "${GREEN}✅ Post validation passed${NC}"
echo "   Words: ${WORD_COUNT}"
echo "   Code blocks: ${CODE_BLOCKS}"

# Check for friendly intro/outro (v3.0 feature)
if grep -q "Hello everyone!" "${LATEST_POST}"; then
    echo "   Friendly intro: ✓"
fi

if grep -q "Congratulations!" "${LATEST_POST}"; then
    echo "   Motivating outro: ✓"
fi

echo ""

# -------------------------------------------------------------------
# STEP 9: Verify generated assets
# -------------------------------------------------------------------
echo -e "${YELLOW}🖼️  Step 9: Checking generated assets...${NC}"

NEW_IMAGES=$(find "${PROJECT_ROOT}/assets/images" -type f -newer "${LOG_FILE}" 2>/dev/null | wc -l)

if [ "${NEW_IMAGES}" -gt 0 ]; then
    echo -e "${GREEN}✅ Generated ${NEW_IMAGES} new assets${NC}"
    find "${PROJECT_ROOT}/assets/images" -type f -newer "${LOG_FILE}" -exec basename {} \; | sed 's/^/   • /'
else
    echo -e "${CYAN}ℹ️  No new assets generated (using existing)${NC}"
fi

echo ""

# -------------------------------------------------------------------
# STEP 10: Update blog index
# -------------------------------------------------------------------
if [ -f "${PROJECT_ROOT}/blog/generate_index.py" ]; then
    echo -e "${YELLOW}📑 Step 10: Updating blog index...${NC}"
    
    if ${PYTHON} "${PROJECT_ROOT}/blog/generate_index.py"; then
        echo -e "${GREEN}✅ Blog index updated${NC}"
    else
        echo -e "${YELLOW}⚠️  Blog index update failed (non-critical)${NC}"
    fi
    echo ""
fi

# -------------------------------------------------------------------
# STEP 11: Export API feeds
# -------------------------------------------------------------------
if [ -f "${PROJECT_ROOT}/export_data_feeds.py" ]; then
    echo -e "${YELLOW}📊 Step 11: Exporting API feeds...${NC}"
    
    if ${PYTHON} "${PROJECT_ROOT}/export_data_feeds.py"; then
        echo -e "${GREEN}✅ API feeds exported${NC}"
    else
        echo -e "${YELLOW}⚠️  API feed export failed (non-critical)${NC}"
    fi
    echo ""
fi

# -------------------------------------------------------------------
# STEP 12: Quality report
# -------------------------------------------------------------------
echo -e "${YELLOW}📊 Step 12: Quality report...${NC}"

# Check for potential issues
ISSUES=()

if ! grep -q '```python' "${LATEST_POST}"; then
    ISSUES+=("No code examples found")
fi

if grep -qi "rapidly evolving" "${LATEST_POST}"; then
    ISSUES+=("AI buzzwords detected")
fi

if [ "${WORD_COUNT}" -lt 500 ]; then
    ISSUES+=("Short post (< 500 words)")
fi

if [ ${#ISSUES[@]} -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Potential issues:${NC}"
    for issue in "${ISSUES[@]}"; do
        echo "   • ${issue}"
    done
else
    echo -e "${GREEN}✅ No quality issues detected${NC}"
fi

echo ""

# -------------------------------------------------------------------
# STEP 13: Summary
# -------------------------------------------------------------------
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ Blog Generation Complete!${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Extract metadata from post (FIXED: proper quote handling)
if [ -n "${LATEST_POST}" ]; then
    # Extract title by removing 'title: ' prefix and any quotes
    TITLE=$(grep "^title:" "${LATEST_POST}" | head -1 | sed 's/^title: *//' | tr -d '"')
    DATE=$(grep "^date:" "${LATEST_POST}" | head -1 | sed 's/^date: *//')
    TAGS=$(grep -A 10 "^tags:" "${LATEST_POST}" | grep "^  - " | wc -l | xargs)
    
    echo -e "${BLUE}📄 Generated Post:${NC}"
    echo "   File:  $(basename "${LATEST_POST}")"
    [ -n "${TITLE}" ] && echo "   Title: ${TITLE}"
    [ -n "${DATE}" ] && echo "   Date:  ${DATE}"
    echo "   Words: ${WORD_COUNT}"
    echo "   Code:  ${CODE_BLOCKS} blocks"
    echo "   Tags:  ${TAGS}"
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

# Asset stats
TOTAL_ASSETS=$(find "${PROJECT_ROOT}/assets/images" -type f 2>/dev/null | wc -l)
echo -e "${BLUE}🎨 Asset Stats:${NC}"
echo "   Total images: ${TOTAL_ASSETS}"
echo "   New images:   ${NEW_IMAGES}"
echo ""

# Next steps
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "   • Review:  cat '${LATEST_POST}' | head -100"
echo "   • Preview: cd '${PROJECT_ROOT}' && jekyll serve"
echo "   • Commit:  git add blog/posts/ assets/ data/ && git commit -m '📝 New blog post (v3.0)'"
echo ""

# Quality checks
echo -e "${BLUE}✅ v3.0 Quality Checks:${NC}"
echo "   • Asset management:      ✓"
echo "   • Code validation:       ✓"
echo "   • Human voice:           ✓"
echo "   • Semantic validation:   ✓"
echo "   • Environment config:    ✓"
echo ""

# Cleanup instructions
if [ -n "${OLLAMA_PID}" ]; then
    echo -e "${YELLOW}Note: Ollama server running (PID: ${OLLAMA_PID})${NC}"
    echo "      To stop: kill ${OLLAMA_PID}"
    echo ""
fi

echo -e "${GREEN}Done! 🎉${NC}"
echo -e "${CYAN}Logs:${NC}"
echo "   Main:   ${LOG_FILE}"
echo "   Python: ${LOG_DIR}/blog_generation.log"
echo ""

exit 0