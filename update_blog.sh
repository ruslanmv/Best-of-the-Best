#!/usr/bin/env bash
# update_blog.sh
# Production-ready blog generation script v3.1 (Provider-aware)
#
# Fix:
# - If NEWS_LLM_MODEL is watsonx/* (or openai/* / anthropic/*), DO NOT run Ollama checks/pulls.
# - Only run Ollama installation/server/pull when provider is ollama/*.
#
# Usage:
#   make update
#   or
#   ./update_blog.sh

set -euo pipefail

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

    # Robust-ish .env loader:
    # - ignores comments/blank lines
    # - supports KEY=VALUE with '=' in VALUE (keeps everything after first '=')
    # - trims surrounding quotes
    while IFS= read -r line || [ -n "$line" ]; do
      # trim leading/trailing whitespace
      line="$(echo "$line" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"

      # skip blank / comment
      [[ -z "$line" ]] && continue
      [[ "$line" =~ ^# ]] && continue

      # must contain '='
      if [[ "$line" != *"="* ]]; then
        continue
      fi

      local key="${line%%=*}"
      local value="${line#*=}"

      # trim whitespace around key
      key="$(echo "$key" | sed -e 's/[[:space:]]*$//')"
      # trim whitespace around value
      value="$(echo "$value" | sed -e 's/^[[:space:]]*//')"

      # strip surrounding quotes
      value="$(echo "$value" | sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")"

      # export
      export "${key}=${value}"

      # print masked
      if [[ "${key}" =~ (KEY|TOKEN|SECRET|PASSWORD|APIKEY) ]]; then
        echo "   ✓ ${key}=***"
      else
        echo "   ✓ ${key}=${value}"
      fi
    done < "${env_file}"

    echo ""
  else
    echo -e "${YELLOW}⚠️  No .env file found at ${env_file}${NC}"
    echo "   Using environment variables or defaults"
    echo ""
  fi
}

load_env_file

# ===================================================================
# CONFIG
# ===================================================================

PYTHON="${PYTHON:-python3}"
PEXELS_API_KEY="${PEXELS_API_KEY:-}"
OPENAI_API_KEY="${OPENAI_API_KEY:-}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
WATSONX_APIKEY="${WATSONX_APIKEY:-}"
WATSONX_URL="${WATSONX_URL:-https://us-south.ml.cloud.ibm.com}"
WATSONX_PROJECT_ID="${WATSONX_PROJECT_ID:-}"

NEWS_LLM_MODEL="${NEWS_LLM_MODEL:-ollama/llama3:8b}"
NEWS_LLM_TEMPERATURE="${NEWS_LLM_TEMPERATURE:-0.7}"

# Ollama settings are only relevant if provider=ollama
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"

# Logging
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/update_blog_$(date +%Y%m%d_%H%M%S).log"

exec > >(tee -a "${LOG_FILE}")
exec 2>&1

# Provider detection
PROVIDER="${NEWS_LLM_MODEL%%/*}"
MODEL_REMAINDER="${NEWS_LLM_MODEL#*/}"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   🏆 Best-of-the-Best Blog Generator (PROD)${NC}"
echo -e "${BLUE}   Provider-aware runner (Ollama/OpenAI/Anthropic/Watsonx)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}📋 Configuration:${NC}"
echo "   Project Root: ${PROJECT_ROOT}"
echo "   Provider:     ${PROVIDER}"
echo "   Model:        ${NEWS_LLM_MODEL}"
echo "   Python:       ${PYTHON}"
echo "   Log File:     ${LOG_FILE}"
if [[ "${PROVIDER}" == "ollama" ]]; then
  echo "   Ollama Host:  ${OLLAMA_HOST}"
fi

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

if [ ! -f "${PROJECT_ROOT}/blog/README.md" ] && [ ! -d "${PROJECT_ROOT}/blog/api" ]; then
  echo -e "${RED}❌ Error: Not in project root or missing blog structure${NC}"
  echo "   Expected: ${PROJECT_ROOT}/blog/"
  echo "   Current:  $(pwd)"
  exit 1
fi

for dir in "blog/api" "blog/posts" "data" "scripts" "assets/images"; do
  if [ ! -d "${PROJECT_ROOT}/${dir}" ]; then
    echo -e "${YELLOW}⚠️  Creating missing directory: ${dir}${NC}"
    mkdir -p "${PROJECT_ROOT}/${dir}"
  fi
done

