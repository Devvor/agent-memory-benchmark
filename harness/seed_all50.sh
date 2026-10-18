#!/bin/bash
# Arm C step 1: start the TDAI seed gateway (port 8420), then seed all 50 personas,
# 10 concurrent, staggered. Resumable (seed_one50.py skips already-seeded).
# Everything persists in the repo checkout (durable).
set -u
B="$(cd "$(dirname "$0")/.." && pwd)"
PLUG=$B/node_modules/@tencentdb-agent-memory/memory-tencentdb
mkdir -p "$B/tdai-data50" "$B/seeds50"

# gateway up?
if ! curl -sf http://127.0.0.1:8420/health > /dev/null 2>&1; then
  echo "starting TDAI seed gateway on :8420"
  ( cd "$PLUG" && TDAI_DATA_DIR="$B/tdai-data50" TDAI_GATEWAY_PORT=8420 TDAI_GATEWAY_HOST=127.0.0.1 \
      TDAI_LLM_BASE_URL=https://inference-api.nousresearch.com/v1 \
      TDAI_LLM_API_KEY="$NOUS_API_KEY" TDAI_LLM_MODEL=z-ai/glm-5.3 TDAI_LLM_MAX_TOKENS=8192 \
      "$B/node_modules/.bin/tsx" src/gateway/server.ts > "$B/logs/gateway_seed.log" 2>&1 ) &
  for i in $(seq 1 60); do
    sleep 2
    curl -sf http://127.0.0.1:8420/health > /dev/null 2>&1 && break
  done
fi
curl -sf http://127.0.0.1:8420/health || { echo "GATEWAY FAILED TO START"; exit 1; }
echo "gateway healthy"

cd "$B"
for i in $(seq 0 49); do
  python3 harness/seed_one50.py $i > "seeds50/seed_$i.log" 2>&1 &
  # throttle: max 10 concurrent
  while [ "$(jobs -rp | wc -l)" -ge 10 ]; do sleep 5; done
  sleep 2
done
wait
ok=$(ls seeds50/seed_*.json 2>/dev/null | wc -l)
echo "SEEDING DONE: $ok/50 seed jsons" | tee seeds50/ALL_DONE
