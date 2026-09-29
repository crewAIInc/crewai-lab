# Building Reliable Agentic Systems That Survive Production

A hands-on CrewAI lab: progressive modules introduce Agents, Flows,
Conversational Flows, MCP, tools, human review, and deployment. The use cases
are intentionally generic — triage, research, permissioned assistants — so the
lab can be reused with any customer. All data is synthetic; nothing connects
to production systems or sends email.

**Workshop slides:** open [`index.html`](index.html) in a browser for the
five-section deck; modules 01–04 carry their own decks, and module 04 has an
interactive flow diagram.
**Presenter notes:** open [`speaker-notes.html`](speaker-notes.html) for the
five-section talk track, module outcomes, demo cues, and transitions.

## Prerequisites

- **Python 3.10–3.13** for the root lab; module 04 requires 3.11–3.13
- **[`uv`](https://docs.astral.sh/uv/getting-started/installation/)** — installs and runs everything
- **A model-provider API key** (e.g. `OPENAI_API_KEY`) matching the `LAB_MODEL` you set

The root lab pins **CrewAI 1.15.23**. Module 04 is a standalone example also
pinned to **CrewAI 1.15.23**; install it in its own environment using its lockfile.

## Setup (2 minutes)

```bash
cp .env.example .env        # add your model-provider key
uv sync --extra dev         # installs the lab
uv run python modules/02-triagex-flow/solution_extended.py --standard
```

That last command is the smoke test: a full deterministic flow run with no
API keys or network — if it prints a triage summary, the lab is ready.

## What each section needs

| Module | Run it | Extra credentials |
|---|---|---|
| 01 · Agent Basics | `uv run python modules/01-company-research-agent/solution.py [company]` | Model key. Firecrawl's keyless tier works; add `FIRECRAWL_API_KEY` for higher limits |
| 02 · Flow Foundations (TriageX) | `uv run python modules/02-triagex-flow/basic.py` — deterministic, no keys | — |
| 02 · extended (router + HITL) | `uv run python modules/02-triagex-flow/solution_extended.py --standard` (no keys) or without the flag (model key, interactive review) | Model key for the incident path |
| 02 · deployable scaffold | `cd modules/02-triagex-flow/triagex_flow && crewai install && crewai run` | Model key + `CREWAI_PLATFORM_INTEGRATION_TOKEN` (GitHub connected in CrewAI AMP). Linear writes are opt-in: `LINEAR_API_KEY`, `LINEAR_TEAM`, `SYNC_TO_LINEAR=true` |
| 03 · Conversational Routing | `cd modules/03-conversational-routing/permissioned_chat && crewai install && crewai run` — switch identity via `CHAT_PROFILE` (analyst/viewer/guest) | Model key. Firecrawl keyless tier is fine |
| [04 · Agentic Routing with Jev](modules/04-agentic-routing-jev/) | `cd modules/04-agentic-routing-jev/example && uv sync --locked && uv run --env-file ../../../.env python flow.py` — interactive live Jev chat | `TYPESAFE_API_KEY` in the root `.env` |

Earlier modules covering tools+MCP, flow memory, and HITL outreach deployment
are parked in [`archive/`](archive/) and can be revived per customer.

The hands-on module directories have a `README.md` (framing, exercise, checkpoint).
Open the section decks for
[Module 01](modules/01-company-research-agent/deck.html),
[Module 02](modules/02-triagex-flow/deck.html),
[Module 03](modules/03-conversational-routing/index.html), and
[Module 04](modules/04-agentic-routing-jev/deck.html) in a browser. Module 04
also has an [interactive four-turn diagram](modules/04-agentic-routing-jev/example/docs/flow-diagram.html).

## Deployable use cases

Modules 02 and 03 carry their complete solution as a standard
`crewai create flow` project — self-contained `src/<name>/main.py`, its own
`pyproject.toml` with `kickoff`/`plot`/`run_with_trigger` entry points — so
each deploys to CrewAI AMP as-is:

- `modules/02-triagex-flow/triagex_flow/` — triage GitHub issues/PRs from a date range → Linear
- `modules/03-conversational-routing/permissioned_chat/` — permission-aware conversational assistant

The former Section 04 self-improving TriageX scaffold and slides remain in
[`modules/04-triagex-flow-imp/`](modules/04-triagex-flow-imp/) for later use;
they are hidden from the current workshop agenda.

Module 04 copies the standalone [Jev support Flow example](modules/04-agentic-routing-jev/example/)
with its own CrewAI version and lockfile. It is a runnable teaching example,
not a `crewai run` deployment scaffold.

Scaffolds are standalone projects: `crewai install` inside one creates its own
venv (fast — uv hardlinks from cache). They are intentionally not part of the
root environment. Each scaffold has its own `.env`.

External writes never happen by default anywhere in the lab: Linear publishing
requires explicit opt-in, and GitHub access is read-only.

## Verify anytime

```bash
uv run python modules/02-triagex-flow/solution_extended.py --standard   # offline flow run
uv run ruff check .
uv run python -m compileall -x '\.venv' src modules
```

The former case-management and renewal modules are parked in
[`archive/`](archive/). More on CrewAI skills:
<https://www.skills.sh/crewaiinc/skills>
