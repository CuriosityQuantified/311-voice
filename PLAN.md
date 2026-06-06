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

**In:** voice input (Web Speech), Pinecone match+rerank, LLM pick (A/B), **CopilotKit
generative-UI form**, **GPS auto-fill (reverse geocode)**, **photo attach**, mock submit,
iPhone via Tailscale.
**Explicitly NOT building:** whisper.cpp local STT, full top-5 reasoning UX.
**Never:** real 311 API submission (mock only).

### Risk rule (CopilotKit is the long pole)

The **deterministic form path must work end-to-end FIRST** (target ~2:15) as the safety
net. CopilotKit generative UI is layered **on top of** that working slice. If CopilotKit
overruns, we demo with the plain form — the core demo is never put at risk by it. GPS and
photos are low-risk add-ons to the form.

## 3. Voice / STT decision

**STT model = Gemini audio** (multimodal), used for BOTH the 200-file accuracy test and
the live demo, so tested accuracy reflects the demo. Browser records audio (MediaRecorder)
→ backend → Gemini transcribes. (Web Speech API dropped — it can't transcribe the test
files; whisper.cpp excluded per user.) Note: STT is therefore cloud, not local.

Test set: `data/voice-files/` = 200 `sample_NNN.mp3` (edge-tts, 6 voices) + `sample_NNN.txt`
ground-truth transcripts, generated from category-labeled templates (heat/noise/pothole/
trash/rats/…), so we can derive expected category per sample.

## 4. Architecture / data flow

```
iPhone Safari → mic (Web Speech API) → transcript text
  → POST /api/match {text}
        → Pinecone search top_k=10 + rerank top_n=5   [SPONSOR: integrated inference + rerank]
        → LLM select_service(complaint, candidates) → picked_ka + reasoning   [A/B: SLM ‖ Gemini]
        → LLM extracts open-text fields from transcript (address text, apt, details)
     ← {candidates[5], picked_ka, reasoning, extracted_fields}
  → CopilotKit generative UI renders the 311 form (agent streams field values into it)
  → GPS: navigator.geolocation → reverse geocode → autofill address + borough
  → photo: camera/file capture → attached to submission (mock)
  → POST /api/submit {ka, fields, photo?}
        → map KA → {agency, problem, problemDetails, locationType} (data/311-mapping.json)
        → build CreateServiceRequest JSON → return mock SR#
     ← {sr_number, payload, status:"mock-submitted"}
  → confirmation screen
served via Tailscale → runs on the phone
(FALLBACK: if CopilotKit overruns, the form renders as a plain controlled form — same
fields, same /api/submit contract.)
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

- Eval set = `data/voice-files/` (200 samples). Derive `expected_category` per sample from
  the generator templates; map category → acceptable KA(s).
- **STT accuracy**: mp3 → Gemini STT → compare to `sample_NNN.txt` (exact / word-error).
- **End-to-end LLM accuracy**: transcript → real match (Pinecone) → each backend picks →
  compare picked_ka's category to `expected_category`.
- `scripts/eval_llm.py` reports, per backend, **top-1 accuracy + avg latency** + per-item
  table. STT accuracy reported once (single STT model).

**Tooling = LangSmith CLI** (`langsmith`, v0.2.34, at `~/.local/bin/langsmith`; reads
`.env` creds; project `311-voice` already exists). Use it to:
- Trace every match/STT/LLM call (`LANGSMITH_TRACING=true` already set) for debugging:
  `langsmith trace list --project 311-voice`, `langsmith run list --run-type llm`.
- Hold the eval set as a dataset and compare backends as experiments:
  `langsmith dataset ...`, `langsmith experiment list --dataset 311-voice-eval`.
- Debug failures by filtering traces (errors/latency) instead of print-debugging.
⚠️ Name collision: `/opt/homebrew/bin/langsmith` is the unrelated self-hosted-server
manager; the eval CLI must win PATH (it does — `~/.local/bin` is first).
- **Decision rule (default, override anytime):** use **SLM** for the demo if it scores
  **≥80% absolute AND within 10 points of Gemini**; otherwise **Gemini**.

## 6. Frozen API contract (so UI + backend build in parallel)

```
GET  /api/health   ⇒ {ok: true, llm_backend: "gemini"|"slm"}
POST /api/match    {text}
                   ⇒ {candidates: [{ka,title,description,score,classification}],
                      picked_ka, reasoning,
                      extracted_fields: {description, address?, apartment?, locationDetails?}}
