# Module 04 · Self-Improving Triage (human_feedback + memory)

## Use case

TriageX (module 02) again — but this time the flow **learns**. Two features
carry the whole module:

- **`@human_feedback`** — a person verifies every urgency proposal before
  anything reaches Linear. Their freeform reply is mapped onto
  `approved`/`rejected` by an LLM; unmappable replies fall back to `rejected`.
- **`self.remember` / `self.recall`** — each verdict is stored as scoped
  memory (`/triage/<owner>-<repo>/urgency`). Future runs recall precedent for
  similar items and can propose urgency even when no label is present.

## Learning objective

Human judgment is expensive — spend it once, then reuse it. The loop stays
safe because each layer only *proposes* to the next:

```text
labels + recalled precedent  →  PROPOSE   (code, strict majority)
@human_feedback              →  CONFIRM   (person, default = reject)
--sync-linear / SYNC_TO_LINEAR → PUBLISH  (explicit opt-in)
```

Rejected proposals are remembered as `not_urgent` — the flow learns from
"no" just as much as from "yes".

## Run it

The complete flow lives in the deployable scaffold (`triagex_flow_imp/`,
standard `crewai create flow` project). See its README for setup and the
two-run demo that shows `(N learned)` proposals citing your own past
verdicts. Slides: open `deck.html` in a browser.

```bash
cd modules/04-triagex-flow-imp/triagex_flow_imp
crewai install && crewai run
```

## Checkpoint

Run twice over overlapping windows. Run 1 proposes from labels only and
remembers your verdict; run 2's review screen shows `[learned precedent]`
proposals with `past verdict · …` lines — your earlier decision, recalled.

## Debrief

Production versions would remember per-reviewer verdicts, add memory decay,
track proposal precision over time, and require per-item (not batch)
approval. The lab keeps the loop visible: propose → confirm → remember.
