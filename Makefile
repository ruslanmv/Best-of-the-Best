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
PYTHON_VENV  := $(VENV_DIR)/python

BUNDLE       ?= bundle
JEKYLL       ?= jekyll

# Baseurl used in production (GitHub Pages path)
JEKYLL_BASEURL ?= /Best-of-the-Best

# -------------------------------------------------------------------
# Phony targets
# -------------------------------------------------------------------
.PHONY: help \
        venv install install-python install-jekyll install-ruby \
        ollama ollama-model \
        backend blog-index export-data update-readme update-db \
        backend-all update \
        serve serve-prod build clean \
        test

# -------------------------------------------------------------------
# Help
# -------------------------------------------------------------------
help:
	@echo ""
	@echo "Best-of-the-Best - Local Dev Makefile"
	@echo "--------------------------------------"
	@echo "Available targets:"
	@echo "  make install         - Setup Python venv and Jekyll deps (once)"
	@echo "  make install-python  - Setup Python venv and install backend deps"
	@echo "  make install-jekyll  - Install Ruby, Bundler, Jekyll + Minimal Mistakes"
	@echo "  make ollama          - Check/install Ollama (Linux/macOS; optional)"
	@echo "  make ollama-model    - Pull llama3.2 model (requires Ollama)"
	@echo "  make backend         - Run multi-agent system (crew.py)"
	@echo "  make update-readme   - Update README tables"
	@echo "  make update-db       - Update tracking database"
	@echo "  make blog-index      - Generate blog index"
	@echo "  make export-data     - Export API data feeds"
	@echo "  make backend-all     - Run full backend pipeline (like CI)"
	@echo "  make update          - 🏆 Generate daily blog post with CrewAI + Ollama"
	@echo "  make serve           - Serve Jekyll site locally at / (dev-friendly)"
	@echo "  make serve-prod      - Serve Jekyll site locally with baseurl $(JEKYLL_BASEURL)"
	@echo "  make build           - Build Jekyll site into ./_site (production baseurl)"
	@echo "  make clean           - Clean Jekyll build artifacts"
	@echo "  make test            - Run backend-all + build (full local test)"
	@echo ""

# -------------------------------------------------------------------
# Installation / setup
# -------------------------------------------------------------------

# Create a local Python virtualenv
venv:
	@test -d "$(VENV_DIR)" || $(PYTHON) -m venv "$(VENV_DIR)"
	@$(PIP) install --upgrade pip

# Install Python deps for the backend
install-python: venv
	@$(PIP) install -r requirements-multiagent.txt

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
install: install-python install-jekyll

# -------------------------------------------------------------------
# Ollama (optional local helper, similar to run_daily_blog.sh)
# -------------------------------------------------------------------

# Install or verify Ollama locally (Linux/macOS only)
ollama:
	@echo "Checking Ollama installation..."
	@if ! command -v ollama >/dev/null 2>&1; then \
		echo "Ollama not found. Installing..."; \
		curl -fsSL https://ollama.com/install.sh | sh; \
	else \
		echo "Ollama is already installed."; \
	fi

# Pull llama3.2 model (Ollama must be installed)
ollama-model:
	@echo "Ensuring llama3.2 model is available..."
	@ollama pull llama3.2

# -------------------------------------------------------------------
# Backend pipeline (Python)
# -------------------------------------------------------------------

# Run multi-agent system
backend: install-python
	@echo "Running multi-agent system (crew.py)..."
	@cd multiagent_system && "$(PYTHON_VENV)" crew.py

# Update README tables
update-readme: install-python
	@echo "Updating README tables..."
	@"$(PYTHON_VENV)" update_readme_tables.py

# Update tracking DB
update-db: install-python
	@echo "Updating tracking database..."
	@"$(PYTHON_VENV)" update_readme_daily.py

# Generate blog index
blog-index: install-python
	@echo "Generating blog index..."
	@"$(PYTHON_VENV)" blog/generate_index.py

# Export API feeds
export-data: install-python
	@echo "Exporting API data feeds..."
	@"$(PYTHON_VENV)" export_data_feeds.py

# Run the full backend pipeline (similar to CI):
# multi-agent -> README -> DB -> blog index -> API feeds
backend-all: backend update-readme update-db blog-index export-data
	@echo "Backend pipeline completed."

# -------------------------------------------------------------------
# Daily Blog Generation (CrewAI + Ollama)
# -------------------------------------------------------------------

# Generate daily blog post with CrewAI multi-agent system
# This uses update_blog.sh which handles:
#  - Ollama setup and model download
#  - Blog post generation with CrewAI
#  - Blog index and API feed updates
update:
	@echo "🏆 Generating daily blog post with CrewAI..."
	@bash update_blog.sh

# -------------------------------------------------------------------
# Jekyll site (Minimal Mistakes)
# -------------------------------------------------------------------

# Build the Jekyll site into ./_site with production baseurl
build: install-jekyll
	@echo "Building Jekyll site (production baseurl: $(JEKYLL_BASEURL))..."
	@JEKYLL_ENV=production $(BUNDLE) exec $(JEKYLL) build --baseurl "$(JEKYLL_BASEURL)"

# Serve the Jekyll site locally WITHOUT baseurl (dev-friendly)
# Open: http://127.0.0.1:4000/
serve: install-jekyll
	@echo "Serving Jekyll site locally at / (no baseurl)..."
	@echo "Open: http://127.0.0.1:4000/"
	@JEKYLL_ENV=development $(BUNDLE) exec $(JEKYLL) serve --livereload --baseurl ""

# Serve the Jekyll site locally WITH production baseurl (for final check)
# Open: http://127.0.0.1:4000$(JEKYLL_BASEURL)/
serve-prod: install-jekyll
	@echo "Serving Jekyll site locally with baseurl $(JEKYLL_BASEURL)..."
	@echo "Open: http://127.0.0.1:4000$(JEKYLL_BASEURL)/"
	@JEKYLL_ENV=development $(BUNDLE) exec $(JEKYLL) serve --livereload --baseurl "$(JEKYLL_BASEURL)"

# Clean build artifacts
clean:
	@echo "Cleaning Jekyll build artifacts..."
	@rm -rf _site .jekyll-cache .sass-cache .bundle vendor

# -------------------------------------------------------------------
# Full local test: backend + Jekyll build
# -------------------------------------------------------------------
test: backend-all build
	@echo "✅ Full local test completed: backend pipeline + Jekyll build."
