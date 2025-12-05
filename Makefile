# Makefile for Best-of-the-Best
# Local development helpers for:
#  - Python backend (multi-agent, blog, feeds)
#  - Jekyll + Minimal Mistakes site build/serve

# -------------------------------------------------------------------
# OS detection (for Ruby install scripts)
# -------------------------------------------------------------------
OS := $(shell uname -s 2>/dev/null || echo Windows)

# -------------------------------------------------------------------
# Configurable variables
# -------------------------------------------------------------------
PYTHON       ?= python3
VENV_DIR     ?= .venv
VENV_BIN     := $(VENV_DIR)/bin
PIP          := $(VENV_BIN)/pip
PYTHON_VENV  := $(VENV_BIN)/python

BUNDLE       ?= bundle
JEKYLL       ?= jekyll

# Baseurl used in production (GitHub Pages path)
JEKYLL_BASEURL ?= /Best-of-the-Best

# Get absolute path to project root (where this Makefile is)
PROJECT_ROOT := $(shell pwd)

# -------------------------------------------------------------------
# Phony targets
# -------------------------------------------------------------------
.PHONY: help \
        venv install install-python install-jekyll install-ruby \
        ollama ollama-model \
        backend blog-index export-data update-readme update-db \
        backend-all update \
        serve serve-prod build clean \
        test diagnose verify-structure

# -------------------------------------------------------------------
# Help
# -------------------------------------------------------------------
help:
	@echo ""
	@echo "Best-of-the-Best - Local Dev Makefile"
	@echo "--------------------------------------"
	@echo "Available targets:"
	@echo ""
	@echo "📦 Setup & Installation:"
	@echo "  make install         - Setup Python venv and Jekyll deps (once)"
	@echo "  make install-python  - Setup Python venv and install backend deps"
	@echo "  make install-jekyll  - Install Ruby, Bundler, Jekyll + Minimal Mistakes"
	@echo "  make ollama          - Check/install Ollama (Linux/macOS; optional)"
	@echo "  make ollama-model    - Pull llama3:8b model (requires Ollama)"
	@echo ""
	@echo "🔍 Diagnostics:"
	@echo "  make diagnose        - Run system diagnostics"
	@echo "  make verify-structure - Verify directory structure"
	@echo ""
	@echo "🤖 Backend Operations:"
	@echo "  make backend         - Run multi-agent system (crew.py)"
	@echo "  make update-readme   - Update README tables"
	@echo "  make update-db       - Update tracking database"
	@echo "  make blog-index      - Generate blog index"
	@echo "  make export-data     - Export API data feeds"
	@echo "  make backend-all     - Run full backend pipeline (like CI)"
	@echo ""
	@echo "✍️  Blog Generation:"
	@echo "  make update          - 🏆 Generate daily blog post with CrewAI + Ollama"
	@echo ""
	@echo "🌐 Jekyll Site:"
	@echo "  make serve           - Serve Jekyll site locally at / (dev-friendly)"
	@echo "  make serve-prod      - Serve Jekyll site locally with baseurl $(JEKYLL_BASEURL)"
	@echo "  make build           - Build Jekyll site into ./_site (production baseurl)"
	@echo "  make clean           - Clean Jekyll build artifacts"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test            - Run backend-all + build (full local test)"
	@echo ""

# -------------------------------------------------------------------
# Structure Verification
# -------------------------------------------------------------------
verify-structure:
	@echo "🔍 Verifying project structure..."
	@echo "   Project root: $(PROJECT_ROOT)"
	@if [ ! -d "blog" ]; then \
		echo "❌ blog/ directory missing"; \
		echo "   Creating: mkdir -p blog/posts blog/api"; \
		mkdir -p blog/posts blog/api; \
	else \
		echo "✅ blog/ directory exists"; \
	fi
	@if [ ! -d "blog/posts" ]; then \
		echo "❌ blog/posts/ directory missing"; \
		mkdir -p blog/posts; \
	else \
		echo "✅ blog/posts/ directory exists"; \
	fi
	@if [ ! -d "blog/api" ]; then \
		echo "❌ blog/api/ directory missing"; \
		mkdir -p blog/api; \
	else \
		echo "✅ blog/api/ directory exists"; \
	fi
	@if [ ! -d "scripts" ]; then \
		echo "❌ scripts/ directory missing"; \
		mkdir -p scripts; \
	else \
		echo "✅ scripts/ directory exists"; \
	fi
	@if [ ! -d "data" ]; then \
		echo "❌ data/ directory missing"; \
		mkdir -p data; \
	else \
		echo "✅ data/ directory exists"; \
	fi
	@if [ ! -d "logs" ]; then \
		echo "❌ logs/ directory missing"; \
		mkdir -p logs; \
	else \
		echo "✅ logs/ directory exists"; \
	fi
	@echo "✅ Structure verification complete"