if [ ! -f "${PROJECT_ROOT}/blog/api/packages.json" ] && \
   [ ! -f "${PROJECT_ROOT}/blog/api/repositories.json" ]; then
  echo -e "${RED}❌ No API data found in blog/api/${NC}"
  echo "   Required: packages.json or repositories.json"
  echo "   Run data export first: make export"
  exit 1
fi

# Provider-specific env validation
case "${PROVIDER}" in
  ollama)
    : # no extra validation here
    ;;
  openai)
    if [ -z "${OPENAI_API_KEY}" ]; then
      echo -e "${RED}❌ Provider is openai but OPENAI_API_KEY is not set${NC}"
      exit 1
    fi
    ;;
  anthropic)
    if [ -z "${ANTHROPIC_API_KEY}" ]; then
      echo -e "${RED}❌ Provider is anthropic but ANTHROPIC_API_KEY is not set${NC}"
      exit 1
    fi
    ;;
  watsonx)
    if [ -z "${WATSONX_APIKEY}" ] || [ -z "${WATSONX_URL}" ] || [ -z "${WATSONX_PROJECT_ID}" ]; then
      echo -e "${RED}❌ Provider is watsonx but one of required vars is missing:${NC}"
      echo "   Required: WATSONX_APIKEY, WATSONX_URL, WATSONX_PROJECT_ID"
      exit 1
    fi
    ;;
  *)
    echo -e "${RED}❌ Unsupported provider prefix in NEWS_LLM_MODEL: ${PROVIDER}${NC}"
    echo "   Expected: ollama/*, openai/*, anthropic/*, watsonx/*"
    exit 1
    ;;
esac

echo -e "${GREEN}✅ Pre-flight checks passed${NC}"
echo ""

# -------------------------------------------------------------------
# STEP 1-3: Ollama setup ONLY if provider is ollama
# -------------------------------------------------------------------
OLLAMA_PID=""

if [[ "${PROVIDER}" == "ollama" ]]; then
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

  OLLAMA_VERSION="$(ollama --version 2>/dev/null || echo "unknown")"
  echo -e "${GREEN}✅ Ollama installed: ${OLLAMA_VERSION}${NC}"
  echo ""

  echo -e "${YELLOW}🔌 Step 2: Checking/Starting Ollama server...${NC}"

  if curl -fsSL "${OLLAMA_HOST}/api/tags" &> /dev/null; then
    echo -e "${GREEN}✅ Ollama server already running at ${OLLAMA_HOST}${NC}"
  else
    echo -e "${YELLOW}⚠️  Starting Ollama server...${NC}"
    ollama serve > "${LOG_DIR}/ollama_$(date +%Y%m%d_%H%M%S).log" 2>&1 &
    OLLAMA_PID=$!
    echo "   PID: ${OLLAMA_PID}"
    echo "   Waiting for startup..."

    for i in {1..60}; do
      if curl -fsSL "${OLLAMA_HOST}/api/tags" &> /dev/null; then
        echo -e "${GREEN}✅ Ollama server started successfully${NC}"
        break
      fi
      if [ "$i" -eq 60 ]; then
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

  echo -e "${YELLOW}🧠 Step 3: Checking Ollama model availability...${NC}"
  OLLAMA_MODEL_NAME="${MODEL_REMAINDER}"

  if ollama list | grep -q "${OLLAMA_MODEL_NAME}"; then
    echo -e "${GREEN}✅ Model ${OLLAMA_MODEL_NAME} is available${NC}"
  else
    echo -e "${YELLOW}⚠️  Model ${OLLAMA_MODEL_NAME} not found. Pulling...${NC}"
    echo "   This may take several minutes for first-time download"
    echo ""
    if ollama pull "${OLLAMA_MODEL_NAME}"; then
      echo -e "${GREEN}✅ Model ${OLLAMA_MODEL_NAME} pulled successfully${NC}"
    else
      echo -e "${RED}❌ Failed to pull model ${OLLAMA_MODEL_NAME}${NC}"
      exit 1
    fi
  fi
  echo ""
else
  echo -e "${YELLOW}📦 Step 1-3: Skipping Ollama setup (provider=${PROVIDER})${NC}"
  echo ""
fi

# -------------------------------------------------------------------
# STEP 4: Check Python environment
# -------------------------------------------------------------------
echo -e "${YELLOW}🐍 Step 4: Checking Python environment...${NC}"

if ! command -v "${PYTHON}" &> /dev/null; then
  echo -e "${RED}❌ Python not found: ${PYTHON}${NC}"
  exit 1
