"""
Main Crew AI multi-agent system for daily AI package blog generation
"""

import os
import json
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew, Process
from llm_client import get_llm
from tools.package_research_tool import PackageResearchTool, WatsonXAnalysisTool


class DailyBlogCrew:
    """Multi-agent crew for generating daily AI package blog posts"""

    def __init__(self, model_name: str = "llama3.2"):
        """
        Initialize the crew with agents and tasks

        Args:
            model_name: Ollama model to use (default: llama3.2)
        """
        self.model_name = model_name
        self.config_dir = Path(__file__).parent / "config"
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.coverage_file = self.data_dir / "blog_coverage.json"

        self.llm = self._setup_llm()
        self.research_tool = PackageResearchTool()
        self.watsonx_tool = WatsonXAnalysisTool()

        # Load configurations
        self.agents_config = self._load_config("agents.yaml")
        self.tasks_config = self._load_config("tasks.yaml")

        # Initialize agents and tasks
        self.agents = self._create_agents()
        self.tasks = self._create_tasks()

    def _setup_llm(self):
        """Setup Ollama LLM with proper LiteLLM configuration"""
        return get_llm(model_name=self.model_name)

    def _load_config(self, filename: str) -> dict:
        """Load YAML configuration file"""
        config_path = self.config_dir / filename
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _create_agents(self) -> dict:
        """Create all agents based on configuration"""
        agents = {}

        # Research Agent
        research_config = self.agents_config['research_agent']
        agents['research'] = Agent(
            role=research_config['role'],
            goal=research_config['goal'],
            backstory=research_config['backstory'],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        # Analysis Agent
        analysis_config = self.agents_config['analysis_agent']
        agents['analysis'] = Agent(
            role=analysis_config['role'],
            goal=analysis_config['goal'],
            backstory=analysis_config['backstory'],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        # Writer Agent
        writer_config = self.agents_config['writer_agent']
        agents['writer'] = Agent(
            role=writer_config['role'],
            goal=writer_config['goal'],
            backstory=writer_config['backstory'],
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )

        return agents

    def _create_tasks(self) -> list:
        """Create all tasks based on configuration"""
        tasks = []

        # Get covered packages to avoid repetition
        covered_packages = self.get_covered_packages()
        print(f"📊 Already covered {len(covered_packages)} packages: {', '.join(covered_packages[:5])}{'...' if len(covered_packages) > 5 else ''}")

        # Get trending packages for context
        trending_packages = self.research_tool.get_trending_packages(20)

        # Filter out already covered packages
        uncovered_packages = [
            pkg for pkg in trending_packages
            if pkg.get('name', '').lower() not in covered_packages
        ]

        if not uncovered_packages:
            print("⚠️  All trending packages already covered, using all packages")
            uncovered_packages = trending_packages

        print(f"✨ Found {len(uncovered_packages)} uncovered packages")

        packages_context = "\n".join([
            f"- {pkg.get('name', 'Unknown')}: {pkg.get('description', 'No description')}"
            for pkg in uncovered_packages[:10]
        ])

        # Research Task
        research_config = self.tasks_config['research_task']

        # Add context about covered packages
        coverage_note = f"\n\n**IMPORTANT**: The following packages have already been covered in previous blog posts: {', '.join(covered_packages[:10]) if covered_packages else 'None'}. Please select a DIFFERENT package from the list below."

        research_task = Task(
            description=research_config['description'] + coverage_note + f"\n\nAvailable uncovered trending packages (SELECT ONE FROM THIS LIST):\n{packages_context}",
            expected_output=research_config['expected_output'],
            agent=self.agents['research']
        )
        tasks.append(research_task)

        # Analysis Task
        analysis_config = self.tasks_config['analysis_task']
        analysis_task = Task(
            description=analysis_config['description'],
            expected_output=analysis_config['expected_output'],
            agent=self.agents['analysis'],
            context=[research_task]
        )
        tasks.append(analysis_task)

        # Writing Task
        writing_config = self.tasks_config['writing_task']
        writing_task = Task(
            description=writing_config['description'],
            expected_output=writing_config['expected_output'],
            agent=self.agents['writer'],
            context=[research_task, analysis_task]
        )
        tasks.append(writing_task)

        return tasks

    def load_coverage(self) -> List[Dict[str, Any]]:
        """Load blog coverage history"""
        if not self.coverage_file.exists():
            return []

        try:
            with self.coverage_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, Exception) as e:
            print(f"⚠️  Error loading coverage file: {e}")
            return []

    def save_coverage(self, entries: List[Dict[str, Any]]) -> None:
        """Save blog coverage history"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.coverage_file.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(entries, f, indent=2)
        tmp.replace(self.coverage_file)

    def get_covered_packages(self) -> List[str]:
        """Get list of already covered package names"""
        coverage = self.load_coverage()
        return [entry["id"] for entry in coverage if entry.get("kind") == "package"]

    def extract_package_name(self, content: str) -> Optional[str]:
        """Extract package name from blog content"""
        # Try to find package name in various ways
        lines = content.split('\n')

        # Method 1: Look for "# Package Name" or "## Package Name" in first few lines
        for line in lines[:20]:
            if line.startswith('#'):
                # Extract potential package name
                title = line.lstrip('#').strip()
                # Remove common prefixes
                for prefix in ["Daily AI Package:", "Package Highlight:", "Featured Package:", "Spotlight:"]:
                    if title.startswith(prefix):
                        title = title[len(prefix):].strip()
                # Check if it looks like a package name (lowercase, may have hyphens)
                title_lower = title.lower()
                words = title_lower.split()
                if words and len(words[0]) > 2:
                    # Take first word as potential package name
                    pkg = words[0].strip('`:*_')
                    if pkg and not any(c in pkg for c in [' ', '.']):
                        return pkg

        # Method 2: Look for installation command: pip install <package>
        pip_pattern = r'pip\s+install\s+([a-zA-Z0-9_-]+)'
        match = re.search(pip_pattern, content)
        if match:
            return match.group(1).lower()

        # Method 3: Look for PyPI references
        pypi_pattern = r'pypi\.org/project/([a-zA-Z0-9_-]+)'
        match = re.search(pypi_pattern, content)
        if match:
            return match.group(1).lower()

        # Method 4: Look for import statements
        import_pattern = r'^\s*import\s+([a-zA-Z0-9_]+)|^\s*from\s+([a-zA-Z0-9_]+)\s+import'
        for line in lines[:100]:
            match = re.search(import_pattern, line)
            if match:
                pkg = match.group(1) or match.group(2)
                if pkg and pkg not in ['os', 'sys', 'json', 'numpy', 'pandas']:  # Skip stdlib
                    return pkg.lower()

        return None

    def run(self) -> str:
        """Execute the crew and return the blog post"""
        crew = Crew(
            agents=list(self.agents.values()),
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True
        )

        result = crew.kickoff()
        return result

    def save_blog_post(self, content: str) -> str:
        """Save the generated blog post to a file"""
        blog_dir = Path("blog/posts")
        blog_dir.mkdir(parents=True, exist_ok=True)

        # Extract package name from content
        package_name = self.extract_package_name(content)
        if not package_name:
            # Fallback: use a generic name
            package_name = "featured"
            print("⚠️  Could not extract package name from content, using 'featured'")
        else:
            print(f"📦 Detected package: {package_name}")

        # Generate filename with today's date and package name
        today = datetime.now()
        filename = f"{today.strftime('%Y-%m-%d')}-package-{package_name}.md"

        # Check if file exists (avoid overwriting)
        filepath = blog_dir / filename
        counter = 1
        while filepath.exists():
            filename = f"{today.strftime('%Y-%m-%d')}-package-{package_name}-v{counter}.md"
            filepath = blog_dir / filename
            counter += 1

        # Add metadata header
        metadata = f"""---
date: {today.strftime('%Y-%m-%d')}
title: "Daily AI Package Highlight - {package_name.title()} - {today.strftime('%B %d, %Y')}"
author: "AI Multi-Agent System"
tags: ["AI", "Machine Learning", "watsonx.ai", "Watson Orchestrate", "{package_name}"]
topic_kind: "package"
topic_id: "{package_name}"
topic_version: 1
---

"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(metadata + content)

        # Record coverage
        coverage = self.load_coverage()
        coverage.append({
            "kind": "package",
            "id": package_name,
            "version": 1,
            "date": today.strftime('%Y-%m-%d'),
            "filename": filename
        })
        self.save_coverage(coverage)
        print(f"📝 Updated coverage tracking")

        print(f"\n✅ Blog post saved to: {filepath}")
        return str(filepath)


def main():
    """Main entry point"""
    print("🚀 Starting Daily AI Package Blog Generation...")
    print("=" * 60)

    # Initialize the crew
    crew = DailyBlogCrew(model_name="llama3.2")

    # Run the crew
    print("\n📊 Running multi-agent research and analysis...")
    result = crew.run()

    # Save the blog post
    print("\n💾 Saving blog post...")
    filepath = crew.save_blog_post(str(result))

    print("\n" + "=" * 60)
    print("✨ Daily blog generation completed successfully!")
    print(f"📝 Blog post location: {filepath}")


if __name__ == "__main__":
    main()
