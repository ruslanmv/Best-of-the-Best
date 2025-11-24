# 🚀 Quick Start Guide - Multi-Agent Blog System

Get your daily AI package blog up and running in 5 minutes!

## Prerequisites Checklist

- [ ] Python 3.11 or higher installed
- [ ] Git installed
- [ ] At least 8GB RAM available
- [ ] GitHub account (for deployment)

## Step 1: Install Ollama

### Linux/macOS
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Windows
Download and install from [ollama.com/download](https://ollama.com/download)

## Step 2: Pull the LLM Model

```bash
ollama pull llama3.2
```

This will download the llama3.2 model (~2GB). Wait for it to complete.

## Step 3: Install Python Dependencies

```bash
pip install -r requirements-multiagent.txt
```

## Step 4: Run the System

### Option A: Automated Script (Recommended)

```bash
./run_daily_blog.sh
```

This script handles everything automatically!

### Option B: Manual Steps

```bash
# Start Ollama (if not already running)
ollama serve &

# Run the multi-agent system
cd multiagent_system
python crew.py

# Generate blog index
cd ..
python blog/generate_index.py
```

## Step 5: View Your Blog

Open `blog/index.html` in your web browser:

```bash
# On macOS
open blog/index.html

# On Linux
xdg-open blog/index.html

# On Windows
start blog/index.html
```

## Step 6: Deploy to GitHub Pages

### First-time Setup

1. **Enable GitHub Pages:**
   - Go to your repository on GitHub
   - Settings → Pages
   - Source: "Deploy from a branch"
   - Branch: `gh-pages`
   - Save

2. **Configure Permissions:**
   - Settings → Actions → General
   - Workflow permissions: "Read and write permissions"
   - Check "Allow GitHub Actions to create and approve pull requests"

3. **Push Your Changes:**
   ```bash
   git add .
   git commit -m "🚀 Add multi-agent blog system"
   git push
   ```

4. **Trigger Workflow:**
   - Go to Actions tab
   - Click "Daily AI Package Blog Generation"
   - Click "Run workflow"
   - Select branch and run

5. **Access Your Live Blog:**
   Your blog will be live at:
   ```
   https://YOUR_USERNAME.github.io/Best-of-the-Best/
   ```

## Daily Automation

Once set up, the system runs automatically every day at 9:00 AM UTC!

You can also trigger it manually:
- Go to GitHub Actions tab
- Select the workflow
- Click "Run workflow"

## Troubleshooting

### "Ollama not found"
```bash
# Check if Ollama is installed
which ollama

# If not found, reinstall
curl -fsSL https://ollama.com/install.sh | sh
```

### "Model not found"
```bash
# List available models
ollama list

# Pull the model if missing
ollama pull llama3.2
```

### "Python package errors"
```bash
# Upgrade pip
pip install --upgrade pip

# Reinstall dependencies
pip install --force-reinstall -r requirements-multiagent.txt
```

### "GitHub Actions failing"
- Check Actions tab for detailed error logs
- Verify workflow permissions are set correctly
- Ensure secrets/tokens are configured if needed

## What Happens Daily?

1. **9:00 AM UTC**: GitHub Actions triggers
2. **Research**: Agent analyzes trending packages
3. **Analysis**: Evaluates watsonx.ai integration potential
4. **Writing**: Creates comprehensive blog post
5. **Publication**: Commits to repo and deploys to Pages

## Customization Quick Tips

### Change Schedule
Edit `.github/workflows/daily-blog.yml`:
```yaml
schedule:
  - cron: '0 14 * * *'  # 2:00 PM UTC instead
```

### Use Different Model
Edit `multiagent_system/crew.py`:
```python
crew = DailyBlogCrew(model_name="mistral")  # or "codellama", etc.
```

### Modify Agent Instructions
Edit files in `multiagent_system/config/`:
- `agents.yaml` - Agent roles and personas
- `tasks.yaml` - Task descriptions and outputs

## Next Steps

- 📖 Read [MULTIAGENT_README.md](MULTIAGENT_README.md) for detailed documentation
- 🎨 Customize `blog/index.html` to match your brand
- 🔧 Modify agent configurations for your specific needs
- 📊 Monitor your blog's performance via GitHub Pages insights

## Support

- 📚 Check [MULTIAGENT_README.md](MULTIAGENT_README.md) for detailed help
- 🐛 Report issues on GitHub
- 💬 Join discussions in repository Discussions tab

---

**You're all set! 🎉**

Your AI-powered blog is ready to generate daily insights about trending AI packages and their integration with watsonx.ai!
