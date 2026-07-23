"""Starter: complete deterministic TriageX state transitions."""

from crewai.flow import Flow, listen, start
from pydantic import BaseModel, Field

from lab_utils.agents import build_triage_ticket_agent
from lab_utils.models import SupportCase
from lab_utils.settings import LINEAR_TEAM


class LabState(BaseModel):
    case: SupportCase = Field(default_factory=SupportCase)
    queue: str = "unassigned"
    priority: str = "P2"
    sync_to_linear: bool = False
    linear_issue: str | None = None


class LabFlow(Flow[LabState]):
    @start()
    def normalize(self) -> None:
        # TODO 1: strip and lowercase self.state.case.severity.
        pass

    @listen(normalize)
    def triage(self) -> None:
        # TODO 2: send critical cases to incident_response; otherwise support.
        # TODO 3: assign P0 to critical cases; otherwise P2.
        pass

    @listen(triage)
    def create_linear_ticket(self) -> str:
        if not self.state.sync_to_linear:
            return "Linear sync skipped"
        if not LINEAR_TEAM:
            raise RuntimeError("Set LINEAR_TEAM to a Linear team name, key, or ID.")

        # TODO 4: keep the Flow's deterministic decision and ask the MCP-enabled
        # Agent to create exactly one issue. Never let the Agent re-triage it.
        result = build_triage_ticket_agent().kickoff(
            "Create exactly one new Linear issue using save_issue. Omit id, call the tool "
            f"once, and use team {LINEAR_TEAM!r}.\n\n"
            f"Title: [{self.state.priority}] {self.state.case.case_id}: "
            f"{self.state.case.summary}\n"
            f"Description: Routed to {self.state.queue} from {self.state.case.source}."
        )
        self.state.linear_issue = result.raw
        return result.raw

    @listen(create_linear_ticket)
    def summarize(self) -> str:
        return f"{self.state.case.case_id}: {self.state.queue} ({self.state.priority})"


if __name__ == "__main__":
    result = LabFlow().kickoff(
        inputs={
            "case": {
                "case_id": "CASE-1042",
                "source": "aws",
                "account_id": "ACC-88",
                "severity": " Critical ",
                "summary": "Production outage during document submission",
            },
            # Flip to True only after adding LINEAR_API_KEY and LINEAR_TEAM.
            "sync_to_linear": False,
        }
    )
    print(result)
