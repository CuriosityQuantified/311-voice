# 311-voice — Build Plan (Hackathon, ~4h)

Single source of truth for Claude + Hermes. Approach **A (safe vertical slice)** with a
**SLM-vs-Gemini accuracy bake-off** for the agent-reasoning step. Build **test-first (TDD)**.

Status: AWAITING USER APPROVAL. Do not write code until the user approves this plan.

## 1. Goal (the one demo that must work)

On an iPhone (Safari), speak a complaint → the app transcribes it, finds the correct
NYC 311 service via Pinecone (search + rerank), an LLM picks the best match and explains
why, the app fills a 311 form and **mock-submits** it, showing a confirmation with a fake
SR number. Served from the Mac over Tailscale.

## 2. Scope

**In:** voice input, Pinecone match+rerank, LLM pick (A/B), form, mock submit, iPhone via Tailscale.
**Cut to stretch (only if time):** whisper.cpp local STT, CopilotKit generative UI, GPS
auto-fill, photos, full top-5 reasoning UX, real API submission (NEVER submit for real).

## 3. Voice decision

Primary = **browser Web Speech API** (works in iOS Safari, zero backend, reliable in minutes).
Stretch = whisper.cpp local STT as the "fully local" upgrade.

## 4. Architecture / data flow

```
iPhone Safari → mic (Web Speech API) → transcript text
  → POST /api/match {text}
        → Pinecone search top_k=10 + rerank top_n=5   [SPONSOR: integrated inference + rerank]
        → LLM select_service(complaint, candidates) → picked_ka + reasoning   [A/B: SLM ‖ Gemini]
     ← {candidates[5], picked_ka, reasoning}
  → form (description, address, borough, apartment?, locationDetails?)
  → POST /api/submit {ka, fields}
        → map KA → {agency, problem, problemDetails, locationType} (data/311-mapping.json)
        → build CreateServiceRequest JSON → return mock SR#
     ← {sr_number, payload, status:"mock-submitted"}
  → confirmation screen
served via Tailscale → runs on the phone
```

## 5. The A/B LLM layer (key piece)

One interface, two swappable backends, selected by env `LLM_BACKEND=gemini|slm`:

```python
# app/llm/base.py
def select_service(complaint: str, candidates: list[Candidate]) -> Selection
# Selection = {picked_ka: str, reasoning: str, confidence: float}
```

- **GeminiBackend** — `google-genai` SDK, model **`gemini-3.1-flash-lite`**, reads
  `GEMINI_API_KEY` (fallback `GOOGLE_API_KEY`). Safe demo default.
  Reference: `scripts/ai_studio_code.py`.
- **SLMBackend** — llama.cpp `llama-server` (OpenAI-compatible `/v1/chat/completions`)
  serving `models/Qwen3.5-2B-UD-IQ2_M.gguf`. On-brand "fully local" contender.
- **FakeBackend** — deterministic, for unit tests (no network / no model).

### Bake-off methodology

- `data/eval-set.json` — ~25 hand-authored `{complaint, expected_ka}` pairs across common
  NYC complaints (heat, trash, pothole, noise, rats, mold, street light, parking, ...).
- `scripts/eval_llm.py` — for each eval item: run real match → candidates, then have each
  backend pick; compare picked_ka to expected_ka. Report **top-1 accuracy + avg latency**
  per backend, plus a per-item table.
- **Decision rule (default, override anytime):** use **SLM** for the demo if it scores
  **≥80% absolute AND within 10 points of Gemini**; otherwise **Gemini**.

## 6. Frozen API contract (so UI + backend build in parallel)

```
GET  /api/health  ⇒ {ok: true, llm_backend: "gemini"|"slm"}
POST /api/match   {text}
                  ⇒ {candidates: [{ka,title,description,score,classification}],
                     picked_ka, reasoning}
POST /api/submit  {ka, description, address, borough, apartment?, locationDetails?}
                  ⇒ {sr_number, payload, status: "mock-submitted"}
```

## 7. Components, owners, and TDD tests

| # | Component | Files | Owner | First tests (RED→GREEN) |
|---|---|---|---|---|
| 1 | Pinecone ingest + verify | `scripts/ingest_pinecone.py`, `scripts/query_pinecone.py` | Claude | query returns expected top match for "no heat" |
| 2 | `/api/match` | `app/match.py`, `app/main.py` | Claude | returns 5 candidates w/ scores; picked_ka ∈ candidates |
| 3 | LLM abstraction + backends | `app/llm/{base,gemini,slm,fake}.py` | Claude | FakeBackend selects highest-scored; Selection schema valid |
| 4 | `/api/submit` (mock) | `app/submit.py`, `app/mapping.py` | Claude | KA→fields mapping resolves; payload has required fields; returns sr_number |
| 5 | Eval harness | `scripts/eval_llm.py`, `data/eval-set.json` | Claude | accuracy computed correctly on a toy 2-item set |
| 6 | Mapping table | `data/311-mapping.json` | Hermes | every demo KA maps to a complete {agency,problem,problemDetails,locationType} |
| 7 | Frontend | `web/` (single page) | Hermes | manual UAT via Playwright: mic→match→form→submit→confirmation |
| 8 | Tailscale exposure | run scripts | Claude | iPhone loads page, full flow works |

TDD discipline: backend = vertical slices, one test → one impl, tests hit public
interfaces only, LLM tests use FakeBackend (no network). Frontend = pragmatic + Playwright UAT.

## 8. Dependencies / env

- `requirements.txt` (Hermes owns): add `google-genai`. Already has `pinecone`, `fastapi`,
  `uvicorn[standard]`, `langchain*`, `python-multipart`.
- `.env`: has `PINECONE_API_KEY`, `GOOGLE_API_KEY`. **Add `GEMINI_API_KEY`** (same value)
  OR rely on backend fallback. ⚠️ `GOOGLE_API_KEY` value format (`AQ.Ab8...`) is unusual —
  **verify it authenticates with a 5-sec test call before building the Gemini backend.**
- llama.cpp installed (`llama-server`); model in `models/` (gitignored).

## 9. Timeline (~240 min, 2 agents parallel)

| Time | Claude | Hermes |
|---|---|---|
| 0:00–0:20 | verify Gemini key; ingest 2,084 → Pinecone; verify rerank | finalize `311-mapping.json`; scaffold `web/` |
| 0:20–1:30 | `/api/match` + LLM abstraction + Gemini backend (TDD) | frontend: mic → results → form (against frozen contract w/ stub) |
| 1:30–2:15 | `/api/submit` (TDD); start `llama-server` + SLM backend | wire frontend ↔ real API; confirmation screen |
| 2:15–2:50 | eval harness; run SLM vs Gemini bake-off; pick winner | polish UI; Playwright UAT |
| 2:50–3:20 | Tailscale exposure; iPhone end-to-end test | fix UAT issues |
| 3:20–3:50 | stretch (whisper/SLM polish); rehearse demo | rehearse demo |
| 3:50–4:00 | FREEZE + buffer | FREEZE + buffer |

## 10. Coordination

- Protocol: `comms/README.md`; log: `comms/log.md`; live state: `.claude-progress.md`.
- CLAIM before editing shared files. The frozen API contract (§6) is the integration seam —
  do not change it without a HANDOFF note + the other agent's ack.
- Demo backend is chosen by the bake-off (§5), set via `LLM_BACKEND` env.

## 11. Definition of done (demo)

Speak → correct service identified → form filled → mock SR# shown, **on the iPhone over
Tailscale**, using whichever LLM backend won the bake-off. Pinecone visibly in the path
(sponsor). No real 311 submission.
