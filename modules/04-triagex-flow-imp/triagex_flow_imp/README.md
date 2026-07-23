# TriageX-Imp Flow — self-improving triage, deployable use case

Module 04 builds directly on module 02's TriageX flow: same GitHub date-range
intake and deterministic quality gate, plus a learning loop that gets
**better at spotting urgent work over time** — urgency is proposed from
labels *and* recalled human precedent, a human verifies every proposal before
Linear is touched, and each verdict is remembered for the next run.

```text
fetch_range (GitHub Agent App, read-only)
  → triage_range      quality gate · urgency proposed by label OR self.recall() precedent
  → @router           proposals? → REVIEW_URGENT · none? → NO_URGENT
  → @human_feedback   reviewer sees each proposal + its past verdicts
        ├── approved → self.remember(verdict=urgent)     → publish (opt-in)
        └── rejected → self.remember(verdict=not_urgent) → nothing publishes
  → publish_accepted  human-approved items only, save_issue-only MCP agent
  → summarize
```

The learning loop is deliberately conservative: memory only ever **proposes**
(strict majority of past `urgent` verdicts required), the human always
confirms, and held proposals teach the flow what *isn't* urgent. Memory is
context, not authority.

## Setup

Fill `.env`: a model key, `CREWAI_PLATFORM_INTEGRATION_TOKEN` (connect GitHub
under CrewAI AMP → Tools & Integrations), and optionally Linear credentials.
Verdict memories are stored under `CREWAI_STORAGE_DIR` (default `./storage`)
— delete that directory to reset what the flow has learned.

## Run locally

```bash
cd modules/04-triagex-flow-imp/triagex_flow_imp
crewai install
crewai run                                   # last 7 days; pauses for review if proposals exist
uv run python src/triagex_flow_imp/main.py --since 2026-07-01 --until 2026-07-22
uv run plot                                  # write triagex_flow_imp.html (flow graph)
```

When urgency is proposed, the terminal pauses at the review gate: reply in
plain language ("approve", "hold these", …) — an LLM maps your reply onto
`approved`/`rejected`, and unmappable replies fall back to `rejected`.

Linear writes stay double-gated: they need your `approved` verdict **and**
`--sync-linear` (or `SYNC_TO_LINEAR=true` in `.env`), plus
`LINEAR_API_KEY`/`LINEAR_TEAM`. Published issues carry the reviewer note.

## See the learning happen

1. Run once; approve (or hold) the proposals — the summary prints how many
   verdicts were remembered.
2. Run again over an overlapping window: the triage summary now shows
   `(N learned)` proposals, and the review screen cites your own past
   verdicts as `past verdict · …` lines.

## Run with a trigger payload (AMP-style invocation)

```bash
uv run run_with_trigger '{"owner": "crewAIInc", "repo": "crewAI", "since": "2026-07-15", "until": "2026-07-22", "sync_to_linear": false}'
```
