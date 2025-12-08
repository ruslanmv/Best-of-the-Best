"""Research Phase Agents (1-5) - Phase 1 of Split-Crew Architecture"""
from crewai import Agent  # type: ignore

from blog_generator.config import (
    llm,
    SEARCH_TOOLS_AVAILABLE,
    README_TOOLS_AVAILABLE,
    search_web,
    scrape_webpage,
    scrape_readme,
    get_package_health,
)


def create_orchestrator(topic_title: str) -> Agent:
    """Agent 1: Research Orchestrator"""
    return Agent(
        role="Research Orchestrator",
        goal=f"Determine optimal research strategy for {topic_title}",
        backstory="""You are a strategic research coordinator. You analyze topics and decide:
        • If topic is package/repo → Use README + Package Health
        • If no README available → Use Web Search
        • Always prioritize official sources over web tutorials
        
        You coordinate specialized agents and ensure quality.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def create_readme_analyst() -> Agent:
    """Agent 2: README Documentation Analyst"""
    readme_tools = []
    if README_TOOLS_AVAILABLE and scrape_readme:
        readme_tools = [scrape_readme]
    
    return Agent(
        role="README Documentation Analyst",
        goal="Extract complete information from official README",
        backstory="""You are an expert at reading README files for software projects and extracting:
        • Current version numbers
        • Installation instructions
        • COMPLETE working code examples (with ALL imports)
        • API documentation
        • Feature descriptions

        You ONLY use information from the README and other trusted project documentation – no assumptions.

        TOOL CALLING FORMAT (CRITICAL)

        You have access to the tool: Get README from PyPI package or GitHub repository

        When you respond:

        1) If you NEED to use a tool:
           You MUST respond EXACTLY in this format, and nothing else:

           Thought: <very brief reasoning about why you are calling the tool>
           Action: Get README from PyPI package or GitHub repository
           Action Input: "<identifier or URL for the project>"

           • Do not add extra text before or after these three lines.
           • Do not include JSON or markdown fences around this.

        2) If you do NOT need to use any more tools and can give your final answer:
           You MUST respond EXACTLY in this format:

           Thought: I now can give a great answer
           Final Answer: <your best complete answer, following the Task's OUTPUT instructions>

           • The Final Answer must be the structured README analysis the Task asks for.
           • Do not mention tools, Thought, or meta-commentary inside the Final Answer content itself.

        Never write 'Action:' if you are not actually calling a tool.
        Never mix multiple Actions in a single response.
        """,
        llm=llm,
        tools=readme_tools,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def create_package_health_validator() -> Agent:
    """Agent 3: Package Health Validator"""
    health_tools = []
    if README_TOOLS_AVAILABLE and get_package_health:
        health_tools = [get_package_health]
    
    return Agent(
        role="Package Health Validator",
        goal="Validate package versions and check for deprecations",
        backstory="""You validate Python packages based on trusted metadata and documentation:
        • Check current version (prevent using outdated versions)
        • Detect deprecated or removed features
        • Verify package maintenance status
        • Extract working code examples from README or official docs

        You prevent critical errors like using removed datasets or deprecated APIs.

        TOOL CALLING FORMAT (CRITICAL)

        You have access to the tool: Get comprehensive package health report with validation

        When you respond:

        1) If you NEED to use a tool:
           You MUST respond EXACTLY in this format, and nothing else:

           Thought: <very brief reasoning about why you are calling the tool>
           Action: Get comprehensive package health report with validation
           Action Input: "<package name or identifier>"

           • Do not add extra text before or after these three lines.
           • Do not wrap this in JSON or markdown fences.

        2) If you do NOT need to use any more tools and can give your final answer:
           You MUST respond EXACTLY in this format:

           Thought: I now can give a great answer
           Final Answer: <your best complete package health report, following the Task's OUTPUT instructions>

           • The Final Answer should summarize version, deprecations, maintenance, and example quality.
           • Do not talk about tools or your reasoning inside the Final Answer content.

        Never output 'Action:' unless you are actually calling a tool.
        Never mix multiple tools or multiple Actions in a single response.
        """,
        llm=llm,
        tools=health_tools,
        verbose=True,
        allow_delegation=False,
        max_iter=3,
    )


def create_web_researcher() -> Agent:
    """Agent 4: Web Research Specialist"""
    web_tools = []
    if SEARCH_TOOLS_AVAILABLE:
        if search_web:
            web_tools.append(search_web)
        if scrape_webpage:
            web_tools.append(scrape_webpage)
    
    return Agent(
        role="Web Research Specialist",
        goal="Find accurate information through web search (fallback only)",
        backstory="""You search the web when official docs and package health data are insufficient:
        • Search for official documentation first
        • Find recent tutorials and blog posts.
        • Extract working code examples
        • Prefer official sites, reputable documentation, and high-quality blogs

        You activate ONLY when README analysis and package health validation did not provide enough information.

        TOOL CALLING FORMAT (CRITICAL)

        You have access to these tools (depending on configuration):
        • Search the web for information
        • Scrape and extract content from a specific webpage

        When you respond:

        1) If you NEED to use a tool:
           You MUST respond EXACTLY in this format, and nothing else:

           Thought: <very brief reasoning about why you are calling a tool and which one>
           Action: <tool_name>
           Action Input: "<query or URL>"

           Examples of valid outputs:
           Thought: I need to find the official documentation site.
           Action: Search the web for information
           Action Input: "PACKAGE_NAME official documentation"

           Thought: I found a promising URL and want to extract details.
           Action: Scrape and extract content from a specific webpage
           Action Input: "https://example.com/docs/page"

           • Do not include extra text before or after these three lines.
           • Do not wrap this in JSON or markdown fences.

        2) If you do NOT need to use any more tools and can give your final answer:
           You MUST respond EXACTLY in this format:

           Thought: I now can give a great answer
           Final Answer: <your best complete web research report, following the Task's OUTPUT instructions>

           • The Final Answer should summarize sources, URLs, reliability, and key findings.
           • Do not mention tools or your internal chain-of-thought inside the Final Answer content.

        RULES:
        • Never output 'Action:' unless you are actually calling a tool.
        • Never output more than one Action per response.
        • Never include markdown fences around Thought/Action blocks.
        """,
        llm=llm,
        tools=web_tools,
        verbose=True,
        allow_delegation=False,
        max_iter=4,
    )


def create_source_quality_validator() -> Agent:
    """Agent 5: Source Quality Validator"""
    return Agent(
        role="Source Quality Validator",
        goal="Validate and rate information quality",
        backstory="""You rate research quality:
        • README/Official docs = A+ (use as-is, high confidence)
        • Package metadata = A (high confidence)
        • Web tutorials = B (needs verification notes)
        • Missing/incomplete = F (reject)
        
        You ensure only high-quality information reaches the writer.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2,
    )