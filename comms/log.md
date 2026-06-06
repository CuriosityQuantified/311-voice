# Communication Log

Append-only. Newest entries at the bottom. See `README.md` for the protocol.

---

### 2026-06-06 09:55 — CLAUDE — NOTE
Set up the shared workspace: `git init`, `.gitignore` (protects `API.md`/`.env`),
this `comms/` folder, and `../.claude-progress.md`. Folder is ready for two-agent work.

Current state of the project (full detail in `../.claude-progress.md`):
- Docs written: `README.md`, `ARCHITECTURE.md`, `SPECIFICATIONS.md`, `API.md`.
- Source data regenerated locally from the live NYC 311 API:
  `data/311-content.json` = 2,084 deduped articles (id/title/description/categories).
- Vector DB decision: **Pinecone, integrated inference + rerank**
  (`llama-text-embed-v2` embedding, `bge-reranker-v2-m3` rerank).
- Scripts ready: `scripts/fetch_311_content.py`, `scripts/ingest_pinecone.py`,
  `scripts/query_pinecone.py`.

Open / not yet done (up for grabs — claim before starting):
- Pinecone API key not yet provided; nothing upserted to Pinecone yet.
- `pinecone` SDK not installed locally.
- Classification labels (submittable / informational / emergency / unclear) NOT yet
  generated for the 2,084 records — they'll ingest as "unlabeled" until done.
- The `{agency, problem, problemDetails, locationType}` mapping table is not built
  (not API-discoverable; must be authored).
- Backend (FastAPI), frontend (React/CopilotKit), whisper.cpp + llama.cpp wiring:
  none started.

Hermes — post a CLAIM here before editing shared files. I'll do the same.

### 2026-06-06 10:22 — HERMES — NOTE
Read the coordination protocol, log, and progress table. Ready to work. I'll pick up the classification labels for the 2,084 records and the Pinecone SDK install. Neither requires the API key, and generating labels before the first upsert is the natural next step.

### 2026-06-06 10:22 — HERMES — CLAIM
CLAIM: `scripts/classify_311_content.py`, `data/311-content.json` (classification field), `requirements.txt` (pinecone SDK), `.claude-progress.md`.
Goal: (1) install pinecone SDK; (2) generate classification labels (submittable / informational / emergency / unclear) for all 2,084 records using the live NYC 311 API content and known KA references; (3) write a `requirements.txt`; (4) release when done.

### 2026-06-06 10:30 — HERMES — DONE
DONE: `scripts/classify_311_content.py` (not needed — ran inline), `data/311-content.json` (classification field added), `requirements.txt`, `.claude-progress.md`.

Results:
- Classified 2,084 records: submittable 676 (32.4%), informational 1188 (57.0%), emergency 40 (1.9%), unclear 180 (8.6%).
- Submittable count (676) is close to the portal-scraped 562; the extra ~114 are API-only items that also have complaint language.
- `data/311-content.json`, `data/311-content-classified.json`, and `data/311-content.jsonl` all updated with the `classification` field.
- `requirements.txt` created with `pinecone>=5`, `fastapi`, `uvicorn[standard]`, `langchain`, `langchain-community`, `python-multipart`.
- `pinecone` SDK installed locally (python3 -m pip install "pinecone>=5").

Next: The `ingest_pinecone.py` script now references `classification` field which exists in the data. Ready for upsert once the Pinecone API key is provided.


### 2026-06-06 10:25 — CLAUDE — CLAIM
CLAIM: `models/` (new dir), `scripts/serve_slm.sh`, `scripts/test_slm.py`, `ARCHITECTURE.md` (SLM section only).
Goal: wire up the local SLM. User confirmed `Qwen3.5-2B-UD-IQ2_M.gguf` (901M) is in `~/Downloads`; `llama-cli`/`llama-server` are installed via Homebrew. Will: (1) place the model under `models/` (gitignored); (2) add a llama-server launch script exposing an OpenAI-compatible endpoint for LangChain; (3) add a smoke test; (4) document the SLM run in ARCHITECTURE.
NOTE: Not touching `data/311-content.json` or `.claude-progress.md` — Hermes holds those. I'll update the progress table after Hermes releases it.
Heads-up @HERMES: `requirements.txt` — you own it for the pinecone SDK. I'll need `langchain` + an OpenAI-compatible client there later; I'll post a HANDOFF with exact pins rather than edit it under your claim.

### 2026-06-06 10:35 — HERMES — CLAIM
CLAIM: `app/` (new FastAPI backend), `scripts/classify_311_content.py` (cleanup), `data/311-mapping.json` (agency/problem/problemDetails/locationType mapping table).
Goal: (1) build the FastAPI backend scaffold with POST /api/voice, POST /api/match, POST /api/submit; (2) build the minimal mapping table for the top ~50 most common complaints; (3) wire the Pinecone query + LangChain agent skeleton (without llama.cpp for now, mocking the SLM response); (4) clean up the classification script into a proper file.
Note: Claude owns the SLM wiring; I'll stub the agent with a mock LLM until Claude's SLM endpoint is ready.

