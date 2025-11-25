# 🚀 Best of the Best AI - Blog & Data Platform

A beautiful, automated blog and data platform showcasing the top AI repositories, research papers, and Python packages, powered by GitHub Actions and deployed on GitHub Pages.

## 🌟 Features

### 📊 Live Data Dashboard
- **Real-time statistics** from README.md
- **Interactive tables** for repositories, papers, and packages
- **Beautiful UI** with gradient design and responsive layout
- **Daily automatic updates** via GitHub Actions

### 📡 Public API Endpoints
All data is available as JSON files for easy integration:

- **Main Data Feed**: `/api/data.json` - Complete dataset
- **Repositories**: `/api/repositories.json` - Top GitHub repos with stars
- **Papers**: `/api/papers.json` - Most cited research papers
- **Packages**: `/api/packages.json` - Top PyPI packages with downloads
- **RSS Feed**: `/api/feed.xml` - Subscribe for daily updates

### 📝 Blog System
- **AI-generated content** using CrewAI multi-agent system
- **Daily blog posts** about trending AI packages
- **Integration insights** for watsonx.ai and Watson Orchestrate
- **Markdown-based** with YAML frontmatter

### 🗄️ Historical Tracking
- **SQLite database** tracks evolution of metrics over time
- **100 MB size limit** with automatic pruning of old records
- **Timestamped snapshots** for trend analysis

## 🏗️ Architecture

```
blog/
├── index.html              # Main blog homepage
├── data.html              # Live data dashboard
├── _config.yml            # Jekyll/GitHub Pages config
├── api/                   # Public API endpoints
│   ├── data.json          # Complete dataset
│   ├── repositories.json  # GitHub repos
│   ├── papers.json        # Research papers
│   ├── packages.json      # PyPI packages
│   ├── feed.xml          # RSS feed
│   └── README.md         # API documentation
└── posts/                 # Blog posts
    ├── index.json         # Posts index
    └── *.md              # Individual posts

Scripts:
├── export_data_feeds.py   # Extracts README data → API files
├── update_readme_daily.py # Updates README & tracks in database
└── blog/generate_index.py # Generates blog posts index
```

## 🔄 Automated Workflows

### 1. Daily README Update (Midnight UTC)
**File**: `.github/workflows/daily-readme-update.yml`

1. Extracts data from README.md
2. Updates README header with current date
3. Stores snapshot in tracking database (data/tracking.db)
4. Exports to JSON/RSS feeds
5. Commits and pushes changes

### 2. Daily Blog Generation (9 AM UTC)
**File**: `.github/workflows/daily-blog.yml`

1. Runs CrewAI multi-agent system
2. Generates blog post about trending AI package
3. Updates blog posts index
4. Exports data feeds
5. Deploys to GitHub Pages (gh-pages branch)

## 📖 Usage

### Viewing the Blog
Visit: `https://ruslanmv.github.io/Best-of-the-Best/`

### Accessing the Data Dashboard
Navigate to: `/data.html` or click "📊 Live Data Dashboard" in the menu

### Using the API

#### JavaScript
```javascript
// Fetch all data
fetch('https://ruslanmv.github.io/Best-of-the-Best/api/data.json')
  .then(response => response.json())
  .then(data => {
    console.log('Repositories:', data.repositories);
    console.log('Papers:', data.papers);
    console.log('Packages:', data.packages);
    console.log('Last updated:', data.last_updated);
  });
```

#### Python
```python
import requests

# Get top repositories
response = requests.get('https://ruslanmv.github.io/Best-of-the-Best/api/repositories.json')
data = response.json()

for repo in data['repositories'][:10]:
    print(f"{repo['name']}: {repo['stars']:,} stars")
    print(f"  {repo['url']}")
```

#### cURL
```bash
# Download complete dataset
curl https://ruslanmv.github.io/Best-of-the-Best/api/data.json

# Get only packages
curl https://ruslanmv.github.io/Best-of-the-Best/api/packages.json

# Subscribe to RSS feed
curl https://ruslanmv.github.io/Best-of-the-Best/api/feed.xml
```

### RSS Feed
Subscribe to updates in your favorite RSS reader:
```
https://ruslanmv.github.io/Best-of-the-Best/api/feed.xml
```

## 🛠️ Development

### Running Scripts Locally

#### Export Data Feeds
```bash
python export_data_feeds.py
```
Generates JSON and RSS feeds in `blog/api/`

#### Update README & Database
```bash
python update_readme_daily.py
```
Updates README date and stores snapshot in database

#### Generate Blog Index
```bash
python blog/generate_index.py
```
Creates `blog/posts/index.json` from markdown files

### Testing Locally

1. **View the blog**:
   ```bash
   cd blog
   python -m http.server 8000
   ```
   Visit: http://localhost:8000

2. **Check API endpoints**:
   ```bash
   python export_data_feeds.py
   cd blog
   python -m http.server 8000
   ```
   Visit: http://localhost:8000/api/data.json

### Manual Workflow Trigger

Go to **Actions** → Select workflow → **Run workflow**

## 📊 Data Sources

- **GitHub Repositories**: GitHub API
- **Research Papers**: Semantic Scholar API, DOI links
- **PyPI Packages**: PyPI.org (data from README badges)
- **Historical Data**: Local SQLite database (data/tracking.db)

## 🎨 Customization

### Styling
Edit inline CSS in `blog/index.html` and `blog/data.html`

Color scheme:
- Primary: `#667eea` (purple-blue)
- Secondary: `#764ba2` (purple)
- Background: Linear gradient

### Blog Content
Posts are generated by CrewAI system in `multiagent_system/crew.py`

To customize:
- Edit agent roles in `multiagent_system/crew.py`
- Modify templates in blog post generation logic

### API Structure
Modify `export_data_feeds.py` to change JSON structure or add fields

## 🔧 Troubleshooting

### Workflow Failing
- Check requirements.txt dependencies
- Verify GitHub token permissions
- Ensure branch name follows pattern `claude/*`

### Data Not Updating
- Check if workflows are enabled in Actions tab
- Verify cron schedule in workflow files
- Check workflow logs for errors

### GitHub Pages Not Deploying
- Ensure gh-pages branch exists
- Check Pages settings in repository
- Verify `publish_dir: ./blog` in workflow

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## 📄 License

This project aggregates data from public sources. Please respect:
- GitHub API rate limits and ToS
- Semantic Scholar API guidelines
- PyPI usage policies

## 🙏 Acknowledgments

- **CrewAI**: Multi-agent system framework
- **Ollama**: Local LLM runtime
- **GitHub Actions**: Automation platform
- **GitHub Pages**: Free hosting

---

## 🔗 Links

- **Live Blog**: https://ruslanmv.github.io/Best-of-the-Best/
- **Data Dashboard**: https://ruslanmv.github.io/Best-of-the-Best/data.html
- **API**: https://ruslanmv.github.io/Best-of-the-Best/api/
- **GitHub Repo**: https://github.com/ruslanmv/Best-of-the-Best

---

**Last Updated**: 2024-11-25
**Status**: ✅ Active and maintained
