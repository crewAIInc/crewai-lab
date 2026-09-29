from crewai import Agent
from dotenv import load_dotenv

from lab_utils.mcp import build_firecrawl_mcp

load_dotenv()


# 3 ways to leverage tools:
agent =Agent(
    role="Company Research Agent",
    goal="Research the company and return a summary of the company",
    backstory=(
        "You are a company research agent that can research the company and return "
        "a summary of the company"
    ),
    # tools=[SerperDevTool()],
    mcps=[
        build_firecrawl_mcp(
            allowed_tools=["firecrawl_search"],
        )
    ],
    # apps=['github/github_update_issue']
)

print(agent.kickoff("Research Docusign and their q2 company updates"))