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

### Agent shared state (bind UI to these)
```
form:       { ka, description, address, borough, apartment, locationDetails }   // live draft
submission: { sr_number, payload, status }                                      // after submit
```

### Agent tools (backend-defined, in app/agent.py)
- `recommend_service(picked_ka, reasoning)` — surfaces the pick.
- `update_form(ka?, description?, address?, borough?, apartment?, locationDetails?)` —
  PARTIAL update to `form` (the draft the user sees). Call on every user revision.
- `submit_service_request()` — commits the current `form` draft (mock).

### Frontend CopilotKit actions (`web/src/copilotkit/schema.ts`)
> ⚠️ These are a DIFFERENT integration style than the backend agent tools above. If we
> use the CopilotKit-action path, names/args must be reconciled. Today App.tsx uses REST,
> so this is not on the critical path. Decide before wiring: action-driven vs shared-state.

---

## Known mismatches to fix (2026-06-06)

| # | Where | Issue | Resolution |
|---|---|---|---|
| 1 | `/api/match` | missing `extracted_fields` | ✅ FIXED (backend now returns it) |
| 2 | borough `STATEN_ISLAND` vs `STATEN ISLAND` | frontend code vs NYC value | ✅ backend normalizes; frontend should prefer canonical |
| 3 | `schema.ts` uses `location_details`; everywhere else `locationDetails` | naming drift | frontend to standardize on `locationDetails` |
| 4 | action-driven (schema.ts) vs shared-state agent tools | two CopilotKit patterns | pick one before wiring the agent UI (REST path works now) |
