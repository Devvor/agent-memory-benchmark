"""Arm C (n=50): recall from each persona's seeded TDAI store + answer with the same
flash model as arms A/B. Per-persona gateway on :8421 (killed after each persona).
Resumable; parser fix; raw text logged; 5-min recall timeout.
Usage: python3 run_arm_c50.py [limit]
"""
import glob, json, os, signal, subprocess, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BENCH, GW2, NOUS_KEY, load_rows, build_options, answer_prompt,
                    answer_with_retry, append_jsonl, done_personas)

PLUGIN = f"{BENCH}/node_modules/@tencentdb-agent-memory/memory-tencentdb"
TSX = f"{BENCH}/node_modules/.bin/tsx"
outC = f"{BENCH}/armC50.jsonl"

def http_json(method, url, body=None, timeout=300):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"}, method=method)
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read())

def wait_health(timeout=120):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            d = http_json("GET", GW2 + "/health", timeout=5)
            if d.get("status") in ("ok", "degraded"):
                return True
        except Exception:
            time.sleep(2)
    return False

limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
rows = load_rows()
if limit:
    rows = rows[:limit]
doneC = done_personas(outC)
print(f"arm C n=50: {len(doneC)} already done, {len(rows) - len(doneC & {str(r['persona_id']) for r in rows})} to run", flush=True)

for idx, row in enumerate(rows):
    pid = str(row["persona_id"])
    if pid in doneC:
        continue
    seed_path = f"{BENCH}/seeds50/seed_{idx:02d}.json"
    if not os.path.exists(seed_path):
        append_jsonl(outC, {"persona": pid, "error": "no seed json (seeding incomplete)"})
        print(f"[C] persona {pid}: no seed", flush=True)
        continue
    seed = json.load(open(seed_path))
    data_dir = seed.get("output_dir")
    if not data_dir or not os.path.isdir(data_dir):
        append_jsonl(outC, {"persona": pid, "error": f"seed dir missing: {data_dir}"})
        print(f"[C] persona {pid}: seed dir missing", flush=True)
        continue

    logf = open(f"{BENCH}/logs/recall_gw_{idx:02d}.log", "w")
    env = dict(os.environ)
    env.update({"TDAI_DATA_DIR": data_dir, "TDAI_GATEWAY_PORT": "8421",
                "TDAI_GATEWAY_HOST": "127.0.0.1",
                "TDAI_LLM_BASE_URL": "https://inference-api.nousresearch.com/v1",
                "TDAI_LLM_API_KEY": NOUS_KEY, "TDAI_LLM_MODEL": "z-ai/glm-5.3",
                "TDAI_LLM_MAX_TOKENS": "8192"})
    proc = subprocess.Popen([TSX, "src/gateway/server.ts"], cwd=PLUGIN, env=env,
                            stdout=logf, stderr=subprocess.STDOUT)
    try:
        if not wait_health():
            append_jsonl(outC, {"persona": pid, "error": "recall gateway failed to start"})
            print(f"[C] persona {pid}: gateway failed", flush=True)
            continue

        options = build_options(row)
        letters = ["A", "B", "C", "D"]
        correct_letter = letters[[i for i, o in enumerate(options) if o["correct"]][0]]
        q = row["user_query"]
        if isinstance(q, dict):
            q = q.get("content", json.dumps(q))

        recall = http_json("POST", GW2 + "/recall",
                           {"query": q, "session_key": f"persona{pid}"}, timeout=300)
        ctx = recall.get("context") or ""
        append_jsonl(f"{BENCH}/armC50_recall.jsonl",
                     {"persona": pid, "context": ctx[:4000],
                      "memory_count": recall.get("memory_count"), "strategy": recall.get("strategy")})
        pmd = ""
        pmd_path = os.path.join(data_dir, "persona.md")
        if os.path.exists(pmd_path):
            pmd = open(pmd_path).read()

        pr = answer_prompt(ctx, row, options, block_label="recalled memory of this user")
        letterC, rec = answer_with_retry([{"role": "user", "content": pr}])
        append_jsonl(outC, {"persona": pid, "correct_letter": correct_letter,
                            "picked": letterC, "ok": letterC == correct_letter,
                            "answer": rec, "recall_chars": len(ctx),
                            "persona_md_chars": len(pmd)})
        print(f"[C] persona {pid}: picked={letterC} correct={correct_letter} "
              f"ok={letterC==correct_letter} recall_chars={len(ctx)} persona_md={len(pmd)}", flush=True)
    except Exception as e:
        append_jsonl(outC, {"persona": pid, "error": str(e)[:200]})
        print(f"[C] persona {pid}: ERROR {str(e)[:150]}", flush=True)
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()
        logf.close()

print("ARM C COMPLETE", flush=True)
