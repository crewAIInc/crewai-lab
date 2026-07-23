# Module 01 · Company Research Agent + MCP (5 minutes)

## Named use case

**Company research agent** — gathers current public company data with one narrowly scoped MCP tool.

## Learning objective

Create one bounded Agent, attach Firecrawl's `firecrawl_search` tool over Streamable HTTP, and request a validated `CompanyResearchBrief`.

## Teach

- `role` defines the job.
- `goal` defines success.
- `backstory` carries stable constraints.
- `mcps` gives the Agent remote capabilities.
- `kickoff()` supplies the current task.
- `response_format` validates the result.

The starter deliberately exposes only `firecrawl_search`. Scraping, crawling, extraction, and page interaction are not available to this Agent.

## Setup

Firecrawl's hosted endpoint supports a rate-limited keyless tier. An API key raises limits:

```bash
FIRECRAWL_MCP_URL=https://mcp.firecrawl.dev/v2/mcp
FIRECRAWL_API_KEY=fc-your-key  # optional
```

The key is sent as an `Authorization` bearer header, never in the task prompt.

## Exercise

Fill the three Agent TODO values in `basic.py`, inspect the `mcps` configuration, then run:

```bash
uv run python modules/01-company-research-agent/basic.py
uv run python modules/01-company-research-agent/solution.py
```

## Checkpoint

The brief cites public URLs, distinguishes evidence from inference, and moves unsupported facts to `open_questions`.

## Debrief

An MCP-enabled Agent still is not the workflow. Triage, tenant authorization, memory, approvals, and the decision to expose more powerful tools remain Flow and application responsibilities. Module 05 places this Agent inside a conversational Flow and adds `firecrawl_scrape` plus local scoring.

