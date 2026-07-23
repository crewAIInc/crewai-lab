# TriageX Flow — deployable use case

The module 02 TriageX flow packaged with the standard CrewAI project scaffold
(`crewai create flow`), so the use case can be deployed to CrewAI AMP or run
with the CrewAI CLI.

**Use case:** inspect the issues and pull requests created in a date range on
the CrewAI OSS repository (<https://github.com/crewAIInc/crewAI>), apply a
deterministic quality gate in Flow code, and optionally publish accepted items
to Linear.

Pipeline: a read-only GitHub Agent App (`search_issue` + `get_issue_by_number`)
extracts structured evidence for each item → `assess_candidate` decides
accept/reject in plain Python → only accepted items carrying an **`urgent`
label** may create Linear issues (priority 1) via a `save_issue`-only MCP
agent, and only when `sync_to_linear` is enabled. Accepted-but-not-urgent
items are recorded in state without any external write.

The flow is self-contained: it carries its own models, least-privilege MCP
configuration, and Agents, so it ships without the workshop repository.

## Setup

Fill `.env`: a model key, `CREWAI_PLATFORM_INTEGRATION_TOKEN` (connect GitHub
under CrewAI AMP → Tools & Integrations), and optionally Linear credentials.

## Run locally

```bash
cd modules/02-triagex-flow/triagex_flow
crewai install
crewai run                                   # triage the last 7 days
uv run python src/triagex_flow/main.py --since 2026-07-01 --until 2026-07-22
uv run plot                                  # write triagex_flow.html (flow graph)
```

Linear writes stay opt-in: add `--sync-linear`, set `SYNC_TO_LINEAR=true` in
`.env` (the only opt-in path `crewai run` can use), or send
`"sync_to_linear": true` in a trigger payload — plus
`LINEAR_API_KEY`/`LINEAR_TEAM`.

The publish gate matches labels in `URGENT_LABELS` (default: `urgent` plus
common high-priority spellings such as `high priority` and `priority: high`).
Urgent-labeled items publish at Linear priority 1; high-priority items at 2.
For a demo that always finds something to publish, add `bug` to
`URGENT_LABELS` in `.env` or pick a window containing a known
priority-labeled item.

## Run with a trigger payload (AMP-style invocation)

```bash
uv run run_with_trigger '{"owner": "crewAIInc", "repo": "crewAI", "since": "2026-07-15", "until": "2026-07-22", "sync_to_linear": false}'
```

The `@start` step accepts `crewai_trigger_payload`, which is how AMP delivers
trigger events (for example, a weekly schedule) to a deployed flow.
