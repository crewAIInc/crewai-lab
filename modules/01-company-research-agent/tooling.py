from crewai import Agent
from crewai_tools import BaseTool, SerperDevTool
from dotenv import load_dotenv

from lab_utils.mcp import build_firecrawl_mcp

load_dotenv()



class ExampleCustomTool(BaseTool):
    name = "example_custom_tool"
    description = "A custom tool that returns a canned response useful for demonstrating tool extension."

    def _run(self, query: str) -> str:
        # Custom logic goes here; here we just return a simple message.
        return f"ExampleCustomTool received query: {query!r} and responds with a canned answer."


# 3 ways to leverage tools:
agent =Agent(
    role="Company Research Agent",
    goal="Research the company and return a summary of the company",
    backstory="You are a company research agent that can research the company and return a summary of the company",
    tools=[SerperDevTool()],
    mcps=[
        build_firecrawl_mcp(
            allowed_tools=["firecrawl_search"],
        )
    ],
    apps=['github']
)