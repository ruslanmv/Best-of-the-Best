"""
Custom tools for researching AI packages and trends
"""

import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

class PackageResearchTool:
    """Tool for researching trending AI packages"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def get_trending_packages(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Get trending packages from the repository data
        """
        # Read the existing data files
        packages_data = []

        # Load from research.json to get package information
        research_file = self.data_dir / "research.json"
        if research_file.exists():
            with open(research_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract packages mentioned in research
            for entry in data:
                for link in entry.get('links', []):
                    if link[0] == 'pypi':
                        package_name = link[1].rstrip('/').split('/')[-1]
                        packages_data.append({
                            'name': package_name,
                            'description': entry.get('description', ''),
                            'source': 'research'
                        })

        # Read README to extract trending packages
        readme_file = Path("README.md")
        if readme_file.exists():
            with open(readme_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract packages from the Packages section
            if "### Packages" in content:
                packages_section = content.split("### Packages")[1].split("###")[0]
                lines = packages_section.strip().split('\n')

                for line in lines[2:]:  # Skip table header
                    if '|' in line and line.strip():
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) >= 5:
                            package_name = parts[1]
                            if package_name and package_name != '---':
                                packages_data.append({
                                    'name': package_name,
                                    'downloads_last_month': parts[2],
                                    'total_downloads': parts[3],
                                    'source': 'readme'
                                })

        return packages_data[:top_n]

    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific package from PyPI
        """
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                info = data.get('info', {})

                return {
                    'name': info.get('name', package_name),
                    'version': info.get('version', 'unknown'),
                    'summary': info.get('summary', 'No summary available'),
                    'description': info.get('description', ''),
                    'author': info.get('author', 'Unknown'),
                    'home_page': info.get('home_page', ''),
                    'project_urls': info.get('project_urls', {}),
                    'requires_python': info.get('requires_python', ''),
                    'license': info.get('license', 'Not specified'),
                    'keywords': info.get('keywords', ''),
                    'classifiers': info.get('classifiers', [])
                }
        except Exception as e:
            print(f"Error fetching package info: {e}")

        return {'name': package_name, 'error': 'Could not fetch package information'}

    def get_github_info(self, repo_url: str) -> Dict[str, Any]:
        """
        Get GitHub repository information
        """
        try:
            # Extract owner and repo from URL
            parts = repo_url.replace('https://github.com/', '').split('/')
            if len(parts) >= 2:
                owner, repo = parts[0], parts[1]

                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                response = requests.get(api_url, timeout=10)

                if response.status_code == 200:
                    data = response.json()

                    return {
                        'stars': data.get('stargazers_count', 0),
                        'forks': data.get('forks_count', 0),
                        'open_issues': data.get('open_issues_count', 0),
                        'watchers': data.get('watchers_count', 0),
                        'language': data.get('language', 'Unknown'),
                        'created_at': data.get('created_at', ''),
                        'updated_at': data.get('updated_at', ''),
                        'description': data.get('description', '')
                    }
        except Exception as e:
            print(f"Error fetching GitHub info: {e}")

        return {'error': 'Could not fetch GitHub information'}


class WatsonXAnalysisTool:
    """Tool for analyzing package compatibility with IBM watsonx.ai"""

    @staticmethod
    def analyze_for_watsonx(package_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze how a package can integrate with watsonx.ai
        Returns potential integration points and use cases
        """
        analysis = {
            'integration_points': [],
            'use_cases': [],
            'compatibility_score': 0
        }

        package_name = package_info.get('name', '').lower()
        description = package_info.get('description', '').lower()
        summary = package_info.get('summary', '').lower()
        keywords = package_info.get('keywords', '').lower()

        combined_text = f"{package_name} {description} {summary} {keywords}"

        # Check for relevant keywords and patterns
        ml_keywords = ['machine learning', 'deep learning', 'neural network', 'ml', 'ai']
        data_keywords = ['data', 'preprocessing', 'etl', 'pipeline']
        nlp_keywords = ['nlp', 'language', 'text', 'llm', 'transformer']
        vision_keywords = ['vision', 'image', 'computer vision', 'cv']

        # Analyze integration potential
        if any(kw in combined_text for kw in ml_keywords):
            analysis['integration_points'].append('Model Training Enhancement')
            analysis['compatibility_score'] += 20

        if any(kw in combined_text for kw in data_keywords):
            analysis['integration_points'].append('Data Preprocessing Pipeline')
            analysis['compatibility_score'] += 15

        if any(kw in combined_text for kw in nlp_keywords):
            analysis['integration_points'].append('NLP Model Integration')
            analysis['use_cases'].append('Enhanced text processing with watsonx.ai foundation models')
            analysis['compatibility_score'] += 25

        if any(kw in combined_text for kw in vision_keywords):
            analysis['integration_points'].append('Computer Vision Pipeline')
            analysis['use_cases'].append('Image processing and analysis workflows')
            analysis['compatibility_score'] += 20

        # Check for specific package types
        if 'langchain' in package_name or 'llama' in package_name:
            analysis['use_cases'].append('LLM orchestration and prompt engineering')
            analysis['compatibility_score'] += 30

        if 'xgboost' in package_name or 'catboost' in package_name or 'lightgbm' in package_name:
            analysis['use_cases'].append('Gradient boosting for structured data in watsonx.ai')
            analysis['compatibility_score'] += 25

        return analysis
