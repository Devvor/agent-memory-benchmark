# agent-memory-benchmark

**One-pass curated memory vs. layered auto-extraction — a head-to-head on [PersonaMem-v2](https://huggingface.co/datasets/bowen-upenn/PersonaMem-v2), the benchmark TencentDB Agent Memory cites for its own 48%→76% claim.**

We benchmarked three memory strategies on the same 50 personas, same questions, same answer model:

| Arm | Strategy | Accuracy | 95% CI | Build cost (LLM passes / persona) |
|---|---|---|---|---|
| **A** | Raw 32k-token chat history in the prompt | **74%** | [60%, 84%] | 0 |
| **B** | One-pass curated memory (~1.3k tokens) | **70%** | [56%, 81%] | 1 |
| **C** | TencentDB Agent Memory (npm `@tencentdb-agent-memory/memory-tencentdb` v1.0.3) | **40%** | [28%, 54%] | ~26 |

**Key findings**

- Curated one-pass memory vs. their five-layer pipeline (L0→L1→L2→L3): **70% vs 40%, z = 3.02, p = 0.0026** — non-overlapping 95% CIs.
- The raw-context baseline (the "dumbest possible memory system") beat their pipeline at **p = 0.0006**.
- Curation matched raw context at p = 0.66 — **zero quality loss for a ~30× token reduction per question** (1.3k vs 43k input tokens), but the real argument over raw context is cost/latency at deployment scale, not accuracy.
- Their pipeline burned ~26 LLM extraction passes per persona to build its store; the curation arm uses exactly one. Ironically, the memory system's *build cost* was ~80% of this entire benchmark's API bill.

Full numbers with per-arm token/cost accounting: [`RESULTS50.json`](RESULTS50.json). Per-arm answer logs are in the harness output files (see Reproduce).

## Methodology

- **Dataset**: [PersonaMem-v2](https://huggingface.co/datasets/bowen-upenn/PersonaMem-v2) (CC-BY-4.0, UPenn) — 5,000 test queries across 200 unique personas, each with a ~32k-token synthetic chat history. We deterministically sampled **50 unique personas, one query row each** (sample seed `20261017`, see `harness/select_rows.py`).
- **Task format**: multiple-choice — the persona's question with 1 correct + 3 incorrect answers, shuffled deterministically per row.
- **Answer model (all arms)**: `z-ai/glm-5.3-flash`, temperature 0.
- **Extraction model (arm B curation and arm C pipeline LLM)**: `z-ai/glm-5.3` — *the same model for both*, so extraction quality differences are not confounded.
- **Arm B prompt**: a single "memory curator" distillation pass (max 60 bullets, explicit remember/forget instructions) — see `harness/run_arms_ab.py`. This models a lean, deliberate, human-readable memory file, not a product.
- **Arm C setup**: their published npm package run standalone via its bundled gateway (`src/gateway/server.ts`): per-persona seeding, hybrid recall (BM25 + bge-m3 embeddings), full pipeline enabled. Same Nous inference endpoint and extraction model as arm B.

### A benchmarking gotcha worth documenting

Our first full run produced collapsed scores (36-40%) that were **an artifact, not a finding**: the answer model burns ALL of `max_tokens` on hidden reasoning before emitting text (`content: null`, `finish_reason: length`), and `thinking: disabled`-style parameters were ignored by the endpoint. Small answer budgets (8-1024 tokens) silently return empty text, which scores as *wrong*. The fix used here: a tiered answer budget (2048 → 8192 → 24576) with raw-reply logging and `finish_reason` recorded per call; unparseable rows are re-run, never silently scored. The final run has **zero unparseable answers across all 150 scored calls**.

## Honest caveats

- **n=50** of the dataset's 200 unique personas (one query each). The CIs are reported so you can judge the separation yourself; treat 40-74% as the honest range per arm.
- **Model substitution**: arm C ran TencentDB Agent Memory with *our* inference models (`z-ai/glm-5.3` for its pipeline), not its defaults — we tested the **architecture**, not their exact hosted configuration.
- **Standalone mode**: we ran the npm package's standalone gateway, not its OpenClaw integration (the context of their headline token savings). One-shot recall per persona.
- **Single dataset, single answer model**: this is a datapoint, not a survey. We have not benchmarked Mem0, Zep, MemGPT/Letta, or other memory systems here.
- Arm B is a *design probe* (one curation prompt), not a production memory system.

## Cost

Total API cost for the full n=50 run: **~$13**. Breakdown by line item is embedded per-answer in the harness outputs (`usage.cost` fields); the dominant line (~80%) was arm C's pipeline seeding, at ~$0.20-0.25 of extraction tokens per persona.

## Reproduce

Requires Python 3.10+, Node >= 22, and an OpenAI-compatible inference endpoint key.

```bash
git clone https://github.com/Devvor/agent-memory-benchmark.git
cd agent-memory-benchmark
export NOUS_API_KEY=<your key>          # or edit harness/common.py for your endpoint
export NOUS_URL=<your chat/completions URL>

# 1. fetch dataset + select the same 50 personas
python3 harness/download_benchmark.py   # or download manually (see below)
python3 harness/select_rows.py
python3 harness/download_histories.py

# 2. arms A+B (raw vs curated)
python3 harness/run_arms_ab.py

# 3. arm C (TencentDB): install their package + seed + recall
npm install --no-audit --no-fund @tencentdb-agent-memory/memory-tencentdb
bash harness/seed_all50.sh
python3 harness/run_arm_c50.py

# 4. tally with Wilson CIs
python3 harness/tally.py
```

The dataset CSV lives at `benchmark/text/benchmark.csv` inside the [HF dataset](https://huggingface.co/datasets/bowen-upenn/PersonaMem-v2) (`data/chat_history_32k/` holds the histories). `sample_rows50.json` (committed here) pins the exact 50 rows used.

## License & credits

- This repository (harness, methodology, results): **MIT**.
- [PersonaMem-v2](https://huggingface.co/datasets/bowen-upenn/PersonaMem-v2): CC-BY-4.0, by the PersonaMem authors (UPenn). Synthetic, pseudonymized data; not real user data.
- TencentDB Agent Memory is a product of Tencent; this repo is an independent benchmark and is not affiliated with or endorsed by them. Its package was used as published on npm.
