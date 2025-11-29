# MCP Server for Best of the Best AI Data

## 🚀 Overview

This MCP (Model Context Protocol) server provides agentic AI systems with structured access to:
- **Top AI/ML GitHub repositories** with star counts
- **Most cited research papers** with citation metrics
- **Top PyPI packages** with download statistics
- **Historical trends** and analytics from the tracking database

## 🔧 Installation

### For Claude Desktop

1. **Locate your Claude Desktop config**:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Add the MCP server configuration**:

```json
{
  "mcpServers": {
    "best-of-the-best-ai": {
      "command": "python",
      "args": ["/absolute/path/to/Best-of-the-Best/mcp_server.py"],
      "description": "AI/ML data: repos, papers, packages with trends"
    }
  }
}
```

3. **Restart Claude Desktop**

### For Cline (VS Code Extension)

1. Open Cline settings in VS Code
2. Add to MCP servers:

```json
{
  "name": "best-of-the-best-ai",
  "command": "python",
  "args": ["mcp_server.py"],
  "cwd": "/path/to/Best-of-the-Best"
}
```

### For Other MCP Clients

Use the standard MCP configuration:

```json
{
  "command": "python",
  "args": ["mcp_server.py"],
  "cwd": "/path/to/Best-of-the-Best"
}
```

## 📚 Available Resources

The MCP server exposes these resources:

### Data Resources

| URI | Description |
|-----|-------------|
| `data://all` | Complete dataset (repositories, papers, packages) |
| `data://repositories` | Top GitHub repositories with stars |
| `data://papers` | Most cited research papers |
| `data://packages` | Top PyPI packages with downloads |
| `data://trends/repositories` | Historical star count trends |
| `data://trends/papers` | Historical citation trends |
| `data://trends/packages` | Historical download trends |

### Example Usage in Claude

```
Can you read data://repositories and tell me the top 5 AI repositories?
```

```
Show me the trend analysis from data://trends/repositories for langchain
```

## 🔧 Available Tools

The server provides these tools for querying and analysis:

### 1. `query_repositories`

Query repositories by name or stars:

```json
{
  "name_pattern": "llm",
  "min_stars": 10000,
  "limit": 5
}
```

### 2. `query_papers`

Find papers by topic or citations:

```json
{
  "name_pattern": "transformer",
  "min_citations": 1000,
  "limit": 10
}
```

### 3. `query_packages`

Search packages by name or downloads:

```json
{
  "name_pattern": "langchain",
  "min_downloads": 1000000,
  "limit": 5
}
```

### 4. `get_trend_analysis`

Analyze growth trends over time:

```json
{
  "type": "repository",
  "name": "ollama/ollama",
  "days": 30
}
```

## 💡 Usage Examples

### In Claude Desktop

Once configured, you can ask Claude:

```
Use the best-of-the-best-ai server to find all repositories
related to "llm" with more than 50,000 stars
```

```
Query the trend analysis for langchain package over the last 30 days
```

```
Show me the top 10 most cited papers about diffusion models
```

### Programmatic Access

```python
import json
import subprocess

# Call MCP server tool
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "query_repositories",
        "arguments": {
            "name_pattern": "llm",
            "min_stars": 10000,
            "limit": 5
        }
    }
}

# Send to MCP server via stdio
result = subprocess.run(
    ["python", "mcp_server.py"],
    input=json.dumps(request),
    capture_output=True,
    text=True
)

print(result.stdout)
```

## 🧪 Testing

Test the MCP server locally:

```bash
# Test mode - shows capabilities and available resources
python mcp_server.py --test
```

Expected output:
```
🚀 MCP Server Capabilities:
{
  "name": "best-of-the-best-ai",
  "version": "1.0.0",
  "capabilities": {
    "resources": true,
    "tools": true
  }
}

📚 Available Resources:
[
  {
    "uri": "data://repositories",
    "name": "Top AI Repositories",
    ...
  }
]

✅ MCP Server is ready!
```

## 📊 Data Format

### Repositories
```json
{
  "repositories": [
    {
      "name": "ollama/ollama",
      "stars": 118329,
      "url": "https://github.com/ollama/ollama"
    }
  ],
  "last_updated": "2024-11-25T13:00:00"
}
```

### Papers
```json
{
  "papers": [
    {
      "name": "Image segmentation",
      "citations": 39528,
      "url": "https://doi.org/10.1007/..."
    }
  ]
}
```

### Packages
```json
{
  "packages": [
    {
      "name": "langchain",
      "downloads_last_month": 33774884,
      "total_downloads": 143306111,
      "url": "https://pypi.org/project/langchain/"
    }
  ]
}
```

### Trend Analysis
```json
{
  "name": "ollama/ollama",
  "type": "repository",
  "period_days": 30,
  "data_points": [
    {"stars": 115000, "timestamp": "2024-10-26"},
    {"stars": 118329, "timestamp": "2024-11-25"}
  ],
  "analysis": {
    "start_stars": 115000,
    "end_stars": 118329,
    "growth": 3329,
    "growth_percentage": 2.89
  }
}
```

## 🔄 Data Updates

The MCP server reads from:
- **JSON feeds**: `blog/api/*.json` (updated daily by workflows)
- **SQLite database**: `data/tracking.db` (historical trends)

Data is automatically updated daily at:
- 00:00 UTC - README and database update
- 09:00 UTC - Blog generation and full data refresh

## 🛠️ Advanced Configuration

### Custom Data Directory

```json
{
  "command": "python",
  "args": ["mcp_server.py"],
  "env": {
    "DATA_DIR": "/custom/path/to/data",
    "API_DIR": "/custom/path/to/api"
  }
}
```

### Multiple Instances

You can run multiple instances with different configurations:

```json
{
  "mcpServers": {
    "ai-repos": {
      "command": "python",
      "args": ["mcp_server.py", "--filter=repositories"]
    },
    "ai-papers": {
      "command": "python",
      "args": ["mcp_server.py", "--filter=papers"]
    }
  }
}
```

## 🐛 Troubleshooting

### Server not starting

1. **Check Python path**:
   ```bash
   which python
   # Use the full path in config
   ```

2. **Test server manually**:
   ```bash
   python mcp_server.py --test
   ```

3. **Check data files exist**:
   ```bash
   ls blog/api/data.json
   ls data/tracking.db
   ```

### No data returned

1. **Ensure data feeds are generated**:
   ```bash
   python export_data_feeds.py
   ```

2. **Check file permissions**:
   ```bash
   chmod +r blog/api/*.json
   chmod +r data/tracking.db
   ```

### Tools not working

1. **Verify tool syntax** matches the inputSchema
2. **Check server logs** in Claude Desktop console
3. **Test tool directly**:
   ```bash
   echo '{"method":"tools/call","params":{"name":"query_repositories","arguments":{}}}' | python mcp_server.py
   ```

## 📖 Learn More

- **MCP Protocol**: https://modelcontextprotocol.io/
- **Claude Desktop**: https://claude.ai/download
- **GitHub Repo**: https://github.com/ruslanmv/Best-of-the-Best

## 🤝 Contributing

To add new tools or resources:

1. Edit `mcp_server.py`
2. Add tool definition to `list_tools()`
3. Implement handler in `call_tool()`
4. Test with `--test` flag
5. Update this README

## 📄 License

This MCP server provides access to aggregated public data from:
- GitHub API
- Semantic Scholar
- PyPI

Please respect rate limits and terms of service.

---

**Version**: 1.0.0
**Last Updated**: 2024-11-25
**Status**: ✅ Production Ready