# -------------------------------------------------------------------
# Diagnostics
# -------------------------------------------------------------------
diagnose: verify-structure
	@echo "🔍 Running system diagnostics..."
	@if [ -f "scripts/diagnose_blog_system.py" ]; then \
		$(PYTHON) scripts/diagnose_blog_system.py; \
	else \
		echo "⚠️  scripts/diagnose_blog_system.py not found"; \
		echo "   Please ensure you have the latest version"; \
	fi

# -------------------------------------------------------------------
# Installation / setup
# -------------------------------------------------------------------

# Create a local Python virtualenv
venv:
	@test -d "$(VENV_DIR)" || $(PYTHON) -m venv "$(VENV_DIR)"
	@$(PIP) install --upgrade pip

# Install Python deps for the backend
install-python: venv
	@echo "📦 Installing Python dependencies..."
	@if [ -f "scripts/requirements.txt" ]; then \
		$(PIP) install -r scripts/requirements.txt; \
	elif [ -f "requirements-multiagent.txt" ]; then \
		$(PIP) install -r requirements-multiagent.txt; \
	else \
		echo "⚠️  No requirements file found, installing core packages..."; \
		$(PIP) install crewai litellm; \
	fi
	@echo "✅ Python dependencies installed"

# Install Ruby and build tools via OS-specific scripts
install-ruby:
ifeq ($(OS),Darwin)
	@echo "🍎 Detected macOS..."
	@chmod +x scripts/install_macos.sh
	@./scripts/install_macos.sh
else ifeq ($(OS),Linux)
	@echo "🐧 Detected Linux (Debian/Ubuntu assumed)..."
	@if [ -f /etc/debian_version ]; then \
		echo "➡️  Installing Ruby + build tools via apt-get"; \
		sudo apt-get update; \
		sudo apt-get install -y ruby-full build-essential zlib1g-dev; \
	elif [ -f /etc/redhat-release ]; then \
		echo "🎩 Using scripts/install_fedora.sh"; \
		chmod +x scripts/install_fedora.sh; \
		./scripts/install_fedora.sh; \
	else \
		echo "⚠️  Linux distro not auto-detected. Please install Ruby manually."; \
	fi
else
	@echo "🪟 Detected Windows..."
	@echo "⚠️  Please run 'scripts/install_windows.ps1' in an elevated PowerShell to install Ruby."
endif

# Install Jekyll + Minimal Mistakes via Bundler
# Uses install-ruby to ensure Ruby & build tools are present first.
install-jekyll: install-ruby
	@if ! command -v ruby >/dev/null 2>&1; then \
		echo "❌ Ruby is still not on PATH after install_ruby."; \
		echo "   Please check the output of the install script for PATH instructions."; \
		exit 1; \
	fi
	@if ! command -v gem >/dev/null 2>&1; then \
		echo "❌ 'gem' command not found. Ruby installation may be incomplete."; \
		exit 1; \
	fi
	@if ! command -v $(BUNDLE) >/dev/null 2>&1; then \
		echo "💎 Bundler not found. Installing locally..."; \
		gem install bundler --no-document || { \
			echo "⚠️  Failed to install Bundler. You may need: sudo gem install bundler --no-document"; \
			exit 1; \
		}; \
	else \
		echo "✅ Bundler is already installed."; \
	fi
	@echo "⚙️  Configuring Bundler to install gems into ./vendor/bundle..."
	@$(BUNDLE) config set --local path 'vendor/bundle'
	@echo "📦 Installing Jekyll + theme dependencies via Bundler..."
	@$(BUNDLE) install --jobs 4 --retry 3

# Convenience: install everything
install: verify-structure install-python install-jekyll
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Run diagnostics: make diagnose"
	@echo "  2. Generate a blog post: make update"
	@echo "  3. Serve the site: make serve"
	@echo ""

# -------------------------------------------------------------------
# Ollama (optional local helper)
# -------------------------------------------------------------------

# Install or verify Ollama locally (Linux/macOS only)
ollama:
	@echo "Checking Ollama installation..."
	@if ! command -v ollama >/dev/null 2>&1; then \
		echo "Ollama not found. Installing..."; \
		curl -fsSL https://ollama.com/install.sh | sh; \
	else \
		echo "✅ Ollama is already installed."; \
		ollama --version; \
	fi

# Pull llama3:8b model (Ollama must be installed)
ollama-model: ollama
	@echo "Ensuring llama3:8b model is available..."
	@if ! ollama list | grep -q "llama3:8b"; then \
		echo "Pulling llama3:8b model..."; \
		ollama pull llama3:8b; \
	else \
		echo "✅ llama3:8b model already available"; \
	fi

# -------------------------------------------------------------------
# Backend pipeline (Python)
# -------------------------------------------------------------------

# Run multi-agent system
backend: install-python
	@echo "Running multi-agent system (crew.py)..."
	@if [ -d "multiagent_system" ]; then \
		cd multiagent_system && "$(PYTHON_VENV)" crew.py; \
	else \
		echo "⚠️  multiagent_system/ directory not found"; \
	fi

# Update README tables
update-readme: install-python
	@echo "Updating README tables..."
	@if [ -f "update_readme_tables.py" ]; then \
		"$(PYTHON_VENV)" update_readme_tables.py; \
	else \
		echo "⚠️  update_readme_tables.py not found (skipping)"; \
	fi

