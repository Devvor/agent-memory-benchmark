"""Select 50 personas from PersonaMem-v2 benchmark.csv — deterministic.
Criteria: one query row per unique persona, must have a 32k chat-history link.
Random seed 20261017 (documented in RESULTS50.json methodology).
Writes sample_rows50.json + prints selection stats.
"""
import csv, json, random, sys

BENCH = os.environ.get("BENCH_DIR",
       os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
rows = list(csv.DictReader(open(f"{BENCH}/data/benchmark.csv", encoding="utf-8")))
print("total query rows:", len(rows))

# group by persona, keep first row per persona with a valid 32k link
by_persona = {}
for r in rows:
    if r.get("chat_history_32k_link", "").strip():
        by_persona.setdefault(r["persona_id"], r)
print("unique personas with 32k history:", len(by_persona))

rng = random.Random(20261017)
picked = rng.sample(sorted(by_persona.keys()), 50)
sel = [by_persona[p] for p in picked]
json.dump(sel, open(f"{BENCH}/sample_rows50.json", "w"))
print("selected:", len(sel))
print("persona ids:", " ".join(sorted(picked, key=int)))
toks = [int(r["total_tokens_in_chat_history_32k"]) for r in sel if r.get("total_tokens_in_chat_history_32k")]
if toks:
    print(f"32k-history token counts: min {min(toks)}, median {sorted(toks)[len(toks)//2]}, max {max(toks)}")
