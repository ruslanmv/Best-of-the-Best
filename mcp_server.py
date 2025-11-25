#!/usr/bin/env python3
"""
MCP (Model Context Protocol) Server for Best of the Best AI Data.
Provides structured data access for agentic AI systems.

This server exposes:
- Repository statistics
- Paper citations
- Package download data
- Historical trends from tracking database

Compatible with Claude Desktop, Cline, and other MCP-compatible agents.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import sys

# MCP Server implementation
class MCPServer:
    """MCP Server for AI Best of the Best data."""

    def __init__(self, data_dir: Path = Path("data"), blog_api_dir: Path = Path("blog/api")):
        self.data_dir = data_dir
        self.blog_api_dir = blog_api_dir
        self.db_path = data_dir / "tracking.db"

    def get_capabilities(self) -> Dict[str, Any]:
        """Return server capabilities."""
        return {
            "name": "best-of-the-best-ai",
            "version": "1.0.0",
            "description": "MCP server providing AI/ML repository, paper, and package data",
            "capabilities": {
                "resources": True,
                "tools": True,
                "prompts": False
            }
        }

    def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources."""
        return [
            {
                "uri": "data://repositories",
                "name": "Top AI Repositories",
                "description": "GitHub repositories with star counts",
                "mimeType": "application/json"
            },
            {
                "uri": "data://papers",
                "name": "Top Research Papers",
                "description": "Most cited AI/ML research papers",
                "mimeType": "application/json"
            },
            {
                "uri": "data://packages",
                "name": "Top PyPI Packages",
                "description": "Most downloaded AI/ML Python packages",
                "mimeType": "application/json"
            },
            {
                "uri": "data://all",
                "name": "Complete Dataset",
                "description": "All repositories, papers, and packages",
                "mimeType": "application/json"
            },
            {
                "uri": "data://trends/repositories",
                "name": "Repository Trends",
                "description": "Historical star count trends",
                "mimeType": "application/json"
            },
            {
                "uri": "data://trends/papers",
                "name": "Paper Citation Trends",
                "description": "Historical citation count trends",
                "mimeType": "application/json"
            },
            {
                "uri": "data://trends/packages",
                "name": "Package Download Trends",
                "description": "Historical download trends",
                "mimeType": "application/json"
            }
        ]

    def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a specific resource."""
        if uri == "data://repositories":
            return self._load_json_feed("repositories.json")

        elif uri == "data://papers":
            return self._load_json_feed("papers.json")

        elif uri == "data://packages":
            return self._load_json_feed("packages.json")

        elif uri == "data://all":
            return self._load_json_feed("data.json")

        elif uri == "data://trends/repositories":
            return self._get_repository_trends()

        elif uri == "data://trends/papers":
            return self._get_paper_trends()

        elif uri == "data://trends/packages":
            return self._get_package_trends()

        else:
            return {"error": f"Unknown resource: {uri}"}

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools."""
        return [
            {
                "name": "query_repositories",
                "description": "Query repositories by name or minimum stars",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name_pattern": {
                            "type": "string",
                            "description": "Filter by name pattern (case-insensitive)"
                        },
                        "min_stars": {
                            "type": "integer",
                            "description": "Minimum star count"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    }
                }
            },
            {
                "name": "query_papers",
                "description": "Query papers by name or minimum citations",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name_pattern": {
                            "type": "string",
                            "description": "Filter by name pattern (case-insensitive)"
                        },
                        "min_citations": {
                            "type": "integer",
                            "description": "Minimum citation count"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    }
                }
            },
            {
                "name": "query_packages",
                "description": "Query PyPI packages by name or downloads",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name_pattern": {
                            "type": "string",
                            "description": "Filter by package name (case-insensitive)"
                        },
                        "min_downloads": {
                            "type": "integer",
                            "description": "Minimum monthly downloads"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 10
                        }
                    }
                }
            },
            {
                "name": "get_trend_analysis",
                "description": "Get trend analysis for a specific item over time",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["repository", "paper", "package"],
                            "description": "Type of item to analyze"
                        },
                        "name": {
                            "type": "string",
                            "description": "Name of the item"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to analyze",
                            "default": 30
                        }
                    },
                    "required": ["type", "name"]
                }
            }
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool."""
        if name == "query_repositories":
            return self._query_repositories(**arguments)

        elif name == "query_papers":
            return self._query_papers(**arguments)

        elif name == "query_packages":
            return self._query_packages(**arguments)

        elif name == "get_trend_analysis":
            return self._get_trend_analysis(**arguments)

        else:
            return {"error": f"Unknown tool: {name}"}

    # Private helper methods

    def _load_json_feed(self, filename: str) -> Dict[str, Any]:
        """Load data from JSON feed file."""
        file_path = self.blog_api_dir / filename
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"error": f"File not found: {filename}"}

    def _query_repositories(self, name_pattern: Optional[str] = None,
                           min_stars: Optional[int] = None,
                           limit: int = 10) -> Dict[str, Any]:
        """Query repositories with filters."""
        data = self._load_json_feed("repositories.json")
        if "error" in data:
            return data

        repos = data.get("repositories", [])

        # Apply filters
        if name_pattern:
            repos = [r for r in repos if name_pattern.lower() in r['name'].lower()]

        if min_stars:
            repos = [r for r in repos if r['stars'] >= min_stars]

        # Sort by stars descending
        repos = sorted(repos, key=lambda x: x['stars'], reverse=True)

        return {
            "repositories": repos[:limit],
            "total_count": len(repos),
            "filters_applied": {
                "name_pattern": name_pattern,
                "min_stars": min_stars,
                "limit": limit
            }
        }

    def _query_papers(self, name_pattern: Optional[str] = None,
                     min_citations: Optional[int] = None,
                     limit: int = 10) -> Dict[str, Any]:
        """Query papers with filters."""
        data = self._load_json_feed("papers.json")
        if "error" in data:
            return data

        papers = data.get("papers", [])

        # Apply filters
        if name_pattern:
            papers = [p for p in papers if name_pattern.lower() in p['name'].lower()]

        if min_citations:
            papers = [p for p in papers if p['citations'] >= min_citations]

        # Sort by citations descending
        papers = sorted(papers, key=lambda x: x['citations'], reverse=True)

        return {
            "papers": papers[:limit],
            "total_count": len(papers),
            "filters_applied": {
                "name_pattern": name_pattern,
                "min_citations": min_citations,
                "limit": limit
            }
        }

    def _query_packages(self, name_pattern: Optional[str] = None,
                       min_downloads: Optional[int] = None,
                       limit: int = 10) -> Dict[str, Any]:
        """Query packages with filters."""
        data = self._load_json_feed("packages.json")
        if "error" in data:
            return data

        packages = data.get("packages", [])

        # Apply filters
        if name_pattern:
            packages = [p for p in packages if name_pattern.lower() in p['name'].lower()]

        if min_downloads:
            packages = [p for p in packages if p['downloads_last_month'] >= min_downloads]

        # Sort by monthly downloads descending
        packages = sorted(packages, key=lambda x: x['downloads_last_month'], reverse=True)

        return {
            "packages": packages[:limit],
            "total_count": len(packages),
            "filters_applied": {
                "name_pattern": name_pattern,
                "min_downloads": min_downloads,
                "limit": limit
            }
        }

    def _get_repository_trends(self) -> Dict[str, Any]:
        """Get repository trends from database."""
        if not self.db_path.exists():
            return {"error": "Tracking database not found"}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT repo_name, stars, timestamp
                FROM repository_stats
                ORDER BY timestamp DESC
                LIMIT 100
            """)

            trends = {}
            for row in cursor.fetchall():
                repo_name, stars, timestamp = row
                if repo_name not in trends:
                    trends[repo_name] = []
                trends[repo_name].append({
                    "stars": stars,
                    "timestamp": timestamp
                })

            conn.close()

            return {"repository_trends": trends}

        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

    def _get_paper_trends(self) -> Dict[str, Any]:
        """Get paper citation trends from database."""
        if not self.db_path.exists():
            return {"error": "Tracking database not found"}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT paper_name, citations, timestamp
                FROM paper_stats
                ORDER BY timestamp DESC
                LIMIT 100
            """)

            trends = {}
            for row in cursor.fetchall():
                paper_name, citations, timestamp = row
                if paper_name not in trends:
                    trends[paper_name] = []
                trends[paper_name].append({
                    "citations": citations,
                    "timestamp": timestamp
                })

            conn.close()

            return {"paper_trends": trends}

        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

    def _get_package_trends(self) -> Dict[str, Any]:
        """Get package download trends from database."""
        if not self.db_path.exists():
            return {"error": "Tracking database not found"}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT package_name, downloads_last_month, total_downloads, timestamp
                FROM package_stats
                ORDER BY timestamp DESC
                LIMIT 100
            """)

            trends = {}
            for row in cursor.fetchall():
                package_name, monthly, total, timestamp = row
                if package_name not in trends:
                    trends[package_name] = []
                trends[package_name].append({
                    "downloads_last_month": monthly,
                    "total_downloads": total,
                    "timestamp": timestamp
                })

            conn.close()

            return {"package_trends": trends}

        except Exception as e:
            return {"error": f"Database error: {str(e)}"}

    def _get_trend_analysis(self, type: str, name: str, days: int = 30) -> Dict[str, Any]:
        """Get detailed trend analysis for a specific item."""
        if not self.db_path.exists():
            return {"error": "Tracking database not found"}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if type == "repository":
                cursor.execute("""
                    SELECT stars, timestamp
                    FROM repository_stats
                    WHERE repo_name = ?
                    AND timestamp >= datetime('now', '-' || ? || ' days')
                    ORDER BY timestamp ASC
                """, (name, days))

                data_points = [{"stars": row[0], "timestamp": row[1]} for row in cursor.fetchall()]

                if len(data_points) >= 2:
                    growth = data_points[-1]["stars"] - data_points[0]["stars"]
                    growth_pct = (growth / data_points[0]["stars"] * 100) if data_points[0]["stars"] > 0 else 0

                    return {
                        "name": name,
                        "type": type,
                        "period_days": days,
                        "data_points": data_points,
                        "analysis": {
                            "start_stars": data_points[0]["stars"],
                            "end_stars": data_points[-1]["stars"],
                            "growth": growth,
                            "growth_percentage": round(growth_pct, 2)
                        }
                    }

            conn.close()
            return {"error": f"No trend data found for {name}"}

        except Exception as e:
            return {"error": f"Database error: {str(e)}"}


def main():
    """Run MCP server in stdio mode."""
    server = MCPServer()

    print(json.dumps({
        "jsonrpc": "2.0",
        "result": server.get_capabilities()
    }), flush=True)

    # Simple stdio server loop
    for line in sys.stdin:
        try:
            request = json.loads(line)
            method = request.get("method")
            params = request.get("params", {})

            if method == "resources/list":
                result = server.list_resources()
            elif method == "resources/read":
                result = server.read_resource(params.get("uri"))
            elif method == "tools/list":
                result = server.list_tools()
            elif method == "tools/call":
                result = server.call_tool(params.get("name"), params.get("arguments", {}))
            else:
                result = {"error": f"Unknown method: {method}"}

            response = {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": result
            }

            print(json.dumps(response), flush=True)

        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)}
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Test mode - demonstrate capabilities
        server = MCPServer()
        print("🚀 MCP Server Capabilities:")
        print(json.dumps(server.get_capabilities(), indent=2))

        print("\n📚 Available Resources:")
        print(json.dumps(server.list_resources(), indent=2))

        print("\n🔧 Available Tools:")
        print(json.dumps(server.list_tools(), indent=2))

        print("\n✅ MCP Server is ready!")
    else:
        # Run in stdio mode for actual MCP communication
        main()
