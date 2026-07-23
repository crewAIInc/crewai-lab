# Module 02 · TriageX Flow + Linear MCP (8 minutes)

## Named use case

**TriageX** — a triage Agent/Flow pattern used in development and sandbox testing.

## Learning objective

Move queue and priority decisions into a typed, observable Flow, then hand the
approved decision to a narrowly scoped Agent that can create a Linear issue.

```text
AWS case input
  → @start normalize
  → @listen triage (deterministic queue + priority)
  → @listen create_linear_ticket (optional Agent + Linear MCP)
  → @listen summarize
```

State is the data plane. Decorators define the control plane. Known routing
policy stays in code rather than depending on model behavior. The Agent is an
integration boundary: it publishes the result but does not decide the result.

## Linear remote MCP

Linear's current read-write endpoint uses Streamable HTTP:

```python
MCPServerHTTP(
    url="https://mcp.linear.app/mcp",
    headers={"Authorization": "Bearer <LINEAR_API_KEY>"},
    streamable=True,
)
```

CrewAI supports the remote transport directly, so this example does not need
the `mcp-remote` compatibility package. The Agent allow-list exposes only
`save_issue`, Linear's current combined create/update issue tool. The prompt
omits `id`, which makes the operation a creation.

## Extended solution: @router, @human_feedback, and or_

`solution_extended.py` reworks the same triage pipeline with three more Flow
features. A `@router` step turns the fixed triage decision into named branches,
P0 incidents pause at a `@human_feedback` approval gate before the Linear
Agent may run, and `or_` re-converges whichever branch ran into one summary:

```text
triage
  → @router dispatch
      ├── "INCIDENT" → @human_feedback review (approve / reject)
      │       ├── approved → optional Linear save_issue
      │       └── rejected → held; never reaches the Agent
      └── "STANDARD" → queue for support (no human, no LLM)
  → @listen(or_(...)) summarize
```

```bash
# Deterministic STANDARD path: no human gate, no LLM call.
uv run python modules/02-triagex-flow/solution_extended.py --standard

# Incident path: pauses for interactive reviewer approval.
uv run python modules/02-triagex-flow/solution_extended.py

# Approved incidents may create a real issue (sandbox team, explicit opt-in).
uv run python modules/02-triagex-flow/solution_extended.py --sync-linear
```

The reviewer's freeform reply is mapped onto the `emit` labels by the LLM;
anything unmappable falls back to `default_outcome="rejected"`, so the safe
path is the default.

## Enterprise extension: GitHub → quality gate → Linear

The optional enterprise path uses CrewAI Agent Apps for GitHub reads and the
remote Linear MCP server for the gated write:

```text
GitHub issue or PR number
  → Agent(apps=["github/get_issue_by_number"])
  → structured GitHubTriageCandidate
  → Flow quality policy
      ├── rejected → explain gaps; never call Linear
      └── accepted → optional Linear save_issue
```

The GitHub action is deliberately read-only. GitHub content is treated as
untrusted data rather than instructions. The Flow accepts an item only when it
has a descriptive title and body, an explicit problem and desired outcome, and
supporting evidence. Pull requests must also state test evidence.

Connect GitHub under CrewAI AMP **Tools & Integrations**, copy the Enterprise
Token, and configure:

```dotenv
CREWAI_PLATFORM_INTEGRATION_TOKEN=
GITHUB_OWNER=your-org
GITHUB_REPO=your-repository
```

Read and triage an issue without writing to Linear:

```bash
uv run python modules/02-triagex-flow/github_solution.py --number 123 --kind issue
```

Read a pull request and allow accepted work to create a Linear issue:

```bash
uv run python modules/02-triagex-flow/github_solution.py \
  --number 456 --kind pull_request --sync-linear
```

`--sync-linear` is still only permission to attempt the write: rejected items
never reach the Linear Agent. The sample processes one item per run so the
decision and side effect remain easy to inspect.

## Exercise

In `basic.py`:

1. Normalize severity.
2. Route critical impact to `incident_response`.
3. Assign `P0` or `P2`.
4. Inspect how the final Flow step gives the fixed triage decision to the
   MCP-enabled Agent without asking the Agent to reclassify it.

```bash
uv run python modules/02-triagex-flow/basic.py                        # deterministic synthetic case
uv run python modules/02-triagex-flow/solution_extended.py --standard # router + HITL, no LLM path
```

Both commands are safe by default and skip Linear.

## Deployable use case: triage a GitHub date range

The `triagex_flow/` scaffold (standard `crewai create flow` project) is the
production shape of this module: it inspects the issues and PRs created in a
date range on <https://github.com/crewAIInc/crewAI>, gates them with the same
deterministic quality policy, and optionally publishes accepted items to
Linear. See `triagex_flow/README.md` for setup; it needs a model key and
`CREWAI_PLATFORM_INTEGRATION_TOKEN`.

```bash
cd modules/02-triagex-flow/triagex_flow
crewai install
crewai run                                                    # last 7 days
uv run python src/triagex_flow/main.py --since 2026-07-01 --until 2026-07-22
```

To create real Linear issues for accepted items, use a sandbox/test team, add
these values to `triagex_flow/.env`, and opt in explicitly with
`--sync-linear`:

```dotenv
LINEAR_MCP_URL=https://mcp.linear.app/mcp
LINEAR_API_KEY=
LINEAR_TEAM=DOC
```

`LINEAR_TEAM` may be a team name, key, or ID. The command performs external
writes and may create visible issues in that team.

## Checkpoint

Change the case from `critical` to `medium`. No LLM or MCP call is needed to
observe the routing change. Then compare that deterministic path with the
explicitly enabled Linear publishing step.

## Debrief

Production TriageX rules would include tenant authorization, idempotency and
deduplication before `save_issue`, richer queue policy, approved team mappings,
prompt-injection defenses, and evaluation against labeled historical cases. The
lab keeps the routing mechanics visible and the external write opt-in.
