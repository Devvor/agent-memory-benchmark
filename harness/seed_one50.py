"""Seed one persona (by index into sample_rows50.json) into the TDAI gateway via POST /seed.
Hardened: 45-min client timeout with automatic salvage — their gateway has a known bug
where extraction completes but the HTTP response hangs; on timeout we scan the data dir
for a seed dir whose records mention this persona, and adopt it.
Writes tdai-gateway.json (bm25 + bge-m3 embeddings via Nous) into the seed output dir.
"""
import glob, json, os, re, sys, time, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import BENCH, GW_SEED, load_rows, load_history

idx = int(sys.argv[1])
rows = load_rows()
row = rows[idx]
pid = str(row["persona_id"])

def http_json(method, url, body=None, timeout=45):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"}, method=method)
    r = urllib.request.urlopen(req, timeout=timeout)
    return json.loads(r.read())

msgs = load_history(row)
rounds, cur = [], []
for m in msgs:
    cur.append({"role": m["role"], "content": m["content"]})
    if m["role"] == "assistant":
        rounds.append(cur); cur = []
if cur:
    rounds.append(cur)

body = {"data": {"sessions": [{"sessionKey": f"persona{pid}", "conversations": rounds}]},
        "config_override": {"bm25": {"language": "en"}}}

out_path = f"{BENCH}/seeds50/seed_{idx:02d}.json"
if os.path.exists(out_path):
    print("ALREADY SEEDED", open(out_path).read(), flush=True)
    sys.exit(0)

t0 = time.time()
try:
    resp = http_json("POST", GW_SEED + "/seed", body, timeout=2700)
    out_dir = resp.get("output_dir")
    out = {"persona": pid, "output_dir": out_dir,
           "rounds": resp.get("rounds_processed"), "l0": resp.get("l0_recorded"),
           "secs": round(time.time() - t0, 1), "idx": idx}
except Exception as e:
    # salvage: their gateway may have finished writing but hung on the HTTP response
    print(f"TIMEOUT/ERR after {time.time()-t0:.0f}s: {str(e)[:150]} — salvaging", flush=True)
    cands = []
    for d in sorted(glob.glob(f"{BENCH}/tdai-data50/seed-*"), key=os.path.getmtime, reverse=True)[:6]:
        recs = glob.glob(os.path.join(d, "records", "*")) + glob.glob(os.path.join(d, "conversations", "*"))
        blob = " ".join(open(f, errors="ignore").read() for f in recs[:2])
        if blob.count(f"persona{pid}") >= 10:
            cands.append(d)
    if not cands:
        out = {"persona": pid, "idx": idx, "error": f"seed failed and no salvage dir: {str(e)[:150]}"}
    else:
        out = {"persona": pid, "output_dir": cands[0], "idx": idx,
               "salvaged": True, "secs": round(time.time() - t0, 1)}
        print(f"SALVAGED -> {cands[0]}", flush=True)

if out.get("output_dir"):
    EMB = {"enabled": True, "provider": "openai",
           "baseUrl": "https://inference-api.nousresearch.com/v1",
           "apiKey": os.environ["NOUS_API_KEY"],
           "model": "baai/bge-m3", "dimensions": 1024, "sendDimensions": False}
    json.dump({"memory": {"bm25": {"language": "en"}, "embedding": EMB}},
              open(os.path.join(out["output_dir"], "tdai-gateway.json"), "w"))

json.dump(out, open(out_path, "w"))
print("SEEDED", json.dumps(out), flush=True)
