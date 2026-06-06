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
