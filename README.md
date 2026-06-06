# 311-voice

A voice-driven NYC 311 complaint-filing app. The user speaks a complaint ("there's a
pothole on Main St, three feet wide"), the system transcribes it on-device, classifies
it against the full NYC 311 service catalog using a RAG pipeline, has an LLM agent
reason about the best match, populates the corresponding service-request form, and
(for the hackathon) **mocks** the submission to the NYC 311 API.

Everything runs **locally on a Mac (mini/host)**. The iPhone is a thin client that
reaches the host over Tailscale for the demo. Target footprint is **< ~1.7 GB total**
so the whole thing could in principle run on a phone later.

---

## The Idea

| Aspect | Decision |
|---|---|
| What | Speak a 311 complaint → get it classified, formatted, and submitted |
| Who | NYC residents (jurisdiction locked to **NYC**) |
| Where it runs | All on the Mac host; iPhone accesses via browser over Tailscale |
| Submission | **Mocked** — validate + format the POST, do not actually file |
| Privacy goal | Local SLM + STT + orchestration; vector DB is Pinecone (cloud) |

## End-to-End Flow

```
User speaks complaint
  → whisper.cpp transcribes (on-device, base model)
  → Pinecone integrated search (server embeds w/ llama-text-embed-v2) → top-10 matches
  → Pinecone rerank (bge-reranker-v2-m3) → top-5 with scores
  → LangChain agent receives complaint + top-5 + scores, reasons, picks one
  → maps to NYC {agency, problem, problemDetails, locationType} triple/quad
  → extracts open-text fields (address, details, apartment) from transcript
  → streams a fixed-schema (A2UI) form to the frontend
  → mock POST to CreateServiceRequest (validated, not actually sent)
```

## Why the agent reasons over top-5 instead of picking top-1

Safety-critical. The agent sees the similarity/rerank scores and can reason:
- Top match 0.94, second 0.71 → large gap → confident, proceed.
- Top two 0.89 and 0.87 → tight → ask the user to clarify.

This prevents silent misclassification of a complaint into the wrong agency.

## Status / Key Facts

- **~2,084** NYC 311 content items pulled from the live API and upserted to Pinecone
  (source regenerable locally via `scripts/fetch_311_content.py` — no Mac mini dependency).
- Vector DB is **Pinecone** (hackathon sponsor) — managed cloud, so retrieval is the
  one part of the stack that is **not** local.
- **562** of those are "submittable" service requests (rest: informational/emergency/unclear).
- NYC does **not** support Open311 GeoReport v2 — it has a custom Azure-gateway API.
- API subscription is live (key in `API.md`); read endpoints confirmed working.
- The categorical submission values (`agency`/`problem`/`problemDetails`) are **not**
  discoverable via the API — they must be mapped/hardcoded.

## Files in this folder

| File | Purpose |
|---|---|
| `README.md` | This overview |
| `ARCHITECTURE.md` | System architecture, stack, host/client topology, RAG pipeline |
| `SPECIFICATIONS.md` | NYC 311 API endpoint map, data model, field catalog, mock plan |
| `API.md` | Subscription key, gateway, headers, working curl test |

> Source of record was the Obsidian vault on the Mac mini at
> `NAP1320/Projects/311-voice/`. This folder is the local working copy on the Air.
