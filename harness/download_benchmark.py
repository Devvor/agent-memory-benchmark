"""Download the PersonaMem-v2 benchmark CSV (~42MB) from HuggingFace (CC-BY-4.0)."""
import os, urllib.request

BENCH = os.environ.get("BENCH_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
URL = "https://huggingface.co/datasets/bowen-upenn/PersonaMem-v2/resolve/main/benchmark/text/benchmark.csv"
os.makedirs(f"{BENCH}/data", exist_ok=True)
dest = f"{BENCH}/data/benchmark.csv"
if os.path.exists(dest) and os.path.getsize(dest) > 1e6:
    print("already present:", dest)
else:
    req = urllib.request.Request(URL, headers={"User-Agent": "agent-memory-benchmark"})
    data = urllib.request.urlopen(req, timeout=300).read()
    open(dest, "wb").write(data)
    print("downloaded", len(data), "bytes ->", dest)
