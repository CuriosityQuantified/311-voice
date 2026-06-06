# 311-voice — Architecture

## Topology: Mac host + iPhone thin client

Everything runs on the Mac. The iPhone is just a browser client reaching the host
over Tailscale (stable HTTPS URL). Zero install, zero storage on the phone.

```
┌───────────────────────────────────────────────────────────────┐
│                     Mac (Server Host)                          │
│                                                                │
│  FastAPI Backend (Python)                                      │
│   ├── POST /api/voice   ← receives audio (WAV/MP3)             │
│   ├── POST /api/match   ← receives text query                 │
│   ├── POST /api/submit  ← MOCK SR submission (validate+format) │
│   └── GET  /api/chat    ← CopilotKit stream                    │
│                                                                │
│   LangChain orchestration                                      │
│     ┌────────────┐  ┌────────────┐  ┌───────────┐             │
│     │ whisper.cpp│  │  llama.cpp │  │ Pinecone  │──┐ (cloud)  │
│     │  (base)    │  │  (SLM)     │  │  client   │  │          │
│     └────────────┘  └────────────┘  └───────────┘  │          │
│                                                                │
│  React + Vite + Tailwind frontend (iOS-style UI)              │
│   └── CopilotKit components                                    │
│                                                                │
│  Tailscale → https://<host>.<tailnet>.ts.net                  │
└───────────────────────────────────────────────────────────────┘
                              │  HTTPS over Tailscale
┌───────────────────────────────────────────────────────────────┐
│                     iPhone (Remote Client)                     │
│  Safari/Chrome → React web app                                 │
│   ├── Voice recorder (Web Media API)                           │
│   ├── Complaint results list (top-5 + scores)                  │
│   ├── Mock submission form                                     │
│   └── CopilotKit chat UI                                       │
└───────────────────────────────────────────────────────────────┘
```

**Audio flow:** iPhone browser records audio → sends WAV/MP3 → Mac runs whisper.cpp →
transcript returned. STT happens on the Mac (`whisper.cpp`), **not** `whisper.rn`,
because the heavy lifting is centralized on the host. (`whisper.rn` would only be
relevant if the model ran on-device in a React Native app — not this topology.)

## Technology Stack

| Component | Technology | Approx size | Location |
|---|---|---|---|
| Frontend | React + Vite + Tailwind CSS | ~5 MB | Mac (served) |
| AI UI / middleware | CopilotKit (React) | ~1 MB | Mac (served) |
| Backend | FastAPI (Python) | ~50 MB | Mac |
| STT | whisper.cpp (base, quantized) | ~40–140 MB | Mac |
| SLM | llama.cpp + Qwen3.5-2B-MTP-GGUF (UD-IQ2_M) | **< 1 GB** | Mac |
| Vector DB | **Pinecone** (managed cloud; hackathon sponsor) | cloud | Pinecone cloud |
| Orchestration | LangChain (Python) | ~20 MB | Mac |
| Embeddings | **Pinecone integrated inference** (`llama-text-embed-v2`, 1024-dim) | cloud | Pinecone cloud |
| Reranker | **Pinecone rerank** (`bge-reranker-v2-m3`) | cloud | Pinecone cloud |
| Data | 2,084 complaint vectors | ~2 MB | Mac |
| **Total** | | **~1.5–1.7 GB** | Mac |

### Model choice

- **SLM:** `unsloth/Qwen3.5-2B-MTP-GGUF`, file `Qwen3.5-2B-UD-IQ2_M.gguf` (< 1 GB).
  Runs under llama.cpp on the Mac. MTP (multi-token prediction) variant for speed.
- **Whisper:** base model (chosen over tiny for accuracy, over small for speed).

### Vector DB note

**Pinecone is the primary store** — chosen because it's a hackathon sponsor (sponsor
track / prize eligibility). Tradeoff: Pinecone is a **managed cloud service**, so the
retrieval step is no longer local — complaint vectors and query embeddings leave the
Mac and hit Pinecone's API. The "fully local / fits on a phone" goal therefore holds
for STT + SLM + orchestration, but **not** for the vector DB. Do not market the demo
as fully offline. (pgvector/ChromaDB remain drop-in local fallbacks if the sponsor
angle is dropped.)

**Integration depth: INTEGRATED INFERENCE + RERANK (chosen).** Pinecone does the
embedding *and* the reranking server-side. We upsert raw **text records** (Pinecone
embeds them with `llama-text-embed-v2`); at query time we send text and Pinecone
embeds → retrieves → reranks with `bge-reranker-v2-m3`. No local embedding model, no
local cross-encoder — maximizes sponsor product coverage. STT (whisper) stays local.

**Index config:**

| Setting | Value |
|---|---|
| Index name | `311-voice` |
| Type | Serverless, created via `create_index_for_model` |
| Embedding model | `llama-text-embed-v2` (Pinecone-hosted, 1024-dim) |
| Rerank model | `bge-reranker-v2-m3` (Pinecone-hosted) |
| Namespace | `nyc-311` |
| Embedded field | `text` = `"{title}. {description}"` |
| Stored fields | `title`, `description`, `categories`, `classification` |

Records are upserted with `_id = KA number` and a `text` field Pinecone embeds; the
other fields are stored alongside so the query can filter
(`filter={"classification": "submittable"}`) and return metadata without a 2nd lookup.

Scripts: `scripts/ingest_pinecone.py` (upsert), `scripts/query_pinecone.py`
(search + rerank, the retrieval the agent consumes).

## RAG Pipeline (classification)

```
transcript
  → Pinecone integrated search (server embeds w/ llama-text-embed-v2) → top-10
  → Pinecone rerank (bge-reranker-v2-m3) → top-5 (with scores)
  → LangChain agent: reason over complaint + 5 candidates + scores
       • large score gap → pick confidently
       • tight scores    → ask user to clarify
  → chosen service → {agency, problem, problemDetails, locationType}
  → extract open-text fields from transcript
  → emit fixed-schema (A2UI) form
```

### Generative UI: Fixed Schema (A2UI)

The 311 form structure is well-known, so the component catalog is pre-defined once
(Card, InfoRow, CategoryBadge, StatusBadge, PrimaryButton). The agent only streams
extracted data into the fixed schema — deterministic, instant render, no runtime
schema generation.

## Offline / queue (post-MVP)

For a real (non-mock) build: persist the full request (incl. compressed photos) to
local SQLite when offline; retry on network restore; show pending count in UI. For
the hackathon this is out of scope because submission is mocked.

## Feasibility notes

- 16 GB RAM Mac comfortably runs SLM + whisper + backend concurrently.
- Web app (not React Native) is 3–5× faster to build for a 1-day hackathon.
- LangChain orchestration is feasible: it ties together STT call → embed/retrieve →
  rerank → agent reason → field extraction → mock submit as a single chain/graph.
