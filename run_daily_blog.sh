#!/bin/bash

###############################################################################
# Daily AI Package Blog Generator
# This script runs the multi-agent system to generate daily blog posts
###############################################################################

set -e  # Exit on error

echo "🚀 Daily AI Package Blog Generator"
echo "===================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Ollama is installed
echo -e "${BLUE}Checking Ollama installation...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "${YELLOW}Ollama is not installed. Installing now...${NC}"
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo -e "${GREEN}✓ Ollama is installed${NC}"
fi

# Start Ollama service if not running
echo -e "${BLUE}Starting Ollama service...${NC}"
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &
    OLLAMA_PID=$!
    sleep 5
    echo -e "${GREEN}✓ Ollama service started (PID: $OLLAMA_PID)${NC}"
else
    echo -e "${GREEN}✓ Ollama is already running${NC}"
fi

# Pull required model
echo -e "${BLUE}Ensuring llama3.2 model is available...${NC}"
ollama pull llama3.2
echo -e "${GREEN}✓ Model ready${NC}"

# Install Python dependencies
echo -e "${BLUE}Installing Python dependencies...${NC}"
pip install -q -r requirements-multiagent.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Run the multi-agent system
echo ""
echo -e "${BLUE}Running multi-agent system...${NC}"
echo "===================================="
cd multiagent_system
python crew.py
cd ..

# Generate blog index
echo ""
echo -e "${BLUE}Generating blog index...${NC}"
python blog/generate_index.py
echo -e "${GREEN}✓ Blog index updated${NC}"

# Display results
echo ""
echo -e "${GREEN}===================================="
echo "✨ Blog generation completed!"
echo "====================================${NC}"
echo ""
echo "📝 New blog posts are available in: blog/posts/"
echo "🌐 View the blog at: blog/index.html"
echo ""
echo "To deploy to GitHub Pages:"
echo "  git add blog/posts/*.md blog/posts/index.json"
echo "  git commit -m '📝 Add daily blog post'"
echo "  git push"
echo ""
