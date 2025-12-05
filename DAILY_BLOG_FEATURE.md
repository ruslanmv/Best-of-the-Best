# Daily Best-of-the-Best Blog Feature

## Overview

This feature automatically generates daily blog posts for the Best-of-the-Best website using AI-powered content generation with CrewAI and Ollama.

## How It Works

### 1. Topic Selection

Every day, the system:

1. Reads existing dashboard data from `blog/api/*.json`:
   - `packages.json` - Top Python packages
   - `repositories.json` - Popular GitHub repositories
   - `papers.json` - Most cited research papers
   - `tutorials.json` - Educational tutorials

2. Maintains a coverage log in `data/blog_coverage.json` to track:
   - Which topics have been covered
   - How many times (version 1, 2, 3, etc.)
   - When they were published

3. Selects the next topic using this priority:
   - **First**: Uncovered packages (v1)
   - **Then**: Uncovered repositories (v1)
   - **Then**: Uncovered papers (v1)
   - **Then**: Uncovered tutorials (v1)
   - **Finally**: If everything is covered, start v2, v3, etc. cycles

### 2. Content Generation with CrewAI

The system uses a **3-agent pipeline**:

#### Agent 1: Strategist
- **Role**: AI Content Strategist
- **Task**: Analyzes the topic and creates a comprehensive outline
- **Output**: Structured blog outline with 7 sections

#### Agent 2: Writer
- **Role**: Senior Technical Writer
- **Task**: Writes the full blog post (800-1200 words)
- **Output**: Complete markdown body with code examples

#### Agent 3: Publisher
- **Role**: Jekyll Metadata Curator
- **Task**: Generates SEO-optimized metadata
- **Output**: JSON with title, excerpt, and tags

### 3. Jekyll Blog Post

Each post is saved as `blog/posts/YYYY-MM-DD-kind-slug[-vN].md` with:

- **Front matter**: Jekyll/Minimal Mistakes compatible YAML
- **Body**: Markdown content with H2/H3 headers, code blocks, bullets
- **Footer**: Powered by Jekyll attribution

Example filename: `2025-12-05-package-langchain.md`

### 4. Integration

After generating the post, the GitHub Action:

1. Runs `python blog/generate_index.py` → updates `blog/posts/index.json`
2. Runs `python export_data_feeds.py` → updates API feeds
3. Commits all changes to the repository

## Files Added

```
scripts/
├── llm_client.py              # Multi-provider LLM client
├── generate_daily_blog.py     # Main blog generator script
└── requirements.txt           # Python dependencies

data/
└── blog_coverage.json         # Coverage tracking log

.github/workflows/
└── daily-best-of-the-best.yml # Daily GitHub Action workflow

update_blog.sh                 # Local testing script (recommended)
Makefile                       # Updated with `make update` target
```

## LLM Provider Support

The system supports multiple LLM providers through `scripts/llm_client.py`:

### Default: Local Ollama (CI-optimized)
```bash
export NEWS_LLM_MODEL="ollama/llama3:8b"
export OLLAMA_HOST="http://127.0.0.1:11434"
```

### OpenAI
```bash
export NEWS_LLM_MODEL="openai/gpt-4o-mini"
export OPENAI_API_KEY="sk-..."
```

### Anthropic Claude
```bash
export NEWS_LLM_MODEL="anthropic/claude-3-5-sonnet-latest"
export ANTHROPIC_API_KEY="sk-ant-..."
```

### IBM watsonx.ai
```bash
export NEWS_LLM_MODEL="watsonx/meta-llama/llama-3-1-70b-instruct"
export WATSONX_APIKEY="..."
export WATSONX_URL="https://api.watsonx.ai/v1"
export WATSONX_PROJECT_ID="..."
```

## GitHub Action Schedule

The workflow runs:
- **Daily**: 04:00 UTC (via cron schedule)
- **Manual**: Can be triggered via `workflow_dispatch`

## Local Testing

### Quick Start (Recommended)

The easiest way to test locally:

```bash
# Option 1: Using Make (recommended)
make update

# Option 2: Run script directly
./update_blog.sh
```

The `update_blog.sh` script automatically:
- ✅ Checks if Ollama is installed
- ✅ Starts Ollama server if needed
- ✅ Pulls llama3:8b model automatically
- ✅ Verifies Python dependencies
- ✅ Runs blog generation with timing
- ✅ Updates blog index and API feeds
- ✅ Shows generated post summary with stats

### Manual Testing

If you prefer manual control:

```bash
# Install dependencies
pip install -r scripts/requirements.txt

# Start Ollama (if not running)
ollama serve &
ollama pull llama3:8b

# Set environment
export NEWS_LLM_MODEL="ollama/llama3:8b"
export OLLAMA_HOST="http://127.0.0.1:11434"

# Run generator
python scripts/generate_daily_blog.py

# Rebuild indexes
python blog/generate_index.py
python export_data_feeds.py
```

## Coverage Log Format

`data/blog_coverage.json` contains entries like:

```json
[
  {
    "kind": "package",
    "id": "langchain",
    "version": 1,
    "date": "2025-12-05",
    "filename": "2025-12-05-package-langchain.md"
  },
  {
    "kind": "repo",
    "id": "ollama/ollama",
    "version": 1,
    "date": "2025-12-06",
    "filename": "2025-12-06-repo-ollama-ollama.md"
  }
]
```

## Performance Optimizations

1. **Minimal Context**: Only essential topic metadata is passed to LLMs
2. **Short Prompts**: Clear, concise agent instructions
3. **No Verbose Logging**: `verbose=False` on all agents
4. **Local Ollama**: Fast, free inference in GitHub Actions
5. **Sequential Processing**: One task at a time for reliability

## Benefits

- ✅ **Fresh Content**: Daily automated blog posts keep "Today's Top Pick" dynamic
- ✅ **Comprehensive Coverage**: Eventually covers all dashboard items
- ✅ **Version Tracking**: Can revisit topics with v2, v3 posts for updates
- ✅ **Multi-Provider**: Works with any LLM provider (Ollama, OpenAI, Claude, Watsonx)
- ✅ **CI-Optimized**: Runs efficiently in GitHub Actions with local Ollama
- ✅ **SEO-Friendly**: Professional Jekyll posts with proper metadata
- ✅ **Zero Maintenance**: Fully automated after initial setup

## Troubleshooting

### Issue: CrewAI returns empty body
**Solution**: Check LLM connectivity and model availability

### Issue: Metadata JSON parsing fails
**Solution**: The script extracts JSON from LLM responses that may have extra text

### Issue: No topics selected
**Solution**: Ensure `blog/api/*.json` files exist and contain data

### Issue: Ollama timeout in CI
**Solution**: Workflow waits up to 60 seconds for Ollama to start

## Future Enhancements

Possible improvements:
- Add images/diagrams to posts
- Include trending GitHub stats
- Cross-reference related posts
- Generate social media snippets
- Add author profiles for diversity
