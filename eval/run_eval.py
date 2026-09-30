"""Score the verifier on labeled letters and write a report.

    python eval/run_eval.py                 # offline: fake AWS + keyword reader -> eval/results-offline.md
    python eval/run_eval.py --live          # real Bedrock (text input, so no Textract) -> eval/results.md
    python eval/run_eval.py --set holdout   # only one set: dev | synthetic | holdout | all
    python eval/run_eval.py --set dev --set synthetic

Three sets, always reported separately:
  dev/       real published messages and notices used while tuning the rules (source URL in every file)
  holdout/   real messages and notices published by government bodies, never looked at while tuning
  synthetic/ letters from synthetic/generate.py (written by the same team that wrote the rules)

The rules are frozen: this script only calls POST /api/check and counts. It never changes thresholds, rules or
the registry, and it records a hash of the rules files (verifier, lexicon, contacts, agencies, pipeline) and
registry.json so a report can be tied to one rules version.
"""
import argparse
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from harness import BACKEND, LocalApi  # noqa: E402

DEFAULT_TODAY = "2026-09-30"
VERDICTS = ("likely_scam", "consistent_with_genuine", "cant_tell")
SETS = ("dev", "synthetic", "holdout")


def load_folder(name):
    cases = []
    for path in sorted((HERE / name).glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        case["set"] = name
        cases.append(case)
    return cases


def load_synthetic():
    path = HERE / "synthetic" / "letters.json"
    if not path.exists():
        sys.exit("eval/synthetic/letters.json is missing; run python eval/synthetic/generate.py first.")
    cases = json.loads(path.read_text(encoding="utf-8"))
    for case in cases:
        case["set"] = "synthetic"
    return cases


def rules_fingerprint():
    parts = []
    for name in ("verifier.py", "lexicon.py", "contacts.py", "agencies.py", "pipeline.py", "registry.json"):
        path = BACKEND / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12] if path.exists() else "missing"
        parts.append(f"{name} {digest}")
    return ", ".join(parts)


def run_case(api, case, index):
    # One documentation-range IP per letter so the per-IP hourly limit doesn't cut a local run short.
    status, body, ms = api.post("/api/check", {"image": None, "text": case["text"],
                                               "today": case.get("today", DEFAULT_TODAY)},
                                source_ip=f"198.51.100.{index % 250 + 1}")
    row = {"id": case["id"], "set": case["set"], "label": case["label"], "status": status, "ms": ms,
           "expected_deadline": case.get("expected_deadline"), "source_url": case.get("source_url")}
    if status != 200:
        row["error"] = body.get("error", str(body))
        return row
    meta = body.get("meta") or {}
    grounding = body.get("grounding") or {}
    row.update({
        "verdict": body.get("verdict"),
        "flags": [{"rule": f.get("rule"), "severity": f.get("severity"), "grounded": f.get("grounded")}
                  for f in body.get("flags") or []],
        "agency": (body.get("agency") or {}).get("key"),
        "deadlines": [d.get("date") for d in (body.get("extracted") or {}).get("deadlines") or []],
        "grounded": grounding.get("grounded", 0),
        "grounding_total": grounding.get("total", 0),
        "server_ms": meta.get("ms"),
        "input_tokens": meta.get("input_tokens") or 0,
        "output_tokens": meta.get("output_tokens") or 0,
        "model": meta.get("model"),
    })
    return row


def percentile(values, pct):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(pct / 100 * len(ordered)) - 1)]


def ratio(num, den):
    return f"{num}/{den} ({num / den:.0%})" if den else "n/a"


def summarize(rows):
    ok = [r for r in rows if r["status"] == 200]
    scams = [r for r in ok if r["label"] == "scam"]
    genuine = [r for r in ok if r["label"] == "genuine"]
    tp = sum(r["verdict"] == "likely_scam" for r in scams)
    fp = sum(r["verdict"] == "likely_scam" for r in genuine)
    dated = [r for r in ok if r.get("expected_deadline")]
    latencies = [r["ms"] for r in ok]
    return {
        "cases": len(rows),
        "errors": len(rows) - len(ok),
        "confusion": {label: {v: sum(r["verdict"] == v for r in ok if r["label"] == label) for v in VERDICTS}
                      for label in ("scam", "genuine")},
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, len(scams)),
        "scam_marked_consistent": sum(r["verdict"] == "consistent_with_genuine" for r in scams),
        "cant_tell": ratio(sum(r["verdict"] == "cant_tell" for r in ok), len(ok)),
        "genuine_consistent": ratio(sum(r["verdict"] == "consistent_with_genuine" for r in genuine), len(genuine)),
        "deadline_accuracy": ratio(sum(r["expected_deadline"] in r["deadlines"] for r in dated), len(dated)),
        "grounding": ratio(sum(r["grounded"] for r in ok), sum(r["grounding_total"] for r in ok)),
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "avg_input_tokens": round(statistics.mean(r["input_tokens"] for r in ok)) if ok else None,
        "avg_output_tokens": round(statistics.mean(r["output_tokens"] for r in ok)) if ok else None,
    }


def flag_list(row):
    return ", ".join(f"{f['rule']} ({f['severity']}{'' if f.get('grounded') is not False else ', ungrounded'})"
                     for f in row.get("flags") or []) or "none"


def misses(rows):
    out = []
    for r in rows:
        if r["status"] != 200:
            out.append((r, f"error {r['status']}: {r.get('error')}"))
        elif r["label"] == "scam" and r["verdict"] != "likely_scam":
            out.append((r, f"scam read as **{r['verdict']}**"))
        elif r["label"] == "genuine" and r["verdict"] == "likely_scam":
            out.append((r, "genuine letter read as **likely_scam**"))
        if r["status"] == 200 and r.get("expected_deadline") and r["expected_deadline"] not in r["deadlines"]:
            out.append((r, f"deadline: expected {r['expected_deadline']}, got {', '.join(filter(None, r['deadlines'])) or 'none'}"))
    return out


