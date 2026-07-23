# Permissioned Chat Flow — deployable use case

The module 03 conversational flow packaged with the standard CrewAI project
scaffold (`crewai create flow`), so the use case can be deployed to CrewAI
AMP or run with the CrewAI CLI.

**Use case:** session setup loads a user profile (analyst / viewer / guest);
the profile's permissions decide which routes each conversational turn may
take — web research (Firecrawl search + scrape), generic page fetch
(scrape-only), or a deterministic permission-denied reply that never builds
an Agent.

The flow is self-contained: it carries its own profiles, least-privilege MCP
configuration, and Agents, so it ships without the workshop repository.

## Run locally

```bash
cd modules/03-conversational-routing/permissioned_chat
crewai install
crewai run                                   # REPL as CHAT_PROFILE (default analyst)
uv run python src/permissioned_chat/main.py --profile viewer
uv run plot                                  # write permissioned_chat.html (flow graph)
```

Try the same two messages under each profile:

1. `Research recent developments in agent orchestration frameworks.`
2. `Fetch https://docs.crewai.com and summarize this page.`

## Persistence: quit and resume

Chats are snapshotted via `@persist()` into `CREWAI_STORAGE_DIR`
(default `./storage`, gitignored). Reuse a session id to continue after a
restart:

```bash
uv run python src/permissioned_chat/main.py --profile viewer --session demo-1
# chat, then quit — later:
uv run python src/permissioned_chat/main.py --profile viewer --session demo-1  # resumes
```

(`crewai run` reads `CHAT_SESSION` from `.env` instead of a flag.) Identity
sticks to the session, but permissions are re-resolved every turn — a resumed
session never keeps stale grants. Delete `./storage` to forget all chats.

## Run one turn with a trigger payload (AMP-style invocation)

```bash
uv run run_with_trigger '{"message": "Research agent orchestration.", "profile": "viewer"}'
```

Pass the same `"session_id"` in later payloads to continue the conversation.