POST /api/submit   {ka, description, address, borough, apartment?, locationDetails?, photo_b64?}
                   ⇒ {sr_number, payload, status: "mock-submitted"}
POST /api/copilotkit  (CopilotKit runtime endpoint; streams agent→generative-UI)
```

GPS reverse-geocode is a frontend concern (autofills `address`/`borough` before submit);
no backend route needed. Photo is sent as base64 in `/api/submit` (`photo_b64`) and just
echoed into the mock payload — not stored.

## 7. Components, owners, and TDD tests

| # | Component | Files | Owner | First tests (RED→GREEN) |
|---|---|---|---|---|
| 1 | Pinecone ingest + verify | `scripts/ingest_pinecone.py`, `scripts/query_pinecone.py` | Claude | query returns expected top match for "no heat" |
| 2 | `/api/match` | `app/match.py`, `app/main.py` | Claude | returns 5 candidates w/ scores; picked_ka ∈ candidates |
| 3 | LLM abstraction + backends | `app/llm/{base,gemini,slm,fake}.py` | Claude | FakeBackend selects highest-scored; Selection schema valid |
| 4 | `/api/submit` (mock) | `app/submit.py`, `app/mapping.py` | Claude | KA→fields mapping resolves; payload has required fields; returns sr_number |
| 5 | Eval harness | `scripts/eval_llm.py`, `data/eval-set.json` | Claude | accuracy computed correctly on a toy 2-item set |
| 6 | Mapping table | `data/311-mapping.json` | Hermes | every demo KA maps to a complete {agency,problem,problemDetails,locationType} |
| 7 | Frontend core (mic→match→**plain form**→submit→confirm) | `web/` | Hermes | manual UAT: full deterministic flow works (SAFETY NET — do first) |
| 8 | CopilotKit runtime endpoint | `app/copilot.py` (`/api/copilotkit`) | Claude | runtime responds; streams agent field values |
| 9 | CopilotKit generative-UI form | `web/` (CopilotKit hooks) | Hermes | agent-streamed form renders; falls back to plain form |
| 10 | GPS auto-fill | `web/` (geolocation + reverse geocode) | Hermes | lat/long → address+borough populates fields |
| 11 | Photo attach | `web/` + `/api/submit` `photo_b64` | Hermes/Claude | photo captured → base64 in submit payload |
| 12 | Tailscale exposure | run scripts | Claude | iPhone loads page, full flow works |

TDD discipline: backend = vertical slices, one test → one impl, tests hit public
interfaces only, LLM tests use FakeBackend (no network). Frontend = pragmatic + Playwright UAT.

## 8. Dependencies / env

- `requirements.txt` (Hermes owns): add `google-genai`, `copilotkit` (Python runtime SDK).
  Already has `pinecone`, `fastapi`, `uvicorn[standard]`, `langchain*`, `python-multipart`.
- Frontend (`web/`): React + Vite + `@copilotkit/react-core` + `@copilotkit/react-ui`
  (generative UI). Web Speech API + `navigator.geolocation` are browser built-ins (no dep).
  Reverse geocode: free Nominatim (`nominatim.openstreetmap.org/reverse`) — no key needed.
- `.env`: has `PINECONE_API_KEY`, `GOOGLE_API_KEY`. **Add `GEMINI_API_KEY`** (same value)
  OR rely on backend fallback. ⚠️ `GOOGLE_API_KEY` value format (`AQ.Ab8...`) is unusual —
  **verify it authenticates with a 5-sec test call before building the Gemini backend.**
- llama.cpp installed (`llama-server`); model in `models/` (gitignored).
- LangSmith CLI installed (`~/.local/bin/langsmith` v0.2.34). `.env` has `LANGSMITH_TRACING`,
  `LANGSMITH_ENDPOINT`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT="311-voice"`. SDK `langsmith`
  0.6.6 present. Backends should emit traces to project `311-voice`.