def render_set(name, rows, blurb):
    s = summarize(rows)
    lines = [f"## {name}", "", blurb, "",
             "| Metric | Value |", "|---|---|",
             f"| Letters | {s['cases']} ({s['errors']} errors) |",
             f"| Precision for likely_scam | {s['precision']} |",
             f"| Recall for likely_scam | {s['recall']} |",
             f"| Scam letters marked consistent_with_genuine (target 0) | **{s['scam_marked_consistent']}** |",
             f"| Can't tell rate (all letters) | {s['cant_tell']} |",
             f"| Genuine letters marked consistent_with_genuine | {s['genuine_consistent']} |",
             f"| Deadline accuracy (letters with a labeled deadline) | {s['deadline_accuracy']} |",
             f"| Quote grounding (grounded / checked quotes) | {s['grounding']} |",
             f"| Latency p50 / p95, /api/check wall clock | {s['p50_ms']} ms / {s['p95_ms']} ms |",
             f"| Average tokens in / out | {s['avg_input_tokens']} / {s['avg_output_tokens']} |",
             "", "| True label | likely_scam | consistent_with_genuine | cant_tell |", "|---|---|---|---|"]
    for label, counts in s["confusion"].items():
        lines.append(f"| {label} | " + " | ".join(str(counts[v]) for v in VERDICTS) + " |")
    lines += ["", f"### Misses ({name})", ""]
    found = misses(rows)
    if not found:
        lines.append("None.")
    for row, what in found:
        source = f" — [source]({row['source_url']})" if row.get("source_url") else ""
        lines.append(f"- `{row['id']}`: {what}. Flags: {flag_list(row)}{source}")
    unconfirmed = [r for r in rows if r["label"] == "genuine" and r.get("verdict") == "cant_tell"]
    if unconfirmed:
        lines += ["", f"Genuine letters left at cant_tell (safe direction, but not confirmed): {len(unconfirmed)}", ""]
        lines += [f"- `{r['id']}`: flags {flag_list(r)}" for r in unconfirmed]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true", help="call real Bedrock instead of the offline reader")
    parser.add_argument("--set", choices=["all", *SETS], action="append",
                        help="which set(s) to run; repeat to run several (default: all)")
    parser.add_argument("--out", help="report path (default eval/results.md live, eval/results-offline.md offline)")
    args = parser.parse_args()

    wanted = set(SETS) if not args.set or "all" in args.set else set(args.set)
    api = LocalApi(live=args.live)
    loaders = {"dev": lambda: load_folder("dev"), "synthetic": load_synthetic,
               "holdout": lambda: load_folder("holdout")}
    cases = [case for name in SETS if name in wanted for case in loaders[name]()]
    rows = []
    for index, case in enumerate(cases):
        row = run_case(api, case, index)
        rows.append(row)
        print(f"  {row['set']:9} {row['label']:8} {row.get('verdict') or row.get('error', '?'):24} {row['ms']:>6} ms  {row['id']}")

    when = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    models = sorted({r.get("model") for r in rows if r.get("model")})
    mode = ("live: Amazon Bedrock via the Converse API, text input (no Textract), models " + (", ".join(models) or "?")
            if args.live else
            "offline: AWS faked, extraction by the keyword reader in eval/mock_model.py. These numbers measure the "
            "deterministic rules plus a crude reader, not the model; latency and tokens are not meaningful")
    report = [
        "# Plainly evaluation", "",
        f"- Generated: {when}",
        f"- Mode: {mode}",
        f"- Rules under test (frozen, sha256 prefix): {rules_fingerprint()}",
        "- Positive class for precision/recall: `likely_scam`. \"Can't tell\" on a scam counts as a miss for recall, "
        "never as a pass.",
        "",
    ]
    if "dev" in wanted:
        report.append(render_set("Dev: government-published examples used for tuning",
                                 [r for r in rows if r["set"] == "dev"],
                                 "Real scam messages and genuine notices published by the FTC, GOV.UK, PIB Fact Check, "
                                 "I4C, DoT and the IRS. The rules were tuned against these, so they measure fit, not "
                                 "generalisation. See eval/README.md for sources."))
    if "holdout" in wanted:
        report.append(render_set("Holdout: government-published examples", [r for r in rows if r["set"] == "holdout"],
                                 "Real scam messages quoted by the IRS, FTC and FBI IC3, and IRS sample notices as "
                                 "genuine letters. Nothing here was written by us, and none of it was used to write "
                                 "the rules. See eval/README.md for sources and coverage gaps."))
    if "synthetic" in wanted:
        report.append(render_set("Synthetic: generated letters", [r for r in rows if r["set"] == "synthetic"],
                                 "24 letters from eval/synthetic/generate.py (12 genuine-format, 12 scam variants). "
                                 "Written by the same team as the rules, so treat these as a regression check, "
                                 "not as evidence of accuracy."))

    out = Path(args.out) if args.out else HERE / ("results.md" if args.live else "results-offline.md")
    out.write_text("\n".join(report), encoding="utf-8")
    raw = out.with_suffix(".json")
    raw.write_text(json.dumps({"generated_at": when, "live": args.live, "rows": rows}, indent=1) + "\n",
                   encoding="utf-8")
    print(f"wrote {out} and {raw}")


if __name__ == "__main__":
    main()
