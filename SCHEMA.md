# 311-voice — Shared Data Schema (single source of truth)

Both backend (`app/`, Claude) and frontend (`web/`, Hermes) MUST conform to this. If you
change a shape, change it here first, then update both sides. Mirrors: `web/src/types.ts`
(REST), `web/src/copilotkit/schema.ts` (CopilotKit actions).

## Conventions

- **JSON field names are camelCase**: `locationDetails` (NOT `location_details`).
- **Borough values are NYC-canonical, space-separated, UPPERCASE**:
  `MANHATTAN`, `BROOKLYN`, `QUEENS`, `BRONX`, `STATEN ISLAND`.
  Frontend may use a code (`STATEN_ISLAND`) for its dropdown, but must send the canonical
  value — OR rely on the backend, which normalizes `_`→` ` and uppercases in `build_payload`.

---

## REST contract (the primary demo path — App.tsx uses this)

### `GET /api/health`
```json
{ "ok": true, "llm_backend": "gemini" }
```

### `POST /api/match`
Request:
```json
{ "text": "no heat in my apartment" }
```
Response (`MatchResponse`):
```json
{
  "candidates": [
    { "ka": "KA-01036", "title": "...", "description": "...", "score": 0.0176, "classification": "submittable" }
  ],
  "picked_ka": "KA-01036",
  "reasoning": "one sentence",
  "emergency": false,
  "extracted_fields": { "description": "no heat in my apartment", "address": "", "apartment": "", "locationDetails": "" }
}
```
- `candidates`: top-5 after Pinecone rerank (highest first by relevance; `score` is the
  reranker score — small absolute values are normal, use for ordering only).
- `picked_ka`: the LLM's choice (always one of `candidates[].ka`).
- `emergency`: `true` if the picked service is a 911 item → show "Call 911", do NOT submit.
- `extracted_fields`: pre-fill for the form. `description` = the transcript. address/
  apartment/locationDetails currently empty (filled via GPS + the form).

### `POST /api/submit`
Request (`SubmitPayload`):
```json
{ "ka": "KA-01036", "description": "no heat", "address": "1681 Madison Ave",
  "borough": "MANHATTAN", "apartment": "4B", "locationDetails": "" , "photo_b64": null }
```
- Required: `ka`, `description`, `address`, `borough`. Optional: `apartment`,
  `locationDetails`, `photo_b64` (base64 image string, just echoed into the mock payload).
Response (`SubmitResponse`):
```json
{ "sr_number": "311-MOCK-XXXXXXXX",
  "payload": { "agency": "HPD", "problem": "Heat/Hot Water", "problemDetails": "Apartment Only",
               "locationType": "Apartment", "description": "N/A", "additionalDetails": "no heat",
               "fullAddress": "1681 Madison Ave", "siteBorough": "MANHATTAN",
               "apartmentNumber": "4B", "locationDetails": "", "srsource": 614110008 },
  "status": "mock-submitted" }
```
- Unmapped `ka` → HTTP 422. Submission is ALWAYS mocked (never hits NYC).

### `POST /api/transcribe`  (Gemini STT)
- multipart form field **`audio`** (mp3/webm/wav). Response: `{ "text": "..." }`.

---

## Agent path (CopilotKit `useAgent` over AG-UI) — layered/optional

### Endpoint
`POST /api/copilotkit` — AG-UI. Frontend: `<CopilotKit runtimeUrl=".../api/copilotkit"
agent="threeoneone">`, `useAgent({ name: "threeoneone" })`.

### Agent shared state (bind the UI to these — THIS is the chosen pattern)
```
transcript: str                                  // the STT complaint text
candidates: [ {ka,title,description,score,classification}, ... ]   // top-5 from search
picked_ka:  str                                  // recommended service
reasoning:  str                                  // one-sentence why
emergency:  bool                                 // picked is a 911 item -> show "Call 911", block submit
form:       { ka, description, address, borough, apartment, locationDetails }   // LIVE DRAFT
submission: { sr_number, payload, status }       // after submit
screen:     "mic" | "results" | "form" | "confirm"   // <- render this screen (Option A)
todos:      [ {content, status}, ... ]           // ADDITIVE (TodoListMiddleware) — frontend may ignore
```
The frontend renders the screen named by `screen`. **`todos` is new and additive** — added by
the agent's TodoListMiddleware harness; the `useAgent` binder can safely ignore it (no UI
change required). Nothing else in the state shape changed. Initialize a run with
`{ messages:[{role:"user", content: makeStartMessage(transcript)}], screen:"mic", form:{} }`.

### Agent tools (backend-defined, in app/agent.py) — each updates state
- `search_services(complaint)` — Pinecone retrieve; sets `candidates`, `transcript`, `screen="results"`. Agent calls this FIRST.
- `recommend_service(picked_ka, reasoning)` — sets `picked_ka`, `reasoning`, `emergency`, `form.ka`.
- `update_form(ka?, description?, address?, borough?, apartment?, locationDetails?)` — PARTIAL update to `form`; sets `screen="form"`. Call on every user revision.
- `submit_service_request()` — commits current `form` (mock); sets `submission`, `screen="confirm"`.
- `load_skill(skill_name)` — internal: loads on-demand domain notes (no state change, no UI impact).
- `write_todos(...)` — internal (TodoListMiddleware); writes `todos` state. UI may ignore.

> HARNESS (2026-06-06): the agent now runs LangChain built-in middleware — PII redaction
> (input), summarization, context-editing, model/tool call limits, and model/tool retries —
> plus a `load_skill` progressive-disclosure tool. All additive: the only new state field is
> `todos`; the 4 UI-facing tools and the `form`/`submission`/`screen` shapes are unchanged.

> DECISION (2026-06-06): we use the **shared-state pattern** (useAgent), NOT the
> action-driven (`show_match_results`/`show_service_form`) pattern. Frontend replaces the
> useCopilotAction components with a useAgent state-binder that routes on `screen`.
> `STT` is a separate REST call: `POST /api/transcribe` (audio) -> {text}, then feed `text`
> into the agent start message.

---

## Known mismatches to fix (2026-06-06)

| # | Where | Issue | Resolution |
|---|---|---|---|
| 1 | `/api/match` | missing `extracted_fields` | ✅ FIXED (backend now returns it) |
| 2 | borough `STATEN_ISLAND` vs `STATEN ISLAND` | frontend code vs NYC value | ✅ backend normalizes; frontend should prefer canonical |
| 3 | `schema.ts` uses `location_details`; everywhere else `locationDetails` | naming drift | frontend to standardize on `locationDetails` |
| 4 | action-driven (schema.ts) vs shared-state agent tools | two CopilotKit patterns | pick one before wiring the agent UI (REST path works now) |
