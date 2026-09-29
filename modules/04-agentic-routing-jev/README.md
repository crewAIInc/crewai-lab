# Module 04 · Agentic Routing with Jev

[Open the section slides](deck.html) for the control-flow diagram, abstention
gate, four-turn journey, evaluation, and live demo commands.

## Use case

A customer asks about order #4021, then asks about a damaged item, an ambiguous
second item, and finally names that item. One CrewAI conversational Flow keeps
the session history. Jev answers three bounded questions on each turn; Python
validates the answers and selects an `@listen` handler. The handlers return
sample replies and never start a return or refund.

The runnable project in [`example/`](example/) comes from
[`convo-flow-example-jev`](https://github.com/lorenzejay/convo-flow-example-jev)
(local source checkout at commit `6758a17`). It carries its own lockfile and
CrewAI 1.15.23. It requires Python 3.11–3.13. Run its commands **inside
`example/`**.

## Learning objective: control flow

```text
handle_turn(message, session_id)
  → CrewAI adds the user turn to conversation history
  → route_turn() sends history + order to Jev once
      ├── route Choice: order / returns / clarify
      ├── item_action yes/no: is this about a particular item?
      └── item Choice: exact item / unresolved
  → Python validates all three answers
  → uncertain route or unresolved item-specific return? clarify
  → @listen(selected_route) runs the matching handler
  → handler appends its reply to the same session
```

The key distinction is between **classification** and **control**. Jev can
classify the turn and identify a possible item. The application decides whether
those answers are sufficient to run a handler. Returning a route from
`route_turn()` bypasses CrewAI's built-in LLM router but keeps CrewAI's
conversation lifecycle and handler dispatch.

## Walk through the four turns

| Turn | Jev's raw route | Application route | Why |
| --- | --- | --- | --- |
| “Where are my Studio headphones?” | `order` | `order` | Delivery question. |
| “They arrived damaged. Can I return them?” | `returns` | `returns` | History resolves “they” to the headphones. |
| “Can I return one of the other blue items too?” | `returns` | `clarify` | Return intent is clear; two other blue items remain possible. |
| “I mean the Sport Earbuds.” | `returns` | `returns` | The follow-up identifies one item in the same session. |

The third row is the main teaching moment: a correct intent label is not enough
to proceed with item-specific help. The original Jev answer stays in
`decision["answer"]`; the final route records the application's override.

Open the [interactive four-turn diagram](example/docs/flow-diagram.html) or
[short GIF](example/docs/demo.gif) to present the sequence. Both are authored
illustrations; neither shows live model measurements.

## Run it

From `modules/04-agentic-routing-jev/example/`:

```bash
uv sync --locked
uv run python smoke_check.py
python3 eval_router.py --check
```

The smoke check uses mocked HTTP and the real CrewAI `handle_turn()` lifecycle:
no model key or provider request. It checks all four handler routes, including
the third-turn override and a low-confidence fallback. The evaluator check
validates the authored cases and scoring without making API requests.

For a live Jev run, copy `.env.example` to `.env`, set `TYPESAFE_API_KEY`, then:

```bash
uv run --env-file .env python flow.py          # interactive: type at You:
uv run --env-file .env python flow.py --demo   # authored four-turn example
```

If your key is already in the lab root's `.env`, use
`uv run --env-file ../../../.env python flow.py` from `example/` instead.

The terminal chat accepts your own messages in one session. The scripted demo
reports differences between authored expectations and live decisions instead
of failing on a safe low-confidence `clarify` route. Each turn makes one
TypeSafe request. No OpenAI key is needed for this flow; the replies are fixed
examples rather than generated support answers or real order lookups.

Run `uv sync --locked` and `uv run` inside `example/`, not in this parent
directory. If your shell is still activated against the old
`05-agentic-routing-jev/example/.venv`, run `deactivate` first. You do not need
to activate a virtual environment for `uv run`.

## Guided exercise

1. In [`flow.py`](example/flow.py), find `route_turn()`. Trace which parts are
   model output, which are Python gates, and which `@listen` method runs for
   turn three. Find the raw `returns` Choice retained after the route changes
   to `clarify`.
2. In [`smoke_check.py`](example/smoke_check.py), change the mocked third-turn
   item from `unresolved` to `sport_earbuds`. Predict the final route, then run
   the check and observe its expected assertion failure. Restore the fixture
   afterward. Explain why the selected item is
   now sufficient for the handler even though the customer's words are still
   ambiguous. This exposes a model-error risk that routing code cannot fix.
3. Add a new no-key case for an item-specific return where Jev selects an item
   with confidence below `ITEM_CONFIDENCE_FLOOR`. Assert that the final route
   is `clarify` and the raw item Choice remains visible. Compare it with the
   existing low-confidence checks.

## Evaluate the decision point

[`support-evaluation.md`](example/docs/support-evaluation.md) explains the
31 authored return-readiness cases and the Jev / GPT-6 Luna / GPT-6 Astra
comparison. In one live pass, all three reached 31/31 final routes. Jev's raw
item Choice was 30/31; the application's low-confidence gate corrected that
final route. Median HTTP times in that pass were 163 ms, 924 ms, and 1,887 ms,
respectively. The cases helped tune the demo and do not establish production
accuracy. The comparison calls providers directly; `smoke_check.py` separately
checks CrewAI dispatch.

The useful evaluation unit is the **final routing decision plus its components**:
raw route, item action, item Choice, confidence, and whether the code abstained.
For a real support system, collect independently reviewed conversations before
choosing thresholds, and count false-ready returns separately from unnecessary
clarifications.

## Checkpoint

Explain why the third turn reaches `clarify` although Jev chose `returns`, and
show where the fourth turn reuses history to reach `returns`. Identify the
model's decision, the code's gate, CrewAI's dispatch, and the handler's reply.

## Source and limits

The example is a standalone conversational Flow project, not a `crewai run`
deployment scaffold. Its handlers are read-only samples. The local copy keeps
the source project's files together so its lockfile, evaluation data, and
visual walkthrough remain reproducible. See the [example README](example/README.md)
for API payload and configuration details.
