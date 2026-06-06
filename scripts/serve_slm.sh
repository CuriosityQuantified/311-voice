#!/usr/bin/env bash
# Launch the local SLM (Qwen3.5-2B) as an OpenAI-compatible server for the bake-off / demo.
# SLMBackend (app/llm/slm.py) talks to http://localhost:8080/v1/chat/completions.
#
#   ./scripts/serve_slm.sh
#
# Requires llama.cpp's llama-server (brew install llama.cpp) and the gguf in models/.
set -euo pipefail

cd "$(dirname "$0")/.."
MODEL="${SLM_MODEL:-models/Qwen3.5-2B-UD-IQ2_M.gguf}"
PORT="${SLM_PORT:-8080}"

exec llama-server \
  -m "$MODEL" \
  --host 127.0.0.1 --port "$PORT" \
  -c 4096 -ngl 99 --temp 0
