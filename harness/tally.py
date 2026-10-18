"""Tally arm results (n=50): accuracy, Wilson 95% CI, unparseable count, token+cost totals.
Writes RESULTS50.json. Run after arms complete."""
import json, math, os, sys

BENCH = os.environ.get("BENCH_DIR",
       os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0, center - half), min(1, center + half))

def tally(path):
    if not os.path.exists(path):
        return None
    rows = [json.loads(l) for l in open(path)]
    errs = [r for r in rows if "error" in r]
    scored = [r for r in rows if "error" not in r]
    ok = sum(1 for r in scored if r.get("ok"))
    unparseable = sum(1 for r in scored if r.get("picked") in (None, ""))
    cost = sum((r.get("answer") or {}).get("usage", {}).get("cost") or 0 for r in scored)
    cost += sum((r.get("extract_usage") or {}).get("cost") or 0 for r in scored)
    pt = sum((r.get("answer") or {}).get("usage", {}).get("pt") or 0 for r in scored)
    ct = sum((r.get("answer") or {}).get("usage", {}).get("ct") or 0 for r in scored)
    lo, hi = wilson(ok, len(scored))
    return {"n": len(scored), "errors": len(errs), "ok": ok,
            "acc": round(ok / len(scored), 3) if scored else None,
            "ci95": [round(lo, 3), round(hi, 3)],
            "unparseable": unparseable, "cost_usd": round(cost, 4),
            "ptokens": pt, "ctokens": ct}

res = {"armA_raw_context": tally(f"{BENCH}/armA50.jsonl"),
       "armB_curated": tally(f"{BENCH}/armB50.jsonl"),
       "armC_tencentdb": tally(f"{BENCH}/armC50.jsonl")}
res["methodology"] = {
    "dataset": "PersonaMem-v2 (bowen-upenn, HuggingFace), benchmark/text/benchmark.csv",
    "selection": "50 unique personas, one query row each, deterministic sample seed 20261017",
    "answer_model": "z-ai/glm-5.3-flash, max_tokens=2048 (fixes content=None reasoning starvation; thinking-disable params ignored by API)",
    "extract_model": "z-ai/glm-5.3 (arm B curation pass; arm C TencentDB pipeline LLM)",
    "tencentdb": "npm @tencentdb-agent-memory/memory-tencentdb, standalone gateway, "
                 "bm25+bge-m3 embeddings, same extract model as arm B",
    "run_date": "2026-10-17/18"}
json.dump(res, open(f"{BENCH}/RESULTS50.json", "w"), indent=1)
print(json.dumps(res, indent=1))
