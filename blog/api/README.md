# Best of the Best AI - Data API

## Available Endpoints

All endpoints are available as static JSON files hosted on GitHub Pages.

Base URL: `https://ruslanmv.github.io/Best-of-the-Best/api/`

### 📊 Main Data Feed
- **URL**: `/api/data.json`
- **Description**: Complete dataset with all repositories, papers, and packages
- **Format**: JSON
- **Example**: `https://ruslanmv.github.io/Best-of-the-Best/api/data.json`

### ⭐ Repositories
- **URL**: `/api/repositories.json`
- **Description**: Top GitHub repositories with star counts
- **Format**: JSON
- **Fields**: `name`, `stars`, `url`

### 📄 Papers
- **URL**: `/api/papers.json`
- **Description**: Most cited research papers
- **Format**: JSON
- **Fields**: `name`, `citations`, `url`

### 📦 Packages
- **URL**: `/api/packages.json`
- **Description**: Top PyPI packages with download statistics
- **Format**: JSON
- **Fields**: `name`, `downloads_last_month`, `total_downloads`, `url`

### 📰 RSS Feed
- **URL**: `/api/feed.xml`
- **Description**: RSS feed for daily updates
- **Format**: RSS 2.0
- **Subscribe**: Add to your RSS reader

## Usage Examples

### JavaScript (Fetch API)
```javascript
// Fetch all data
fetch('https://ruslanmv.github.io/Best-of-the-Best/api/data.json')
  .then(response => response.json())
  .then(data => {
    console.log('Repositories:', data.repositories);
    console.log('Papers:', data.papers);
    console.log('Packages:', data.packages);
  });
```

### Python
```python
import requests

# Fetch repositories
response = requests.get('https://ruslanmv.github.io/Best-of-the-Best/api/repositories.json')
data = response.json()

for repo in data['repositories']:
    print(f"{repo['name']}: {repo['stars']} stars")
```

### cURL
```bash
# Download all data
curl https://ruslanmv.github.io/Best-of-the-Best/api/data.json

# Download specific category
curl https://ruslanmv.github.io/Best-of-the-Best/api/repositories.json
```

## Update Frequency

- Data is updated **daily** via GitHub Actions
- Last update timestamp is included in all JSON responses
- RSS feed reflects the latest changes

## License

Data is aggregated from public sources:
- GitHub API (repositories)
- Semantic Scholar (papers)
- PyPI (packages)

Please respect rate limits and terms of service of the original data sources.

## Questions or Issues?

Visit our [GitHub repository](https://github.com/ruslanmv/Best-of-the-Best) to report issues or request features.

---

**Generated**: 2025-11-29 21:56:41 UTC
