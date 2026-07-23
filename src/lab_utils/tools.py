"""Deterministic tools used alongside the lab's use-case Agents."""

from __future__ import annotations

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class AccountPriorityInput(BaseModel):
    """Arguments accepted by the account-priority tool."""

    employee_count: int = Field(description="Approximate company employee count", ge=0)
    open_cases: int = Field(description="Number of currently open support cases", ge=0)
    renewal_days: int = Field(description="Days until renewal", ge=0)


def score_account_priority(
    employee_count: int,
    open_cases: int,
    renewal_days: int,
) -> str:
    """Return a transparent account-research priority tier."""
    reasons: list[str] = []
    if employee_count >= 10_000:
        reasons.append("large enterprise account")
    if open_cases >= 5:
        reasons.append("five or more open cases")
    if renewal_days <= 90:
        reasons.append("renewal is within 90 days")

    if len(reasons) >= 2:
        return f"HIGH: {'; '.join(reasons)}"
    if reasons:
        return f"MEDIUM: {reasons[0]}"
    return "STANDARD: no priority rules matched"


class AccountPriorityTool(BaseTool):
    """Expose deterministic account-priority rules to the research Agent."""

    name: str = "account_priority_check"
    description: str = "Score account-research priority from size, open cases, and renewal timing."
    args_schema: type[BaseModel] = AccountPriorityInput

    def _run(self, employee_count: int, open_cases: int, renewal_days: int) -> str:
        return score_account_priority(employee_count, open_cases, renewal_days)
