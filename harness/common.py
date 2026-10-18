"""Common harness utilities: Nous API caller, prompt builders, answer parsing.
Rerun (Oct 17 2026): durable home, long-lived key, raw-reply logging, parser fix
  (answer calls use max_tokens=256 — glm-5.3-flash burns reasoning tokens first and
   returns content=None when the budget is small; that bug invalidated the previous
   n=50 arms A/B).
"""
import json, os, time, urllib.request, random

NOUS_KEY = os.environ["NOUS_API_KEY"]
NOUS_URL = "https://inference-api.nousresearch.com/v1/chat/completions"
ANSWER_MODEL = "z-ai/glm-5.3-flash"   # answer model, same across all arms
EXTRACT_MODEL = "z-ai/glm-5.3"        # extraction model (arm B curation + arm C pipeline)
BENCH = os.environ.get("BENCH_DIR",
       os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GW_SEED = "http://127.0.0.1:8420"     # shared seeding gateway
GW2 = "http://127.0.0.1:8421"         # per-persona recall gateway

def nous_call(messages, model=ANSWER_MODEL, max_tokens=256, temperature=0.0, retries=4):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens,
            "temperature": temperature}
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(NOUS_URL, data=json.dumps(body).encode(),
                                         headers={"Authorization": "Bearer " + NOUS_KEY,
                                                  "Content-Type": "application/json"})
            t0 = time.time()
            r = urllib.request.urlopen(req, timeout=600)
            d = json.loads(r.read())
            msg = d["choices"][0]["message"]
            usage = d.get("usage", {})
            return {"text": msg.get("content"),
                    "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                    "finish_reason": d["choices"][0].get("finish_reason"),
                    "usage": {"pt": usage.get("prompt_tokens"), "ct": usage.get("completion_tokens"),
                              "cost": usage.get("cost")},
                    "secs": round(time.time() - t0, 1)}
        except Exception as e:
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"nous_call failed after {retries}: {last}")

def load_rows():
    return json.load(open(f"{BENCH}/sample_rows50.json"))

def load_history(row):
    fn = os.path.basename(row["chat_history_32k_link"])
    h = json.load(open(f"{BENCH}/hist50/{fn}"))
    return [m for m in h["chat_history"] if m["role"] != "system"]

def transcript(msgs, turn_numbers=True):
    lines = []
    for i, m in enumerate(msgs):
        who = "User" if m["role"] == "user" else "Assistant"
        prefix = f"[{i}] " if turn_numbers else ""
        lines.append(f"{prefix}{who}: {m['content']}")
    return "\n\n".join(lines)

def build_options(row):
    """Shuffle correct + incorrect answers into A-D. Deterministic per row."""
    rng = random.Random("persona" + row["persona_id"] + row["user_query"][:40])
    opts = [{"text": row["correct_answer"], "correct": True}]
    inc = row["incorrect_answers"]
    if isinstance(inc, str):
        inc = json.loads(inc)
    for t in inc:
        opts.append({"text": t, "correct": False})
    rng.shuffle(opts)
    return opts

def answer_prompt(context_block, row, options, block_label="CONTEXT"):
    q = row["user_query"]
    if isinstance(q, dict):
        q = q.get("content", json.dumps(q))
    letters = ["A", "B", "C", "D"]
    opt_str = "\n".join(f"{letters[i]}) {o['text']}" for i, o in enumerate(options[:4]))
    return f"""You are answering a question about a specific user. You are given a {block_label} about this user (their preferences, habits, and history).

<{block_label}>
{context_block}
</{block_label}>

Question from the user: {q}

{opt_str}

Pick the answer that best matches this specific user. Respond with ONLY the letter (A, B, C, or D) of the best answer. No other text."""

def parse_letter(text):
    if not text:
        return None
    t = text.strip().upper()
    for ch in t:
        if ch in "ABCD":
            return ch
    return None

def answer_with_retry(messages, log_extra=None):
    """Answer call with the parser fix: 2048-token budget (glm-5.3-flash reasons
    ~1200 tokens on long prompts and starves smaller budgets to content=None;
    'thinking-disabled' params are ignored by this API); one retry at 8192.
    Returns (letter, call_record). Raw text always recorded."""
    tiers = [2048, 8192, 24576]
    r = nous_call(messages, max_tokens=tiers[0])
    letter = parse_letter(r["text"])
    for tier in tiers[1:]:
        if letter is not None:
            break
        r2 = nous_call(messages, max_tokens=tier)
        letter = parse_letter(r2["text"])
        r = {"text": r2["text"], "finish_reason": r2["finish_reason"],
             "reasoning_tokens": r2["reasoning_tokens"],
             "usage": {"pt": (r["usage"]["pt"] or 0) + (r2["usage"]["pt"] or 0),
                       "ct": (r["usage"]["ct"] or 0) + (r2["usage"]["ct"] or 0),
                       "cost": (r["usage"]["cost"] or 0) + (r2["usage"]["cost"] or 0)},
             "secs": r["secs"] + r2["secs"], "retried": True}
    rec = {"raw": (r["text"] or "")[:200], "finish": r["finish_reason"],
           "reasoning": r["reasoning_tokens"], "usage": r["usage"], "secs": r["secs"]}
    if r.get("retried"):
        rec["retried"] = True
    if log_extra:
        rec.update(log_extra)
    return letter, rec

def append_jsonl(path, obj):
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")

def done_personas(path):
    """Personas already scored in a results file — rows without 'error' AND with a
    parsed letter (unparseable rows get re-run on resume, not skipped)."""
    if not os.path.exists(path):
        return set()
    out = set()
    for line in open(path):
        try:
            r = json.loads(line)
        except Exception:
            continue
        if "error" not in r and r.get("picked") is not None and r.get("persona") is not None:
            out.add(str(r["persona"]))
    return out
