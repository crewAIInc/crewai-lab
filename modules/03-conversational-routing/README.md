# Module 03 · Permission-Aware Conversational Routing

## Use case

A conversational assistant where session setup loads a **user profile**, and
the profile's **permissions** decide which routes each turn may take:

- `research` permission → a web-research route (Firecrawl search + scrape)
- `fetch` permission → a generic low-privilege fetch route (scrape only)
- neither → a deterministic permission-denied reply

## Learning objective

Intelligent routing is two separable decisions — and only one of them may
be delegated to a model:

1. **Intent** — what does this turn ask for? Delegated to the LLM router
   (`RouterConfig`): the catalog is built from each handler's docstring, and
   `route_turn()` does session setup then `super().route_turn(context)` —
   every turn routes via the catalog, including profile questions and
   goodbyes. (Returning `None` would NOT delegate: it means converse.)
2. **Authorization** — may this profile do that? Code, always: every handler
   checks its permission on entry and falls back to the deterministic denial.

```text
session start → load profile (like a @start step) → permissions
each turn     → route_turn(): session setup, then super() → LLM router
                  ├── docstring catalog → WEB_RESEARCH · PAGE_FETCH · PROFILE_INFO · converse · end
                  ├── handler checks permission → runs its Agent, or denies in code
                  └── PROFILE_INFO answers from state — detection is fuzzy, answers are code
```

The security property to teach: **permissions map to tool allowlists**. The
research route's Agent carries `firecrawl_search` + `firecrawl_scrape`; the
fetch route's Agent carries `firecrawl_scrape` only. A denied route never
constructs an Agent at all — the model is never asked to enforce policy.

## Exercise

In `basic.py`:

1. Gate the research route on the `research` permission (TODO 1).
2. Gate the fetch route on the `fetch` permission (TODO 2).
3. Inspect why `build_page_fetch_agent()` gets a scrape-only allowlist (TODO 3).

```bash
uv run python modules/03-conversational-routing/basic.py
```

## Deployable use case: the `permissioned_chat/` scaffold

The complete flow lives in the standard `crewai create flow` project (the
module's solution), self-contained and deployable to CrewAI AMP:

```bash
cd modules/03-conversational-routing/permissioned_chat
crewai install
crewai run                                                  # REPL as CHAT_PROFILE
uv run python src/permissioned_chat/main.py --profile viewer
uv run run_with_trigger '{"message": "Research agent orchestration."}'
```

Try the same two messages under each profile:

1. `Research recent developments in agent orchestration frameworks.`
2. `Fetch https://docs.crewai.com and summarize it.`

## Checkpoint

No LLM call is needed to observe the routing change: `route_for()` is a pure
function. `analyst` routes message 1 to `WEB_RESEARCH`; `viewer` gets
`PERMISSION_DENIED` for the same words; `guest` is denied both routes. Try it
directly in a REPL: `route_for("research X", load_profile("viewer"))`.

## Debrief

Production versions would resolve profiles from an identity provider, carry
tenant scoping in every tool call, log denied attempts, and treat the
permission set as claims on the session rather than a class attribute. The
lab keeps the mechanics visible: profile → permissions → route → allowlist.