## 9. Timeline (~240 min, 2 agents parallel)

| Time | Claude (worktree `../311-voice-claude`, branch `claude/backend`) | Hermes (worktree `../311-voice-hermes`, branch `hermes/frontend`) |
|---|---|---|
| 0:00–0:15 | set up worktrees+branches; verify Gemini key; ingest 2,084 → Pinecone | finalize `311-mapping.json`; scaffold `web/` (Vite) |
| 0:15–1:15 | `/api/match` + LLM abstraction + Gemini backend (TDD) | frontend CORE: mic → results → **plain form** (vs stubbed API) |
| 1:15–2:00 | `/api/submit` (TDD); start `llama-server` + SLM backend | **merge `claude/backend`→ test against real API**; confirmation screen |
| 2:00–2:15 | **INTEGRATION CHECKPOINT: deterministic flow works end-to-end (safety net)** | same — verify plain flow on desktop |
| 2:15–2:50 | eval harness; SLM-vs-Gemini bake-off; pick winner; `/api/copilotkit` | CopilotKit generative UI + GPS auto-fill + photo |
| 2:50–3:20 | Tailscale exposure; iPhone end-to-end test | wire CopilotKit/GPS/photo ↔ backend; Playwright UAT |
| 3:20–3:50 | merge both branches → main; help fix integration | rehearse demo on iPhone |
| 3:50–4:00 | FREEZE on main + buffer | FREEZE + buffer |

## 10. Git workflow (separate branches per agent)

**Mechanism: git worktrees** (REQUIRED — two branches cannot be checked out in one working
tree at once; worktrees give each agent its own directory sharing the one `.git`).

```
311-voice/            main  (integration branch; canonical comms/, PLAN.md, progress)
311-voice-claude/     claude/backend   (Claude works here)
311-voice-hermes/     hermes/frontend  (Hermes works here)
```

Setup (step 0, on approval):
```
git branch claude/backend && git branch hermes/frontend
git worktree add ../311-voice-claude claude/backend
git worktree add ../311-voice-hermes hermes/frontend
```

Rules:
- Each agent commits only on their own branch, in their own worktree.
- **`.env` and `models/` are gitignored** → they do NOT appear in new worktrees. Copy `.env`
  into each worktree; symlink `models/` into `../311-voice-claude/` (Claude needs the SLM).
- **Coordination files stay canonical on `main`**: `comms/log.md`, `.claude-progress.md`,
  `PLAN.md`. Agents append to them via the main worktree (append-only → clean merges), not
  on feature branches, to avoid divergence.
- Integration: merge `claude/backend` → `main`, then Hermes merges `main` into
  `hermes/frontend` to pick up the real API. Final: both → `main` by 3:50.
- The frozen API contract (§6) is the merge seam — don't change it without a HANDOFF + ack.

## 11. Coordination

- Protocol: `comms/README.md`; log: `comms/log.md`; live state: `.claude-progress.md`.
- CLAIM before editing shared files. Demo backend chosen by bake-off (§5), set via `LLM_BACKEND`.

## 12. Definition of done (demo)

Speak → correct service identified → form filled → mock SR# shown, **on the iPhone over
Tailscale**, using whichever LLM backend won the bake-off. Pinecone visibly in the path
(sponsor). No real 311 submission.
