"""Module 07: outreach generation, evaluation, HITL, and deployment."""

from __future__ import annotations

from crewai.flow import Flow, HumanFeedbackResult, human_feedback, listen, start
from pydantic import BaseModel

from lab_utils.agents import build_email_evaluator, build_outreach_agent
from lab_utils.models import EmailEvaluation, LeadEmail
from lab_utils.settings import LAB_MODEL


class OutreachState(BaseModel):
    lead_context: str = (
        "Synthetic lead: Jordan Lee, VP Operations at Northwind. Public signal: the company is "
        "expanding digital sales workflows. Approved value point: reduce manual agreement steps."
    )
    draft: LeadEmail | None = None
    evaluation: EmailEvaluation | None = None
    disposition: str = "pending"


class OutreachProductionFlow(Flow[OutreachState]):
    """Generate, evaluate, and review one lead email before publication."""

    @start()
    def generate_email(self) -> LeadEmail:
        result = build_outreach_agent().kickoff(
            "Draft one lead email using only the approved synthetic context below. Do not invent "
            "personalization or customer claims.\n\n"
            f"{self.state.lead_context}",
            response_format=LeadEmail,
        )
        if result.pydantic is None:
            raise RuntimeError("The email Agent did not return a LeadEmail")
        self.state.draft = result.pydantic
        return self.state.draft

    @listen(generate_email)
    @human_feedback(
        message="Review the email and quality evaluation. Approve, reject, or request revision:",
        emit=["approved", "rejected", "needs_revision"],
        llm=LAB_MODEL,
        default_outcome="needs_revision",
    )
    def evaluate_for_review(self, draft: LeadEmail) -> str:
        result = build_email_evaluator().kickoff(
            "Evaluate this outreach draft against grounding, relevance, clarity, tone, and one "
            "clear call to action. Unsupported claims must fail.\n\n"
            f"APPROVED CONTEXT:\n{self.state.lead_context}\n\n"
            f"DRAFT:\n{draft.model_dump_json(indent=2)}",
            response_format=EmailEvaluation,
        )
        if result.pydantic is None:
            raise RuntimeError("The evaluator did not return an EmailEvaluation")
        self.state.evaluation = result.pydantic
        return (
            f"DRAFT:\n{draft.model_dump_json(indent=2)}\n\n"
            f"QUALITY EVALUATION:\n{self.state.evaluation.model_dump_json(indent=2)}"
        )

    @listen("approved")
    def publish(self, review: HumanFeedbackResult) -> str:
        self.state.disposition = "approved"
        return f"Approved for the downstream send system. Reviewer note: {review.feedback}"

    @listen("rejected")
    def stop(self, review: HumanFeedbackResult) -> str:
        self.state.disposition = "rejected"
        return f"Stopped before send. Reviewer note: {review.feedback}"

    @listen("needs_revision")
    def revise(self, review: HumanFeedbackResult) -> str:
        self.state.disposition = "needs_revision"
        return f"Revision requested: {review.feedback}"


def run_lead(inputs: dict[str, str]) -> object:
    """Per-lead unit suitable for an Airflow task or another orchestrator."""
    return OutreachProductionFlow().kickoff(inputs=inputs)


def kickoff() -> object:
    """Flow entry point used by `crewai run` and deployment."""
    return OutreachProductionFlow().kickoff()


def plot() -> None:
    """Generate a local HTML visualization of the production Flow."""
    OutreachProductionFlow().plot("outreach_production_flow")


if __name__ == "__main__":
    kickoff()
