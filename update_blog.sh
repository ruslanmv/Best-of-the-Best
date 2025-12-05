#!/usr/bin/env bash
# update_blog.sh
# Local testing script for Best-of-the-Best daily blog generation
#
# This script:
# 1. Checks/starts Ollama server
# 2. Pulls llama3:8b model if needed
# 3. Generates a new blog post using CrewAI
# 4. Updates blog index and API feeds
# 5. Shows summary of generated content

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
OLLAMA_MODEL="${NEWS_LLM_MODEL:-ollama/llama3:8b}"
PYTHON="${PYTHON:-python3}"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   🏆 Best-of-the-Best Blog Generator (Local Test)${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# -------------------------------------------------------------------
# Step 1: Check if Ollama is installed
# -------------------------------------------------------------------
echo -e "${YELLOW}📦 Step 1: Checking Ollama installation...${NC}"

if ! command -v ollama &> /dev/null; then
    echo -e "${RED}❌ Ollama is not installed.${NC}"
    echo ""
    echo "To install Ollama:"
    echo "  • macOS/Linux: curl -fsSL https://ollama.com/install.sh | sh"
    echo "  • Or use: make ollama"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Ollama is installed${NC}"
echo ""

# -------------------------------------------------------------------
# Step 2: Check if Ollama server is running
# -------------------------------------------------------------------
echo -e "${YELLOW}🔌 Step 2: Checking Ollama server...${NC}"

if curl -fsSL "${OLLAMA_HOST}/api/tags" &> /dev/null; then
    echo -e "${GREEN}✅ Ollama server is running at ${OLLAMA_HOST}${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama server is not running. Starting it...${NC}"

    # Start Ollama in background
    ollama serve > /tmp/ollama.log 2>&1 &
    OLLAMA_PID=$!

    echo "   Waiting for Ollama to start (PID: ${OLLAMA_PID})..."

    # Wait up to 30 seconds for Ollama to be ready
    for i in {1..30}; do
        if curl -fsSL "${OLLAMA_HOST}/api/tags" &> /dev/null; then
            echo -e "${GREEN}✅ Ollama server started successfully${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done

    if ! curl -fsSL "${OLLAMA_HOST}/api/tags" &> /dev/null; then
        echo -e "${RED}❌ Failed to start Ollama server${NC}"
        echo "   Check logs: tail -f /tmp/ollama.log"
        exit 1
    fi
fi
echo ""

# -------------------------------------------------------------------
# Step 3: Check if model is available
# -------------------------------------------------------------------
echo -e "${YELLOW}🧠 Step 3: Checking for llama3:8b model...${NC}"

# Extract model name from OLLAMA_MODEL (remove "ollama/" prefix if present)
MODEL_NAME="${OLLAMA_MODEL#ollama/}"

if ollama list | grep -q "${MODEL_NAME}"; then
    echo -e "${GREEN}✅ Model ${MODEL_NAME} is available${NC}"
else
    echo -e "${YELLOW}⚠️  Model ${MODEL_NAME} not found. Pulling it...${NC}"
    ollama pull "${MODEL_NAME}"
    echo -e "${GREEN}✅ Model ${MODEL_NAME} pulled successfully${NC}"
fi
echo ""

# -------------------------------------------------------------------
# Step 4: Check Python dependencies
# -------------------------------------------------------------------
echo -e "${YELLOW}🐍 Step 4: Checking Python dependencies...${NC}"

if ! ${PYTHON} -c "import crewai" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  CrewAI not installed. Installing dependencies...${NC}"
    ${PYTHON} -m pip install -q -r scripts/requirements.txt
    echo -e "${GREEN}✅ Dependencies installed${NC}"
else
    echo -e "${GREEN}✅ Python dependencies OK${NC}"
fi
echo ""

# -------------------------------------------------------------------
# Step 5: Generate blog post
# -------------------------------------------------------------------
echo -e "${YELLOW}✍️  Step 5: Generating blog post with CrewAI...${NC}"
echo ""

export NEWS_LLM_MODEL="${OLLAMA_MODEL}"
export OLLAMA_HOST="${OLLAMA_HOST}"

START_TIME=$(date +%s)

if ${PYTHON} scripts/generate_daily_blog.py; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))

    echo ""
    echo -e "${GREEN}✅ Blog post generated successfully (took ${DURATION}s)${NC}"
else
    echo ""
    echo -e "${RED}❌ Blog generation failed${NC}"
    exit 1
fi
echo ""

# -------------------------------------------------------------------
# Step 6: Update blog index
# -------------------------------------------------------------------
echo -e "${YELLOW}📑 Step 6: Updating blog index...${NC}"

if ${PYTHON} blog/generate_index.py; then
    echo -e "${GREEN}✅ Blog index updated${NC}"
else
    echo -e "${RED}❌ Blog index update failed${NC}"
    exit 1
fi
echo ""

# -------------------------------------------------------------------
# Step 7: Export API data feeds
# -------------------------------------------------------------------
echo -e "${YELLOW}📊 Step 7: Exporting API data feeds...${NC}"

if ${PYTHON} export_data_feeds.py; then
    echo -e "${GREEN}✅ API feeds exported${NC}"
else
    echo -e "${RED}❌ API feed export failed${NC}"
    exit 1
fi
echo ""

# -------------------------------------------------------------------
# Step 8: Show summary
# -------------------------------------------------------------------
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ Blog generation completed successfully!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Find the most recent blog post
LATEST_POST=$(ls -t blog/posts/*.md 2>/dev/null | grep -v index.json | head -1)

if [ -n "${LATEST_POST}" ]; then
    echo -e "${BLUE}📄 Latest blog post:${NC}"
    echo "   ${LATEST_POST}"
    echo ""

    # Extract title from front matter
    TITLE=$(grep "^title:" "${LATEST_POST}" | head -1 | sed 's/title: *"\(.*\)"/\1/')
    if [ -n "${TITLE}" ]; then
        echo -e "${BLUE}📝 Title:${NC}"
        echo "   ${TITLE}"
        echo ""
    fi

    # Show word count
    WORD_COUNT=$(grep -v "^---" "${LATEST_POST}" | wc -w | xargs)
    echo -e "${BLUE}📊 Stats:${NC}"
    echo "   Word count: ${WORD_COUNT}"
    echo ""
fi

# Show coverage stats
if [ -f data/blog_coverage.json ]; then
    COVERAGE_COUNT=$(${PYTHON} -c "import json; data=json.load(open('data/blog_coverage.json')); print(len(data))" 2>/dev/null || echo "?")
    echo -e "${BLUE}📈 Coverage:${NC}"
    echo "   Total posts generated: ${COVERAGE_COUNT}"
    echo ""
fi

echo -e "${BLUE}🔍 Next steps:${NC}"
echo "   • Preview the post: cat ${LATEST_POST}"
echo "   • View blog locally: make serve"
echo "   • Commit changes: git add . && git commit -m '📝 New blog post'"
echo ""

echo -e "${GREEN}Done! 🎉${NC}"
echo ""
