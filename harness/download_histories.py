"""Download the 50 selected persona chat histories (32k) from HuggingFace."""
import json, os, urllib.request

BENCH = os.environ.get("BENCH_DIR",
       os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = "https://huggingface.co/datasets/bowen-upenn/PersonaMem-v2/resolve/main/"
sel = json.load(open(f"{BENCH}/sample_rows50.json"))
os.makedirs(f"{BENCH}/hist50", exist_ok=True)

ok, fail = 0, 0
for i, row in enumerate(sel):
    rel = row["chat_history_32k_link"]
    dest = f"{BENCH}/hist50/{os.path.basename(rel)}"
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        ok += 1
        continue
    try:
        req = urllib.request.Request(BASE + rel, headers={"User-Agent": "agent-memory-benchmark"})
        data = urllib.request.urlopen(req, timeout=120).read()
        open(dest, "wb").write(data)
        ok += 1
        print(f"[{i+1}/50] {os.path.basename(rel)} {len(data)} bytes", flush=True)
    except Exception as e:
        fail += 1
        print(f"[{i+1}/50] FAIL {rel}: {str(e)[:120]}", flush=True)
print(f"DONE ok={ok} fail={fail}")
