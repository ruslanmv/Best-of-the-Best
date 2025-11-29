# 🤖 Multi-Agent Daily Blog System

A sophisticated multi-agent system that leverages CrewAI and Ollama to automatically generate daily blog posts about trending AI packages, with special focus on IBM watsonx.ai and Watson Orchestrate integration opportunities.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [How It Works](#how-it-works)
- [GitHub Pages Deployment](#github-pages-deployment)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

This multi-agent system combines the power of:
- **CrewAI**: For orchestrating multiple AI agents working together
- **Ollama**: For local LLM inference (using models like llama3.2)
- **Python**: For data processing and automation
- **GitHub Pages**: For hosting the generated blog
- **GitHub Actions**: For daily automated execution

The system analyzes trending AI packages daily and produces comprehensive blog posts that include:
- Package overview and features
- watsonx.ai integration opportunities
- Watson Orchestrate use cases
- Business value analysis
- Implementation guides

## 🏗️ Architecture

### Multi-Agent System

The system consists of three specialized AI agents:

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Agent System                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   Research   │ ───> │   Analysis   │ ───> │  Writer   │ │
│  │    Agent     │      │    Agent     │      │   Agent   │ │
│  └──────────────┘      └──────────────┘      └───────────┘ │
│        │                     │                      │        │
│        ▼                     ▼                      ▼        │
│  Find trending        Analyze watsonx.ai      Generate      │
│  AI packages          integration potential   blog post     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   GitHub Pages       │
                    │   Static Blog        │
                    └──────────────────────┘
```

### Agent Roles

1. **Research Agent** 🔍
   - Role: AI Trends Research Analyst
   - Responsibility: Identifies and researches trending AI packages
   - Tools: Package research tools, PyPI stats, GitHub API

2. **Analysis Agent** 🧠
   - Role: IBM watsonx.ai Integration Specialist
   - Responsibility: Analyzes packages for watsonx.ai and Watson Orchestrate integration
   - Tools: watsonx.ai analysis tool, integration patterns

3. **Writer Agent** ✍️
   - Role: Technical Content Writer and Blogger
   - Responsibility: Creates engaging, SEO-optimized blog posts
   - Tools: Content templates, markdown formatting

## ✨ Features

- **Automated Daily Execution**: GitHub Actions workflow runs daily at 9:00 AM UTC
- **Multi-Agent Collaboration**: Three specialized agents work together sequentially
- **Local LLM**: Uses Ollama for privacy-friendly, cost-effective AI inference
- **watsonx.ai Focus**: Specialized analysis for IBM's AI platform integration
- **Watson Orchestrate**: Identifies automation and orchestration opportunities
- **Static Blog**: Beautiful GitHub Pages blog with no server required
- **Version Control**: All blog posts tracked in Git
- **Customizable**: Easy to modify agents, tasks, and templates

## 📦 Prerequisites

- **Python 3.11+**
- **Ollama** (for local LLM)
- **Git**
- **GitHub account** (for Pages deployment)
- At least 8GB RAM (for running Ollama models)

## 🚀 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/ruslanmv/Best-of-the-Best.git
cd Best-of-the-Best
```

### 2. Install Ollama

**On Linux/macOS:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**On Windows:**
Download from [ollama.com](https://ollama.com/download)

### 3. Pull the LLM Model

```bash
ollama pull llama3.2
```

### 4. Install Python Dependencies

```bash
pip install -r requirements-multiagent.txt
```

## 💻 Usage

### Quick Start

Run the entire system with one command:

```bash
./run_daily_blog.sh
```

This script will:
1. Check and start Ollama
2. Install dependencies
3. Run the multi-agent system
4. Generate blog index
5. Create the daily blog post

### Manual Execution

If you prefer step-by-step execution:

```bash
# 1. Start Ollama service
ollama serve &

# 2. Run the multi-agent system
cd multiagent_system
python crew.py

# 3. Generate blog index
cd ..
python blog/generate_index.py
```

### Testing Individual Components

**Test Research Tool:**
```python
from multiagent_system.tools.package_research_tool import PackageResearchTool

tool = PackageResearchTool()
packages = tool.get_trending_packages(5)
print(packages)
```

**Test watsonx.ai Analysis:**
```python
from multiagent_system.tools.package_research_tool import WatsonXAnalysisTool

analyzer = WatsonXAnalysisTool()
analysis = analyzer.analyze_for_watsonx({'name': 'langchain', 'description': 'LLM framework'})
print(analysis)
```

## 🔄 How It Works

### Daily Workflow

1. **Trigger** (9:00 AM UTC via GitHub Actions)
   - Workflow starts automatically
   - Sets up Python and Ollama environment

2. **Research Phase**
   - Research Agent analyzes trending packages
   - Evaluates download trends, GitHub stars
   - Selects the most promising package

3. **Analysis Phase**
   - Analysis Agent examines the selected package
   - Identifies watsonx.ai integration opportunities
   - Determines Watson Orchestrate use cases
   - Calculates business value

4. **Writing Phase**
   - Writer Agent creates structured blog post
   - Includes code examples and practical guides
   - Formats in Markdown with metadata

5. **Publication**
   - Blog post saved to `blog/posts/`
   - Index.json updated
   - Committed to Git
   - Deployed to GitHub Pages

### File Structure

```
Best-of-the-Best/
├── multiagent_system/
│   ├── config/
│   │   ├── agents.yaml          # Agent definitions
│   │   └── tasks.yaml           # Task definitions
│   ├── tools/
│   │   ├── __init__.py
│   │   └── package_research_tool.py
│   ├── __init__.py
│   └── crew.py                  # Main orchestration
├── blog/
│   ├── posts/
│   │   ├── 2024-11-22-daily-package.md
│   │   └── index.json
│   ├── index.html               # Blog homepage
│   ├── _config.yml              # Jekyll config
│   └── generate_index.py        # Index generator
├── .github/
│   └── workflows/
│       └── daily-blog.yml       # GitHub Actions
├── requirements-multiagent.txt
├── run_daily_blog.sh
└── MULTIAGENT_README.md
```

## 🌐 GitHub Pages Deployment

### Initial Setup

1. **Enable GitHub Pages:**
   - Go to repository Settings
   - Navigate to "Pages"
   - Source: Deploy from a branch
   - Branch: `gh-pages`
   - Click Save

2. **Configure Workflow Permissions:**
   - Go to Settings → Actions → General
   - Workflow permissions: "Read and write permissions"
   - Check "Allow GitHub Actions to create and approve pull requests"

3. **First Deployment:**
   ```bash
   # Run locally first
   ./run_daily_blog.sh

   # Commit and push
   git add .
   git commit -m "🚀 Initial multi-agent system setup"
   git push
   ```

4. **Trigger Daily Workflow:**
   - Go to Actions tab
   - Select "Daily AI Package Blog Generation"
   - Click "Run workflow"

### Accessing Your Blog

After deployment, your blog will be available at:
```
https://ruslanmv.github.io/Best-of-the-Best/
```

## 🎨 Customization

### Change LLM Model

Edit `multiagent_system/crew.py`:
```python
def __init__(self, model_name: str = "llama3.2"):
    # Change to: "mistral", "codellama", etc.
```

### Modify Agent Behavior

Edit `multiagent_system/config/agents.yaml`:
```yaml
research_agent:
  role: "Your Custom Role"
  goal: "Your Custom Goal"
  backstory: "Your Custom Backstory"
```

### Adjust Task Instructions

Edit `multiagent_system/config/tasks.yaml`:
```yaml
research_task:
  description: "Your custom task description"
  expected_output: "Your expected output format"
```

### Change Schedule

Edit `.github/workflows/daily-blog.yml`:
```yaml
on:
  schedule:
    # Change cron expression
    - cron: '0 9 * * *'  # Currently 9:00 AM UTC
```

### Customize Blog Design

Edit `blog/index.html` to change:
- Colors and styling
- Layout structure
- Feature cards
- Header/footer content

## 🐛 Troubleshooting

### Ollama Not Running

```bash
# Check if Ollama is running
pgrep -x "ollama"

# Start Ollama
ollama serve &

# Verify model is available
ollama list
```

### Python Dependencies Issues

```bash
# Upgrade pip
pip install --upgrade pip

# Reinstall dependencies
pip install --force-reinstall -r requirements-multiagent.txt
```

### GitHub Actions Failing

1. Check workflow logs in Actions tab
2. Verify workflow permissions are set correctly
3. Ensure `gh-pages` branch exists
4. Check secrets and tokens if needed

### Blog Not Updating

```bash
# Regenerate blog index
python blog/generate_index.py

# Check Git status
git status

# Manually commit if needed
git add blog/posts/*.md blog/posts/index.json
git commit -m "Update blog"
git push
```

### Memory Issues with Ollama

If you encounter memory errors:
```bash
# Use a smaller model
ollama pull llama3.2:1b

# Or adjust model settings in crew.py
```

## 📊 Monitoring

### View Agent Progress

The system provides verbose output showing:
- Current agent working
- Task being executed
- Research findings
- Analysis results
- Blog generation progress

### Check Blog Posts

```bash
# List all posts
ls -lh blog/posts/

# View latest post
cat blog/posts/$(ls -t blog/posts/*.md | head -1)
```

### GitHub Actions Logs

1. Go to repository Actions tab
2. Click on latest workflow run
3. View detailed logs for each step

## 🎯 watsonx.ai Integration Examples

The system analyzes packages for watsonx.ai integration in several areas:

1. **Model Training Enhancement**
   - Data preprocessing pipelines
   - Feature engineering tools
   - Training optimization

2. **NLP Capabilities**
   - Text processing
   - Prompt engineering
   - Foundation model integration

3. **Deployment Workflows**
   - Model serving
   - API integration
   - Monitoring and logging

4. **Business Intelligence**
   - Analytics integration
   - ROI tracking
   - Performance metrics

## 🔧 Watson Orchestrate Use Cases

The analysis identifies automation opportunities:

1. **Skill Integration**
   - Package as Watson skill
   - API endpoint exposure
   - Workflow automation

2. **Business Process Automation**
   - Data processing automation
   - Report generation
   - Scheduled tasks

3. **Enterprise Integration**
   - Legacy system connectivity
   - Microservices architecture
   - Event-driven workflows

## 📈 Future Enhancements

Potential improvements:
- [ ] Support for multiple LLM providers
- [ ] Interactive blog comments
- [ ] RSS feed generation
- [ ] Email newsletter integration
- [ ] Analytics dashboard
- [ ] Multi-language support
- [ ] Video content generation
- [ ] Podcast summaries

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Additional analysis tools
- New agent types
- Enhanced blog templates
- Integration with more IBM products
- Performance optimizations

## 📝 License

This project follows the license of the Best-of-the-Best repository.

## 🙏 Acknowledgments

- **CrewAI** - Multi-agent orchestration framework
- **Ollama** - Local LLM runtime
- **IBM watsonx.ai** - Enterprise AI platform
- **GitHub Actions** - CI/CD automation
- **GitHub Pages** - Static site hosting

## 📞 Support

For issues and questions:
1. Check this documentation
2. Review GitHub Issues
3. Check CrewAI and Ollama documentation
4. Open a new issue with detailed information

---

**Happy Blogging! 🚀**

Generated with ❤️ by Multi-Agent AI System
