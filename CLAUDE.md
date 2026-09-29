# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A hands-on CrewAI teaching lab agentic systems use cases. Active workshop modules: 01 (agent basics), 02 (TriageX — the primary Flow use case), 03 (Conversational Flows via permission-aware routing: profile → permissions → route → tool allowlist), and 04 (Agentic Routing with Jev: typed decisions → Python readiness gate → CrewAI handler dispatch). The former self-improving TriageX module remains outside the current agenda.

The root lab pins CrewAI to exactly 1.15.23. Module 04 is a copied standalone Jev example with its own lockfile and the same CrewAI 1.15.23 pin. Modules 02–03 have independent scaffold environments pinned to 1.15.5. Do not sync their environments from the root.

## Commands

```bash
uv sync --extra dev                 # install (Python 3.10–3.13)
uv run python modules/02-triagex-flow/solution_extended.py --standard   # offline smoke run (no keys)
uv run ruff check .                 # lint
uv run python -m compileall -x '\.venv' src modules     # syntax-check everything (skip scaffold venvs)

uv run python modules/02-triagex-flow/solution_extended.py --standard   # run a module script (deterministic path)
cd modules/02-triagex-flow/triagex_flow && crewai run        # run a scaffolded use-case project
uv run outreach                     # module 07 outreach flow (root project script)
```

Modules that call an LLM need `.env` (copy from `.env.example`) with a key matching `LAB_MODEL`. Tests do not need keys.

## Architecture

Flow code lives inside each module; the package holds only shared infrastructure:

- `modules/01-…/02-…/03-…/` — the teaching layer, one directory per use case. Each has `README.md` (instructor framing), `basic.py` (the exercise with intentional TODOs — do not "fix" these), and the complete flow (inline `solution.py` or a scaffold). Module scripts import shared infra from `lab_utils` but own their flows. Module 04 instead uses its copied standalone example and a guided exercise in its README.
- `src/lab_utils/` — shared infrastructure only: `settings.py` (env vars; `LAB_MODEL` is the single model string), `models.py` (shared Pydantic contracts; agents return them via `kickoff(..., response_format=Model)` → `result.pydantic`), `agents.py` (`build_*_agent()` factories, created fresh per call), `mcp.py` (least-privilege MCP builders — every `MCPServerHTTP` uses `create_static_tool_filter` allowlists and bearer-token headers; tests assert this), `tools.py` (deterministic `BaseTool`s with plain-function cores).
- **Deployable use-case scaffolds**: the hands-on modules contain a `crewai create flow` project (`modules/02-triagex-flow/triagex_flow/` and `modules/03-conversational-routing/permissioned_chat/`; the parked self-improvement scaffold is in `modules/04-triagex-flow-imp/triagex_flow_imp/`). Each has its own `pyproject.toml`, `[tool.crewai]`, `kickoff`/`plot`/`run_with_trigger` scripts, and a self-contained `src/<name>/main.py`. The scaffold IS the module's solution — those modules have no `solution.py`. Scaffold projects deliberately do NOT import `lab_utils` — they carry their own copies so they deploy standalone. Never create these by hand; run `crewai create flow <name>` (underscores) and port code into it.
- Exception: `src/lab_utils/outreach_flow.py` (archived module 07's flow) stays in the package behind the root `outreach`/`outreach_plot` scripts (uniquely named — the canonical `kickoff`/`run_crew`/`plot` entry points belong to the scaffolds). Scaffolds are deliberately NOT uv workspace members: they all declare the same AMP-required script names, which cannot coexist in one venv (syncing one deletes another's launchers). Each scaffold is standalone — `crewai install` inside it creates its own venv.
- Module 02 currently has extra flat scripts (`solution_extended.py` with `@router`/`@human_feedback`/`or_`, `github_solution.py` with `Agent(apps=["github/get_issue_by_number"])`) and an HTML slide deck (`deck.html`).
- Module 04 is a self-contained copy of the Jev support routing example under `modules/04-agentic-routing-jev/example/`. Its `flow.py` and `smoke_check.py` share a four-turn `scenario.json`; `eval_router.py` and `eval_cases.json` support an offline dataset check and optional live model comparison. It has its own `pyproject.toml` and `uv.lock`; run `uv sync --locked` inside `example/`, not at the lab root. The module's README provides the exercise and checkpoint, so this module has no `basic.py`.

There is no shared test suite — this is workshop material. Verify changes with `ruff`, `compileall`, and the offline deterministic runs (module 02 `basic.py` and `solution_extended.py --standard` need no keys; module 04 has `smoke_check.py` and `eval_router.py --check`). The root Ruff config excludes module 04's copied source to preserve the upstream example verbatim.

## Design rules the code follows

- **Flows decide, agents phrase.** Routing, priority, validation, and gating are deterministic Python in Flow methods (see `TriageXFlow.triage`); agents only handle language-heavy steps and are told not to alter or invent decisions, data, or system status.
- Conversational module 03 (and several archived modules) uses the experimental `@ConversationConfig` + `Flow[ConversationState]` with a `route_turn()` string router and `@listen("ROUTE_NAME")` handlers; handlers call `self.append_assistant_message(reply)`. Module 03 subclasses `ConversationState` to carry the session profile, and its routes map permissions to MCP tool allowlists (research = search+scrape, fetch = scrape-only); denied routes reply deterministically without building an Agent.
- Module 04's Jev example uses the same conversational lifecycle on CrewAI 1.15.23. One Jev request per turn returns typed route, item-action, and item answers; Python validates them and routes uncertain or unresolved item-specific returns to `clarify`. The handlers only append fixed, read-only sample replies. The 31-case comparison is tuned, authored diagnostic data, not a production accuracy estimate.
- External side effects (real Linear issue creation) are opt-in behind explicit flags like `--sync-linear` or `SYNC_TO_LINEAR=true`, never the default path. GitHub access is read-only.
- Keep decision logic (triage rules, quality gates, permission routing) in pure functions so it stays inspectable and runnable offline — the deterministic paths are the workshop's no-keys demos.

## Editing guidance

If you change shared logic in `src/lab_utils/`, check whether the corresponding `modules/*/basic.py`, `solution.py`, and `README.md` reference it — the teaching layer and package must stay in sync. Scaffolded use-case projects duplicate infra by design; when the shared version of copied logic changes (e.g. triage rules), update the scaffold copy too. Timing and module ordering are documented in `README.md`.
