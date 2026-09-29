"""Small live support-routing diagnostic. No dependencies; see docs/support-evaluation.md."""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import random
import statistics
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
# USD / million tokens: input, cached input, output, cache writes. Sources in docs/support-evaluation.md.
MODELS = {
    "jev": {"provider": "jev", "model": "jev-1.13.0", "key": "TYPESAFE_API_KEY", "rates": [0.042, 0.042, 0, 0.042]},
    "openai-fast": {"provider": "openai", "model": "gpt-6-luna", "key": "OPENAI_API_KEY", "effort": "none", "rates": [0.10, 0.01, 0.50, 0.125]},
    "openai-frontier": {"provider": "openai", "model": "gpt-6-astra", "key": "OPENAI_API_KEY", "effort": "low", "rates": [10, 1, 50, 12.50]},
}
ROUTE_CONFIDENCE_FLOOR = .5


def validate_dataset(dataset):
    ids = set()
    for case in dataset["cases"]:
        assert case["id"] not in ids, case["id"]
        ids.add(case["id"])
        task = dataset["tasks"][case["task"]]
        assert case["expected"] in task["criteria"], case["id"]
        assert case["messages"][-1]["role"] == "user", case["id"]
        assert case["slice"] and case["rationale"]
        if "item_question" in task:
            assert case["expected_raw_route"] in task["criteria"], case["id"]
            assert type(case["expected_item_action"]) is bool, case["id"]
            assert case["expected_item"] in task["item_criteria"], case["id"]
            assert case["expected_item_identified"] == (case["expected_item"] != "unresolved"), case["id"]
            assert case["split"], case["id"]
            expected = ("clarify" if case["expected_raw_route"] == "returns"
                        and case["expected_item_action"] and case["expected_item"] == "unresolved"
                        else case["expected_raw_route"])
            assert case["expected"] == expected, case["id"]
    assert ids


def request_data(config, task, case):
    state = dict(case.get("state", task["state"]), messages=case["messages"])
    properties = {"route": {"type": "string", "enum": list(task["criteria"])}}
    if "item_question" in task:
        properties.update(item_action={"type": "boolean"}, item={"type": "string", "enum": list(task["item_criteria"])})
    schema = {"type": "object", "properties": properties,
              "required": list(properties), "additionalProperties": False}
    if config["provider"] == "jev":
        questions = {"route": {"type": "choice", "instructions": task["instructions"], "criteria": task["criteria"]}}
        if "item_question" in task:
            questions["item_action"] = {"type": "noul", "instructions": task["action_question"]}
            questions["item"] = {"type": "choice", "instructions": task["item_question"],
                                 "criteria": task["item_criteria"]}
        return "https://api.typesafe.ai/v1/systemone", {
            "model": config["model"], "state": state,
            "questions": questions,
        }
    instructions = task["instructions"] + "\nAllowed routes and criteria:\n" + json.dumps(task["criteria"], ensure_ascii=False)
    if "item_question" in task:
        instructions += "\nAnswer item_action independently: " + task["action_question"]
        instructions += "\nAnswer item independently: " + task["item_question"]
        instructions += "\nAllowed items and criteria:\n" + json.dumps(task["item_criteria"], ensure_ascii=False)
    return "https://api.openai.com/v1/responses", {
        "model": config["model"], "store": False,
        "service_tier": "default",
        "instructions": instructions,
        "input": json.dumps(state, ensure_ascii=False),
        "text": {"format": {"type": "json_schema", "name": "route", "strict": True, "schema": schema}},
        "reasoning": {"effort": config["effort"]},
        "max_output_tokens": 2048 if config["effort"] != "none" else 128,
    }


