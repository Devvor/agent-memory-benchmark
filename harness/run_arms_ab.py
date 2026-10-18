"""Arms A and B (n=50): raw-context baseline vs our curation-style compact memory.
Fixes vs the dead Oct-15 run: answers via answer_with_retry (parser fix, raw text
logged), resumable, per-call cost recorded.
Usage: python3 run_arms_ab.py [limit]   (limit=N runs first N personas, for smoke test)
"""
import json, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BENCH, load_rows, load_history, transcript, build_options,
                   answer_prompt, nous_call, answer_with_retry, append_jsonl,
                   done_personas)

limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
rows = load_rows()
if limit:
    rows = rows[:limit]
outA, outB = f"{BENCH}/armA50.jsonl", f"{BENCH}/armB50.jsonl"
doneA, doneB = done_personas(outA), done_personas(outB)

CURATE_PROMPT = """You are the memory curator for an AI assistant. Below is the full chat history between a user and the assistant. Distill it into a COMPACT CURATED MEMORY of this user — the kind of memory file a thoughtful assistant would keep between sessions.

Rules:
- Capture: stable preferences, habits, tastes, identity facts, relationships, goals, health/diet details, and anything the user asked to remember or asked to FORGET (explicit "please remember/forget" requests are highest priority).
- Prefer concrete specifics over generalities ("drinks oolong tea every morning" beats "likes tea").
- If the user asked to forget something, note it as: [FORGET: <thing>] and do NOT store the underlying detail.
- One bullet per fact, most durable/important first. Max 60 bullets.
- Do NOT include assistant small-talk or generic advice — only facts about THIS user.
- Output ONLY the memory bullets, no preamble.

CHAT HISTORY:
"""

for idx, row in enumerate(rows):
    pid = str(row["persona_id"])
    if pid in doneA and pid in doneB:
        continue
    t0 = time.time()
    msgs = load_history(row)
    ts = transcript(msgs)
    options = build_options(row)
    letters = ["A", "B", "C", "D"]
    correct_letter = letters[[i for i, o in enumerate(options) if o["correct"]][0]]

    if pid not in doneA:
        try:
            prA = answer_prompt(ts, row, options, block_label="chat history with this user")
            letterA, recA = answer_with_retry([{"role": "user", "content": prA}])
            append_jsonl(outA, {"persona": pid, "correct_letter": correct_letter,
                                "picked": letterA, "ok": letterA == correct_letter,
                                "answer": recA, "ctx_chars": len(ts)})
            print(f"[A] persona {pid}: picked={letterA} correct={correct_letter} ok={letterA==correct_letter} raw={recA['raw'][:30]!r}", flush=True)
        except Exception as e:
            append_jsonl(outA, {"persona": pid, "error": str(e)[:200]})
            print(f"[A] persona {pid}: ERROR {str(e)[:120]}", flush=True)

    if pid not in doneB:
        try:
            mem = ""
            for extract_mt in (2000, 32768, 65536):
                rE = nous_call([{"role": "user", "content": CURATE_PROMPT + ts}],
                               model="z-ai/glm-5.3", max_tokens=extract_mt)
                mem = rE["text"] or ""
                if mem.strip():
                    break
            if not mem.strip():
                raise RuntimeError("curation returned empty memory after retries")
            append_jsonl(f"{BENCH}/armB50_memory.jsonl", {"persona": pid, "memory": mem})
            prB = answer_prompt(mem, row, options, block_label="curated memory of this user")
            letterB, recB = answer_with_retry([{"role": "user", "content": prB}])
            append_jsonl(outB, {"persona": pid, "correct_letter": correct_letter,
                                "picked": letterB, "ok": letterB == correct_letter,
                                "answer": recB, "mem_chars": len(mem),
                                "extract_usage": rE["usage"]})
            print(f"[B] persona {pid}: picked={letterB} correct={correct_letter} ok={letterB==correct_letter} mem_chars={len(mem)}", flush=True)
        except Exception as e:
            append_jsonl(outB, {"persona": pid, "error": str(e)[:200]})
            print(f"[B] persona {pid}: ERROR {str(e)[:120]}", flush=True)

    print(f"--- persona {pid} done in {time.time()-t0:.0f}s ({idx+1}/{len(rows)})", flush=True)

print("ARMS A+B COMPLETE", flush=True)
