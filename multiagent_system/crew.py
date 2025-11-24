"""
Main Crew AI multi-agent system for daily AI package blog generation
"""

import os
import yaml
from datetime import datetime
from pathlib import Path
from crewai import Agent, Task, Crew, Process
from langchain_ollama import ChatOllama
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
        """Setup Ollama LLM"""
        return ChatOllama(
            model=self.model_name,
            base_url="http://localhost:11434",
            temperature=0.7
        )

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

        # Get trending packages for context
        trending_packages = self.research_tool.get_trending_packages(10)
        packages_context = "\n".join([
            f"- {pkg.get('name', 'Unknown')}: {pkg.get('description', 'No description')}"
            for pkg in trending_packages
        ])

        # Research Task
        research_config = self.tasks_config['research_task']
        research_task = Task(
            description=research_config['description'] + f"\n\nAvailable trending packages:\n{packages_context}",
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

        # Generate filename with today's date
        today = datetime.now()
        filename = f"{today.strftime('%Y-%m-%d')}-daily-package.md"
        filepath = blog_dir / filename

        # Add metadata header
        metadata = f"""---
date: {today.strftime('%Y-%m-%d')}
title: "Daily AI Package Highlight - {today.strftime('%B %d, %Y')}"
author: "AI Multi-Agent System"
tags: ["AI", "Machine Learning", "watsonx.ai", "Watson Orchestrate"]
---

"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(metadata + content)

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