def parse_response(config, raw, criteria, item_criteria=None):
    if config["provider"] == "jev":
        answer = raw["answers"]["route"]
        route, probabilities, confidence = answer["choice"], answer["probabilities"], answer["confidence"]
        assert answer["type"] == "choice"
        assert set(probabilities) == set(criteria)
        assert all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in probabilities.values())
        # Jev rounds each reported probability; with 77 routes the displayed sum can be 0.99.
        tolerance = max(.001, min(.05, .0005 * len(probabilities)))
        assert abs(sum(probabilities.values()) - 1) <= tolerance
        assert probabilities[route] >= max(probabilities.values())
        assert type(confidence) in (int, float) and math.isfinite(confidence) and 0 <= confidence <= 1
        if item_criteria:
            action_answer = raw["answers"]["item_action"]
            item_action_score = action_answer["noul"]
            assert action_answer["type"] == "noul"
            assert type(item_action_score) in (int, float) and math.isfinite(item_action_score) and 0 <= item_action_score <= 1
            item_action = item_action_score >= .5
            item_answer = raw["answers"]["item"]
            item = item_answer["choice"]
            item_probabilities = item_answer["probabilities"]
            assert item_answer["type"] == "choice" and item in item_criteria
            assert set(item_probabilities) == set(item_criteria)
            assert all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in item_probabilities.values())
            assert abs(sum(item_probabilities.values()) - 1) <= .02
            assert item_probabilities[item] >= max(item_probabilities.values())
            item_confidence = item_answer["confidence"]
            assert type(item_confidence) in (int, float) and math.isfinite(item_confidence) and 0 <= item_confidence <= 1
    else:
        assert raw["status"] == "completed", "Response did not complete"
        output = "".join(c["text"] for o in raw["output"] if o["type"] == "message"
                         for c in o["content"] if c["type"] == "output_text")
        parsed = json.loads(output)
        route = parsed["route"]
        probabilities = confidence = None
        if item_criteria:
            item_action, item = parsed["item_action"], parsed["item"]
            assert type(item_action) is bool and item in item_criteria
    assert route in criteria
    final_route = ("clarify" if confidence is not None and confidence < ROUTE_CONFIDENCE_FLOOR
                   and "clarify" in criteria else route)
    result = {"route": final_route, "probabilities": probabilities, "confidence": confidence}
    if item_criteria:
        low_item_confidence = config["provider"] == "jev" and item_confidence < .6
        result.update(raw_route=route, item_action=item_action, item=item,
                      route="clarify" if final_route == "returns" and item_action
                      and (item == "unresolved" or low_item_confidence) else final_route)
        if config["provider"] == "jev":
            result.update(item_action_score=item_action_score, item_confidence=item_answer["confidence"])
    return result


def estimated_cost(config, usage):
    if type(usage.get("input_tokens")) is not int or type(usage.get("output_tokens")) is not int:
        return None
    cached = usage.get("input_tokens_details", {}).get("cached_tokens", 0)
    writes = usage.get("input_tokens_details", {}).get("cache_write_tokens", 0)
    inp, cache, out, write = config["rates"]
    return ((usage["input_tokens"] - cached - writes) * inp + cached * cache + writes * write + usage["output_tokens"] * out) / 1_000_000


