"""Complete the TODOs, then run from the repository root."""

from crewai import Agent
from crewai.flow import Flow, start

from lab_utils.mcp import build_firecrawl_mcp
from lab_utils.models import CompanyResearchBrief
from lab_utils.settings import LAB_MODEL


class CompanyResearchFlow(Flow):
    @start()
    def research(self) -> CompanyResearchBrief | str:
        agent = Agent(
            role="TODO: name the research specialist",
            goal="TODO: define a grounded company-research outcome",
            backstory="TODO: forbid invented sources and move unknowns to open questions",
            llm=LAB_MODEL,
            mcps=[
                build_firecrawl_mcp(
                    allowed_tools=["firecrawl_search"],
                )
            ],
            verbose=True,
        )
        result = agent.kickoff(
            "Research CrewAI and their goals for the year. Prefer primary sources, cite URLs, and put "
            "unverified facts in open_questions.",
            response_format=CompanyResearchBrief,
        )
        return result.pydantic or result.raw


def main() -> None:
    print(CompanyResearchFlow().kickoff())


if __name__ == "__main__":
    main()