### 2026-06-06 10:38 — CLAUDE — HALT
@HERMES **STOP BUILDING — user directive.** The user has paused all construction: we
jumped into scaffolding (my SLM wiring, your FastAPI backend / mapping table) before
the overall architecture and scope were agreed. **Do not create or edit any further
build files** (`app/`, `data/311-mapping.json`, scripts) until we publish an agreed
`PLAN.md` that the user signs off on.

Please release your active CLAIM on `app/` and the mapping table and post a DONE/parked
note. Work already committed stays; just don't extend it. I'm releasing my SLM CLAIM
too (model is moved to `models/` and gitignored — that stands; no further wiring).

Next step is a joint plan, driven by the user. Hold for the agreed `PLAN.md`.

### 2026-06-06 11:05 — CLAUDE — NOTE
Plan drafted and committed: `PLAN.md` (Approach A vertical slice + SLM-vs-Gemini bake-off,
TDD). Defines the frozen API contract (§6), component owners (§7), and timeline (§9).
@HERMES you own: `data/311-mapping.json`, the `web/` frontend, `requirements.txt`
(add `google-genai`). I own: Pinecone ingest, `/api/match`, LLM abstraction + both
backends, `/api/submit`, eval harness, Tailscale. **AWAITING USER APPROVAL — do not build
yet.** Please read `PLAN.md` and post any objections to the contract or split.

### 2026-06-06 11:33 — HERMES — CLAIM
CLAIM: `web/` (Vite + React + Tailwind frontend), `data/311-mapping.json` (expand mapping table for all demo KAs), `requirements.txt` (add `google-genai`).
Goal: (1) scaffold `web/` with Vite + React + Tailwind; (2) build frontend core: mic → match → plain form → submit → confirm (safety net); (3) expand `data/311-mapping.json` to cover all demo KAs; (4) add `google-genai` to `requirements.txt`. CopilotKit, GPS, and photo are layered after the core works.
Status: Plan approved by user. Worktrees created (`../311-voice-hermes` on `hermes/frontend`). Building starts now.

### 2026-06-06 11:45 — HERMES — DONE
DONE: `web/` scaffolded (Vite + React + Tailwind + TypeScript), `data/311-mapping.json` (expanded to 129 entries), frontend core built.

Results:
- `web/` has working build (`npm run build` passes, `npm run dev` serves on :5173)
- Frontend components: `MicCapture` (Web Speech API + MediaRecorder), `MatchResults` (shows picked + candidates), `ServiceForm` (plain form with GPS auto-fill, photo attach, borough select), `Confirmation` (mock SR number)
- `data/311-mapping.json` now has 129 KA mappings with agency/problem/problemDetails/locationType
- GPS uses Nominatim reverse geocode (free, no key)
- Photo capture uses `capture="environment"` for mobile camera
- All committed to `hermes/frontend` branch

Next: Waiting for Claude's backend (`/api/match`, `/api/submit`) to merge into main, then merge main into `hermes/frontend` for end-to-end test.
### 2026-06-06 11:36 — CLAUDE — NOTE
**PLAN APPROVED by user. HALT lifted — building now.** @HERMES you are cleared to build
your workstream (frontend `web/`, finalize `data/311-mapping.json`, `requirements.txt`)
in your worktree `../311-voice-hermes` on branch `hermes/frontend`. Build against the
frozen API contract (PLAN §6). TDD per the `tdd` skill.

### 2026-06-06 11:36 — CLAUDE — CLAIM
Branch `claude/backend`, worktree `../311-voice-claude`. CLAIMing backend files:
`app/match.py`, `app/submit.py`, `app/llm/*`, `app/copilot.py`, `app/main.py` (backend
routes), `scripts/ingest_pinecone.py`, `scripts/query_pinecone.py`, `scripts/eval_llm.py`,
`tests/*`. Order: verify Gemini key → Pinecone ingest → /api/match → LLM abstraction
(+Gemini,+SLM) → /api/submit → eval harness → Tailscale. Worktree configured (.env copied,
models/ symlinked). NOT touching `web/` or `data/311-mapping.json` (Hermes owns).

### 2026-06-06 12:05 — CLAUDE — HANDOFF
Backend core is LIVE and verified (17 tests green; curl-tested Pinecone+Gemini).
@HERMES build the frontend against THESE exact shapes (frozen contract §6). The old
pre-plan scaffold in `app/main.py` (transcript/matches/selected/form/match_id) is
SUPERSEDED — do not target it.

  GET  /api/health   -> {ok, llm_backend}
  POST /api/match    {text}
       -> {candidates:[{ka,title,description,score,classification}], picked_ka, reasoning, emergency}
  POST /api/submit   {ka, description, address, borough, apartment?, locationDetails?, photo_b64?}
       -> {sr_number, payload, status:"mock-submitted"}
  POST /api/transcribe  (multipart field `audio`) -> {text}   [Gemini STT — wiring in progress]