def call(config, task, case):
    url, payload = request_data(config, task, case)
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers={
        "Authorization": "Bearer " + os.environ[config["key"]], "Content-Type": "application/json",
    })
    started = time.perf_counter()
    record = {"request_sha256": hashlib.sha256(request.data).hexdigest()}
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = json.load(response)
        record["raw_response"] = raw
        if not isinstance(raw, dict):
            raise ValueError("Provider response must be a JSON object")
        record.update(resolved_model=raw.get("model"), usage=raw.get("usage", {}))
        record["estimated_cost_usd"] = estimated_cost(config, record["usage"])
        record.update(parse_response(config, raw, task["criteria"], task.get("item_criteria")))
    except urllib.error.HTTPError as exc:
        # Store only provider error metadata; never request headers or credentials.
        record["error"] = "HTTP " + str(exc.code)
        try:
            error = json.loads(exc.read()).get("error", {})
            record["error_detail"] = {k: error[k] for k in ("type", "code", "message") if k in error}
        except (ValueError, TypeError, AttributeError, OSError, http.client.HTTPException):
            pass
    except (OSError, http.client.HTTPException, ValueError, KeyError, TypeError, AttributeError, AssertionError) as exc:
        record["error"] = type(exc).__name__ + ": " + str(exc)
    record["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return record


def score(rows, criteria, floor=None):
    predicted = [("clarify" if floor is not None and r.get("confidence") is not None
                  and r["confidence"] < floor else r.get("route")) for r in rows]
    correct = sum(p == r["expected"] for p, r in zip(predicted, rows))
    automatic = [(p, r) for p, r in zip(predicted, rows) if p not in (None, "clarify")]
    f1 = []
    for label in criteria:
        tp = sum(p == label == r["expected"] for p, r in zip(predicted, rows))
        fp = sum(p == label != r["expected"] for p, r in zip(predicted, rows))
        fn = sum(p != label == r["expected"] for p, r in zip(predicted, rows))
        f1.append(2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0)
    result = {
        "n": len(rows), "correct": correct, "accuracy": correct / len(rows),
        "macro_f1": statistics.mean(f1), "error_count": sum("error" in r for r in rows),
    }
    if "clarify" in criteria:
        result.update(
            automatic_coverage=len(automatic) / len(rows),
            automatic_error_rate=sum(p != r["expected"] for p, r in automatic) / len(automatic) if automatic else None,
            unnecessary_clarifications=sum(p == "clarify" != r["expected"] for p, r in zip(predicted, rows)),
            missed_clarifications=sum(p not in (None, "clarify") and r["expected"] == "clarify" for p, r in zip(predicted, rows)),
        )
    return result


def summarize(rows, dataset):
    summary = {}
    for model in dict.fromkeys(r["model_key"] for r in rows):
        selected = [r for r in rows if r["model_key"] == model]
        latencies = sorted(r["latency_ms"] for r in selected if "error" not in r)
        costs = [r["estimated_cost_usd"] for r in selected if r.get("estimated_cost_usd") is not None]
        item = {
            "requests": len(selected), "errors": sum("error" in r for r in selected),
            "accuracy": sum(r.get("route") == r["expected"] for r in selected) / len(selected),
            "accuracy_on_completed": (sum(r.get("route") == r["expected"] for r in selected if "error" not in r)
                                      / sum("error" not in r for r in selected)) if any("error" not in r for r in selected) else None,
            "p50_ms": statistics.median(latencies) if latencies else None,
            "p95_ms": latencies[math.ceil(.95 * len(latencies)) - 1] if latencies else None,
            "estimated_cost_usd": sum(costs), "requests_with_known_cost": len(costs),
            "usd_per_1000_requests": 1000 * sum(costs) / len(selected) if len(costs) == len(selected) else None,
            "tasks": {},
        }
        for name, task in dataset["tasks"].items():
            group = [r for r in selected if r["task"] == name]
            if not group:
                continue
            details = score(group, task["criteria"])
            if "item_question" in task:
                details["component_accuracy"] = {
                    predicted: sum(r.get(predicted) == r[expected] for r in group) / len(group)
                    for predicted, expected in (
                        ("raw_route", "expected_raw_route"),
                        ("item_action", "expected_item_action"),
                        ("item", "expected_item"),
                    )
                }
                details["splits"] = {split: score([r for r in group if r["split"] == split], task["criteria"])
                                     for split in sorted({r["split"] for r in group})}
            details["slices"] = {s: score([r for r in group if r["slice"] == s], task["criteria"])
                                 for s in sorted({r["slice"] for r in group})}
            for slice_score in details["slices"].values():
                # A slice may contain only one class; full-taxonomy macro F1 is misleading there.
                del slice_score["macro_f1"]
            if "clarify" in task["criteria"] and any(r.get("confidence") is not None for r in group):
                details["confidence_floors"] = {str(f): score(group, task["criteria"], f) for f in (.5, .75, .9)}
            item["tasks"][name] = details
        summary[model] = item
    return summary


def self_check(dataset):
    from unittest.mock import patch

    validate_dataset(dataset)
    cfg = MODELS["jev"]
    good = {"answers": {"route": {"type": "choice", "choice": "order", "probabilities": {"order": .8, "clarify": .2}, "confidence": .4}}}
    assert parse_response(cfg, good, ["order", "clarify"])["route"] == "clarify"
    good["answers"]["route"]["confidence"] = .5
    assert parse_response(cfg, good, ["order", "clarify"])["route"] == "order"
    bad = json.loads(json.dumps(good))
    bad["answers"]["route"]["confidence"] = True
    try:
        parse_response(cfg, bad, ["order", "clarify"])
        raise RuntimeError("Boolean confidence accepted")
    except AssertionError:
        pass
    many = {"choice": "winner", "type": "choice", "confidence": .8,
            "probabilities": dict.fromkeys(["winner"] + [f"other_{i}" for i in range(76)], 0.)}
    many["probabilities"]["winner"] = .99
    assert parse_response(cfg, {"answers": {"route": many}}, many["probabilities"])["route"] == "winner"
    readiness = dataset["tasks"]["return_readiness"]
    item_probs = dict.fromkeys(readiness["item_criteria"], 0.0)
    item_probs.update(sport_earbuds=.93, travel_speaker=.04, unresolved=.02)  # Rounded sum: .99.
    item_response = {"answers": {
        "route": {"type": "choice", "choice": "returns", "probabilities": {"order": 0, "returns": 1, "clarify": 0}, "confidence": 1},
        "item_action": {"type": "noul", "noul": .95},
        "item": {"type": "choice", "choice": "sport_earbuds", "probabilities": item_probs, "confidence": .9},
    }}
    assert parse_response(cfg, item_response, readiness["criteria"], readiness["item_criteria"])["route"] == "returns"
    item_response["answers"]["item"]["confidence"] = .5
    assert parse_response(cfg, item_response, readiness["criteria"], readiness["item_criteria"])["route"] == "clarify"
    rows = [{"route": "order", "confidence": .4, "expected": "order"},
            {"route": "order", "confidence": .1, "expected": "clarify"}, {"error": "timeout", "expected": "order"}]
    raw, gated = score(rows, ["order", "clarify"]), score(rows, ["order", "clarify"], .5)
    assert raw["accuracy"] == 1 / 3 and raw["automatic_error_rate"] == .5
    assert gated["correct"] == 1 and gated["unnecessary_clarifications"] == 1 and gated["error_count"] == 1
    assert gated["automatic_error_rate"] is None
    assert estimated_cost(MODELS["openai-fast"], {"input_tokens": 1000, "output_tokens": 10,
           "input_tokens_details": {"cached_tokens": 500}}) == .00006
    assert estimated_cost(MODELS["openai-fast"], {"input_tokens": 1000, "output_tokens": 10,
           "input_tokens_details": {"cached_tokens": 500, "cache_write_tokens": 200}}) == .000065
    case = dataset["cases"][0]
    with patch.dict(os.environ, {"TYPESAFE_API_KEY": "mock-only"}), \
            patch("urllib.request.urlopen", side_effect=ConnectionResetError("reset")):
        assert call(cfg, dataset["tasks"][case["task"]], case)["error"] == "ConnectionResetError: reset"
    print(f"PASS: {len(dataset['cases'])} cases; parsing, errors, confidence policy and cached cost checks. No API calls.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--dataset", type=Path, default=ROOT / "eval_cases.json")
    parser.add_argument("--task", help="Task to evaluate; defaults to return_readiness when present, or use 'all'")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    dataset_bytes = args.dataset.read_bytes()
    dataset = json.loads(dataset_bytes)
    validate_dataset(dataset)
    task_name = args.task or ("return_readiness" if "return_readiness" in dataset["tasks"] else "all")
    if task_name != "all" and task_name not in dataset["tasks"]:
        parser.error("Unknown task: " + task_name)
    if args.check:
        self_check(dataset)
        return
    if args.repeats < 1 or (args.limit is not None and args.limit < 1):
        parser.error("--repeats and --limit must be positive")
    missing = sorted({MODELS[m]["key"] for m in args.models if not os.environ.get(MODELS[m]["key"])})
    if missing:
        parser.error("Missing environment variables: " + ", ".join(missing))
    out = args.out or ROOT / "eval_results" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=False)
    (out / "dataset.json").write_bytes(dataset_bytes)
    meta = {"started_at": datetime.now(timezone.utc).isoformat(), "models": {k: MODELS[k] for k in args.models},
            "dataset_sha256": hashlib.sha256(dataset_bytes).hexdigest(), "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "seed": args.seed, "repeats": args.repeats, "limit": args.limit, "task": task_name,
            "method": "Synthetic development diagnostic; sequential interleaved calls; no retries or warmup; HTTP round-trip latency; errors count as incorrect."}
    (out / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    cases = [case for case in dataset["cases"] if task_name == "all" or case["task"] == task_name][:args.limit]
    rng = random.Random(args.seed)
    jobs = [(rep, case) for rep in range(args.repeats) for case in cases]
    rng.shuffle(jobs)
    rows = []
    with (out / "results.jsonl").open("w") as file:
        for rep, case in jobs:
            models = list(args.models)
            rng.shuffle(models)
            for model in models:
                row = {k: case[k] for k in ("id", "task", "slice", "expected")}
                for key in ("expected_raw_route", "expected_item_action", "expected_item", "split"):
                    if key in case:
                        row[key] = case[key]
                row.update(model_key=model, repeat=rep, timestamp=datetime.now(timezone.utc).isoformat())
                row.update(call(MODELS[model], dataset["tasks"][case["task"]], case))
                rows.append(row)
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
                file.flush()
                print(f"{len(rows)}/{len(jobs) * len(models)} {model} {case['id']}: {row.get('route', row.get('error'))} ({row['latency_ms']:.0f} ms)", flush=True)
                if row.get("error") in ("HTTP 401", "HTTP 402", "HTTP 403", "HTTP 404", "HTTP 429"):
                    (out / "summary.json").write_text(json.dumps(summarize(rows, dataset), indent=2) + "\n")
                    raise SystemExit("Stopped after authentication, availability or quota failure; partial results retained.")
    (out / "summary.json").write_text(json.dumps(summarize(rows, dataset), indent=2) + "\n")
    print(f"Saved raw responses and summary: {out}")


if __name__ == "__main__":
    main()
