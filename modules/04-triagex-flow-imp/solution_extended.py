"""Extended solution for module 02: @router branches, @human_feedback, and or_ fan-in."""

from __future__ import annotations

from crewai.flow import (
    Flow,
    HumanFeedbackResult,
    human_feedback,
    listen,
    or_,
    router,
    start,
)
from pydantic import BaseModel, Field

from lab_utils.agents import build_triage_ticket_agent
from lab_utils.models import SupportCase
from lab_utils.settings import LAB_MODEL, LINEAR_TEAM


class ExtendedTriageState(BaseModel):
    """TriageX state plus the review outcome fields the extended pipeline adds."""

    case: SupportCase = Field(default_factory=SupportCase)
    queue: str = "unassigned"
    priority: str = "P2"
    reasons: list[str] = Field(default_factory=list)
    sync_to_linear: bool = False
    linear_issue: str | None = None
    disposition: str = "pending"
    reviewer_note: str = ""


def dispatch_route(priority: str) -> str:
    """Deterministic branch label for the router: only P0 needs a human gate."""
    return "INCIDENT" if priority == "P0" else "STANDARD"


class TriageXExtendedFlow(Flow[ExtendedTriageState]):
    """TriageX with named branches, a human approval gate, and fan-in.

    Extends the module 02 linear pipeline with three Flow features:

    - ``@router``: triage fans out to an INCIDENT or STANDARD path, so the
      branches run genuinely different steps instead of sharing one.
    - ``@human_feedback``: P0 incidents pause for reviewer approval before any
      Linear write. The LLM maps the reviewer's freeform reply onto one of the
      ``emit`` labels; an unmappable reply falls back to ``default_outcome``.
    - ``or_``: one summarize step re-converges whichever branch actually ran.

    To keep state across restarts, stack ``@persist`` above the class (SQLite
    by default) and resume a run with ``kickoff(inputs={"id": <state uuid>})``.
    """

    @start()
    def normalize(self) -> str:
        self.state.case.source = self.state.case.source.strip().casefold()
        self.state.case.severity = self.state.case.severity.strip().casefold()
        self.state.case.customer_tier = self.state.case.customer_tier.strip().casefold()
        self.state.case.summary = self.state.case.summary.strip()
        return self.state.case.case_id

    @listen(normalize)
    def triage(self) -> str:
        summary = self.state.case.summary.casefold()
        if self.state.case.severity == "critical" or any(
            term in summary for term in ("outage", "security incident")
        ):
            self.state.queue = "incident_response"
            self.state.priority = "P0"
            self.state.reasons.append("critical impact signal")
        elif self.state.case.customer_tier == "strategic" and "renewal" in summary:
            self.state.queue = "account_escalation"
            self.state.priority = "P1"
            self.state.reasons.append("strategic account renewal signal")
        else:
            self.state.queue = "support"
            self.state.priority = "P2"
            self.state.reasons.append("standard support path")
        return self.state.queue

    @router(triage)
    def dispatch(self) -> str:
        """Return an event label; @listen("LABEL") methods subscribe to it."""
        return dispatch_route(self.state.priority)

    @listen("STANDARD")
    def queue_for_support(self) -> str:
        """Non-incidents proceed without a human in the loop."""
        self.state.disposition = "queued"
        return f"queued for {self.state.queue} without human review"

    @listen("INCIDENT")
    @human_feedback(
        message="A P0 incident is about to be published to Linear. Approve or reject:",
        emit=["approved", "rejected"],
        llm=LAB_MODEL,
        default_outcome="rejected",
    )
    def review_incident(self) -> str:
        """Show the reviewer the fixed triage decision, not a model's opinion."""
        return (
            f"CASE {self.state.case.case_id}: {self.state.case.summary}\n"
            f"Queue: {self.state.queue} | Priority: {self.state.priority}\n"
            f"Reasons: {', '.join(self.state.reasons)}"
        )

    @listen("approved")
    def publish_incident(self, review: HumanFeedbackResult) -> str:
        """Only a human-approved incident may reach the Linear write path."""
        self.state.disposition = "approved"
        self.state.reviewer_note = review.feedback or ""
        if not self.state.sync_to_linear:
            return "approved; Linear sync skipped (enable with --sync-linear)"
        if not LINEAR_TEAM:
            raise RuntimeError("Set LINEAR_TEAM to a Linear team name, key, or ID.")

        result = build_triage_ticket_agent().kickoff(
            "Create exactly one new Linear issue using save_issue. Omit the id argument so "
            "the operation creates rather than updates. Do not call the tool more than once. "
            f"Use team exactly as provided: {LINEAR_TEAM}. Set Linear priority to 1. "
            "Return the created issue identifier and URL.\n\n"
            f"TITLE: [{self.state.priority}] {self.state.case.case_id}: "
            f"{self.state.case.summary}\n"
            "DESCRIPTION (synthetic workshop data):\n"
            f"- Routed queue: {self.state.queue}\n"
            f"- Triage reason: {', '.join(self.state.reasons)}\n"
            f"- Reviewer note: {self.state.reviewer_note or 'none'}"
        )
        self.state.linear_issue = result.raw
        return f"approved and published | {result.raw}"

    @listen("rejected")
    def hold_incident(self, review: HumanFeedbackResult) -> str:
        """A rejected incident never reaches the Linear Agent."""
        self.state.disposition = "held"
        self.state.reviewer_note = review.feedback or ""
        return "held by reviewer; nothing was published"

    @listen(or_(publish_incident, hold_incident, queue_for_support))
    def summarize(self, branch_result: str) -> str:
        """Fan-in: one closing step, whichever branch ran."""
        return (
            f"{self.state.case.case_id} → {self.state.queue} "
            f"({self.state.priority}) [{self.state.disposition}]: {branch_result}"
        )


def sample_inputs() -> dict[str, object]:
    """Return the synthetic P0 case that exercises the human approval gate."""
    return {
        "case": {
            "case_id": "CASE-1042",
            "source": " AWS ",
            "account_id": "ACC-88",
            "customer_tier": "Strategic",
            "severity": "Critical",
            "summary": " Production outage during document submission ",
        }
    }


def standard_inputs() -> dict[str, object]:
    """A synthetic non-incident case that takes the STANDARD path end to end."""
    inputs = sample_inputs()
    case = inputs["case"]
    assert isinstance(case, dict)
    case["severity"] = "Medium"
    case["customer_tier"] = "Standard"
    case["summary"] = "User needs help updating a template."
    return inputs


def run(*, standard: bool = False, sync_to_linear: bool = False) -> str:
    flow = TriageXExtendedFlow()
    inputs = standard_inputs() if standard else sample_inputs()
    inputs["sync_to_linear"] = sync_to_linear
    result = flow.kickoff(inputs=inputs)
    print(result)
    print(flow.state.model_dump_json(indent=2))
    return str(result)


def main() -> None:
    """Run the incident path (interactive review) unless --standard is passed."""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--standard",
        action="store_true",
        help="Use a non-incident case: no human gate, no LLM, fully deterministic.",
    )
    parser.add_argument(
        "--sync-linear",
        action="store_true",
        help="Allow an approved incident to create a real Linear issue via MCP.",
    )
    args = parser.parse_args()
    run(standard=args.standard, sync_to_linear=args.sync_linear)


if __name__ == "__main__":
    main()