fi

echo "   $(${PYTHON} --version 2>&1)"

REQUIRED_PACKAGES=(crewai litellm Pillow sklearn pandas numpy requests python_dotenv)
MISSING_PACKAGES=()

for package in "${REQUIRED_PACKAGES[@]}"; do
  # python-dotenv imports as dotenv, not python_dotenv; check that separately
  if [[ "${package}" == "python_dotenv" ]]; then
    if ! ${PYTHON} -c "import dotenv" 2>/dev/null; then
      MISSING_PACKAGES+=("python-dotenv")
    fi
  else
    if ! ${PYTHON} -c "import ${package}" 2>/dev/null; then
      MISSING_PACKAGES+=("${package}")
    fi
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

echo ""

# -------------------------------------------------------------------
# STEP 5: Verify assets
# -------------------------------------------------------------------
echo -e "${YELLOW}🎨 Step 5: Checking blog assets...${NC}"

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

if [ -n "${PEXELS_API_KEY}" ]; then
  echo -e "${GREEN}✅ Pexels API key configured${NC}"
else
  echo -e "${CYAN}ℹ️  Pexels API key not set (will use placeholders)${NC}"
fi

echo ""

# -------------------------------------------------------------------
# STEP 6: Generate blog post
# -------------------------------------------------------------------
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}✍️  Step 6: Generating blog post with CrewAI...${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Export env vars for Python
export NEWS_LLM_MODEL="${NEWS_LLM_MODEL}"
export NEWS_LLM_TEMPERATURE="${NEWS_LLM_TEMPERATURE}"
export OLLAMA_HOST="${OLLAMA_HOST}"
export PEXELS_API_KEY="${PEXELS_API_KEY}"
export OPENAI_API_KEY="${OPENAI_API_KEY}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}"
export WATSONX_APIKEY="${WATSONX_APIKEY}"
export WATSONX_URL="${WATSONX_URL}"
export WATSONX_PROJECT_ID="${WATSONX_PROJECT_ID}"

START_TIME="$(date +%s)"
cd "${PROJECT_ROOT}"

if ${PYTHON} scripts/generate_daily_blog.py; then
  END_TIME="$(date +%s)"
  DURATION="$((END_TIME - START_TIME))"
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
# STEP 7: Verify output
# -------------------------------------------------------------------
echo -e "${YELLOW}🔍 Step 7: Verifying output...${NC}"

LATEST_POST="$(ls -t "${PROJECT_ROOT}"/blog/posts/*.md 2>/dev/null | grep -v index | head -1 || true)"

if [ -z "${LATEST_POST}" ]; then
  echo -e "${RED}❌ No blog post found in blog/posts/${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Blog post found: $(basename "${LATEST_POST}")${NC}"

if ! head -1 "${LATEST_POST}" | grep -q "^---$"; then
  echo -e "${RED}❌ Invalid Jekyll front matter${NC}"
  exit 1
fi

WORD_COUNT="$(grep -v "^---" "${LATEST_POST}" | wc -w | xargs)"
if [ "${WORD_COUNT}" -lt 100 ]; then
  echo -e "${RED}❌ Post too short: ${WORD_COUNT} words${NC}"
  exit 1
fi

CODE_BLOCKS="$(grep -c '```python' "${LATEST_POST}" 2>/dev/null || echo "0")"

echo -e "${GREEN}✅ Post validation passed${NC}"
echo "   Words: ${WORD_COUNT}"
echo "   Code blocks: ${CODE_BLOCKS}"
echo ""

# -------------------------------------------------------------------
# STEP 8: Summary
# -------------------------------------------------------------------
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ Blog Generation Complete!${NC}"
echo -e "${MAGENTA}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

TITLE="$(grep "^title:" "${LATEST_POST}" | head -1 | sed 's/^title: *//' | tr -d '"')"
DATE="$(grep "^date:" "${LATEST_POST}" | head -1 | sed 's/^date: *//')"

echo -e "${BLUE}📄 Generated Post:${NC}"
echo "   File:  $(basename "${LATEST_POST}")"
[ -n "${TITLE}" ] && echo "   Title: ${TITLE}"
[ -n "${DATE}" ] && echo "   Date:  ${DATE}"
echo "   Words: ${WORD_COUNT}"
echo "   Code:  ${CODE_BLOCKS} blocks"
echo "   Path:  ${LATEST_POST}"
echo ""

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