# Update tracking DB
update-db: install-python
	@echo "Updating tracking database..."
	@if [ -f "update_readme_daily.py" ]; then \
		"$(PYTHON_VENV)" update_readme_daily.py; \
	else \
		echo "⚠️  update_readme_daily.py not found (skipping)"; \
	fi

# Generate blog index
blog-index: install-python
	@echo "Generating blog index..."
	@if [ -f "blog/generate_index.py" ]; then \
		"$(PYTHON_VENV)" blog/generate_index.py; \
	else \
		echo "⚠️  blog/generate_index.py not found (skipping)"; \
	fi

# Export API feeds
export-data: install-python
	@echo "Exporting API data feeds..."
	@if [ -f "export_data_feeds.py" ]; then \
		"$(PYTHON_VENV)" export_data_feeds.py; \
	else \
		echo "⚠️  export_data_feeds.py not found (skipping)"; \
	fi

# Run the full backend pipeline (similar to CI):
# multi-agent -> README -> DB -> blog index -> API feeds
backend-all: backend update-readme update-db blog-index export-data
	@echo "✅ Backend pipeline completed."

# -------------------------------------------------------------------
# Daily Blog Generation (CrewAI + Ollama)
# -------------------------------------------------------------------

# Generate daily blog post with CrewAI multi-agent system
# This uses update_blog.sh which handles:
#  - Ollama setup and model download
#  - Blog post generation with CrewAI
#  - Blog index and API feed updates
update: verify-structure
	@echo "🏆 Generating daily blog post with CrewAI..."
	@if [ ! -f "update_blog.sh" ]; then \
		echo "❌ update_blog.sh not found in project root"; \
		echo "   Please ensure update_blog.sh is in: $(PROJECT_ROOT)"; \
		exit 1; \
	fi
	@if [ ! -f "scripts/generate_daily_blog.py" ]; then \
		echo "❌ scripts/generate_daily_blog.py not found"; \
		echo "   Please ensure the blog generation script exists"; \
		exit 1; \
	fi
	@bash update_blog.sh

# -------------------------------------------------------------------
# Jekyll site (Minimal Mistakes)
# -------------------------------------------------------------------

# Build the Jekyll site into ./_site with production baseurl
build: install-jekyll verify-structure
	@echo "Building Jekyll site (production baseurl: $(JEKYLL_BASEURL))..."
	@JEKYLL_ENV=production $(BUNDLE) exec $(JEKYLL) build --baseurl "$(JEKYLL_BASEURL)"

# Serve the Jekyll site locally WITHOUT baseurl (dev-friendly)
# Open: http://127.0.0.1:4000/
serve: install-jekyll verify-structure
	@echo "Serving Jekyll site locally at / (no baseurl)..."
	@echo "Open: http://127.0.0.1:4000/"
	@JEKYLL_ENV=development $(BUNDLE) exec $(JEKYLL) serve --livereload --baseurl ""

# Serve the Jekyll site locally WITH production baseurl (for final check)
# Open: http://127.0.0.1:4000$(JEKYLL_BASEURL)/
serve-prod: install-jekyll verify-structure
	@echo "Serving Jekyll site locally with baseurl $(JEKYLL_BASEURL)..."
	@echo "Open: http://127.0.0.1:4000$(JEKYLL_BASEURL)/"
	@JEKYLL_ENV=development $(BUNDLE) exec $(JEKYLL) serve --livereload --baseurl "$(JEKYLL_BASEURL)"

# Clean build artifacts
clean:
	@echo "Cleaning Jekyll build artifacts..."
	@rm -rf _site .jekyll-cache .sass-cache .bundle vendor
	@echo "Cleaning Python artifacts..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Clean complete"

# -------------------------------------------------------------------
# Full local test: backend + Jekyll build
# -------------------------------------------------------------------
test: verify-structure backend-all build
	@echo "✅ Full local test completed: backend pipeline + Jekyll build."

# -------------------------------------------------------------------
# Quick status check
# -------------------------------------------------------------------
status:
	@echo ""
	@echo "📊 Project Status"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Project root: $(PROJECT_ROOT)"
	@echo ""
	@echo "Directory structure:"
	@ls -la blog/posts 2>/dev/null | head -5 || echo "  ❌ blog/posts not found"
	@echo ""
	@echo "Recent blog posts:"
	@ls -t blog/posts/*.md 2>/dev/null | head -3 | xargs -I {} basename {} || echo "  No posts yet"
	@echo ""
	@echo "Coverage:"
	@if [ -f "data/blog_coverage.json" ]; then \
		echo "  Entries: $$(python3 -c 'import json; print(len(json.load(open(\"data/blog_coverage.json\"))))' 2>/dev/null || echo '?')"; \
	else \
		echo "  ❌ No coverage file"; \
	fi
	@echo ""
	@echo "Logs:"
	@ls -t logs/*.log 2>/dev/null | head -3 | xargs -I {} basename {} || echo "  No logs yet"
	@echo ""