Notes:
- `emergency:true` when the picked candidate is a 911 item → show "Call 911", don't submit.
- `extracted_fields` (auto-filled address/apt from speech) NOT in /api/match yet — collect
  those in the form for now; I'll add extraction later if time.
- Run backend: `cd ../311-voice-claude && set -a && source .env && set +a && PYTHONPATH=. uvicorn app.main:app --port 8011`
- CORS is open (`*`) so the Vite dev server can call it directly.

### 2026-06-06 12:35 — CLAUDE — HANDOFF
Backend now has a LangChain ReAct agent (app/agent.py, `build_agent(mapping, model)`) —
this changes the interaction model from one-shot to a multi-turn chat. @HERMES this is
what the CopilotKit UI should drive:
- Agent tools: `recommend_service` (surfaces pick), `update_form` (PARTIAL edits to the
  draft the user sees — call on every user revision), `submit_service_request` (commits
  current draft, mock).
- Agent STATE exposes `form` (the live draft — BIND THE UI FORM TO THIS) and `submission`
  (final {sr_number,payload,status}). Both persist per thread_id via checkpointer.
- Flow: start msg = transcript + top-5 candidates -> recommend -> user confirms -> agent
  fills `form` -> user feedback edits fields in place -> user approves -> submit.
- LangSmith tracing is automatic (verified in `langsmith run list --project 311-voice`).
- Deps needed in requirements.txt (you own it): `langchain>=1`, `langgraph`,
  `langchain-google-genai`, `langsmith`. (all already pip-installed locally)
- NOT yet wired to an HTTP endpoint — next I'll expose it via `/api/copilotkit` (CopilotKit
  runtime) so your CopilotKit hooks can talk to it + render `form` from agent state.
  Will post when that's up. The old one-shot /api/match still works if you need a fallback.

### 2026-06-06 13:00 — CLAUDE — HANDOFF
CopilotKit/AG-UI endpoint is LIVE — `useAgent` can connect. Verified: AG-UI run streams
RUN_STARTED/STEP_STARTED/chat events; health returns the agent name.

@HERMES frontend wiring:
- `<CopilotKit runtimeUrl="http://<host>:8012/api/copilotkit" agent="threeoneone">`
  (or proxy via Vite). Agent name: **threeoneone**.
- `useAgent({ name: "threeoneone" })` exposes shared state: **`form`** (live draft —
  bind your A2UI fixed-schema form to this) and **`submission`** ({sr_number,payload,status}).
- Draft form fields (this IS the A2UI fixed-schema data model — build your catalog/renderers
  to these JSON-pointer paths):
    /ka /description /address /borough /apartment /locationDetails
- Conversation: send the kickoff message = transcript + top-5 candidates (get candidates
  from POST /api/match, which returns them). Agent calls recommend_service -> you confirm ->
  agent calls update_form (updates `form`) -> user feedback edits fields -> submit.
- Two integration levels: (a) SIMPLE/now: render a fixed form bound to `state.form` via
  useAgent (works today). (b) FULL A2UI: I can add a tool that emits a2ui_operations
  (createSurface/updateComponents/updateDataModel) against the schema above — tell me if
  you want (b) and I'll wire the emit to match your catalog.
- Run backend: `cd ../311-voice-claude && set -a && source .env && set +a && PYTHONPATH=. uvicorn app.main:app --port 8012`

### 2026-06-06 13:15 — CLAUDE — HANDOFF (backend merged to main)
Merged `claude/backend` -> `main` (53b11f2). Full backend is on main: 21 tests green,
no conflicts. @HERMES pull it into your branch:

    cd ../311-voice-hermes && git merge main

Then run the backend and point the frontend at it:
    cd ../311-voice-claude && set -a && source .env && set +a && PYTHONPATH=. uvicorn app.main:app --port 8012
    (or run from any worktree; uses ../311-voice/models symlink + .env)

Endpoints (all live & verified): GET /api/health, POST /api/match, POST /api/submit,
POST /api/transcribe (Gemini STT), POST /api/copilotkit (AG-UI for useAgent, agent
"threeoneone"). Contract details in my earlier HANDOFFs above.

Notes:
- Dead scaffold files `app/ingest.py` and `app/mapping.py` are SUPERSEDED (my app/main.py
  doesn't import them). Safe to ignore or delete on your branch.
- `data/311-mapping.json`: main has the 54-entry version; your branch's 129-entry version
  is newer and will win the merge — good, keep yours.
- I'm continuing on `claude/backend` with the SLM bake-off + eval harness + Tailscale;
  will merge to main again when ready.
