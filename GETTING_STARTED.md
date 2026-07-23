# Getting Started

This guide gets the CrewAI use-case lab running locally.

## Requirements:
- Python 3.10–3.13
- `uv` package manager https://docs.astral.sh/uv/getting-started/installation/

## Installation
- `Install Guide` framework https://docs.crewai.com/v1.15.5/en/installation

## Getting Started

```bash
cp .env.example .env
uv sync --extra dev
```

The first Agent guide uses Firecrawl MCP. Its hosted endpoint has a keyless tier; optionally add `FIRECRAWL_API_KEY` to `.env` for higher limits.

Module 02 can optionally create a real Linear issue. Leave it disabled for the
local exercise, or add `LINEAR_API_KEY` and `LINEAR_TEAM` and run the solution
with `--sync-linear` against a sandbox/test team.

Its enterprise extension also requires GitHub to be connected under CrewAI AMP
Tools & Integrations and `CREWAI_PLATFORM_INTEGRATION_TOKEN` to be set. The
extension exposes only `github/get_issue_by_number` and never writes to GitHub.

## Run the flow
```bash
uv run python modules/02-triagex-flow/triagex_flow/src/triagex_flow/main.py
crewai run
```
## Coding Agent Skills:
https://www.skills.sh/crewaiinc/skills
