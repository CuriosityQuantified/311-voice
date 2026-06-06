# Hackathon Submission Form — 311 Voice

**Submission link:** https://docs.google.com/forms/d/e/1FAIpQLScEfqQlAR0lse4IoyEYIUIDYCkJFbgg5e3Cl8qUlXFKs2usRA/viewform?usp=dialog

---

## Suggested Responses

### 1. Project Name
**311 Voice** — Voice-Driven NYC 311 Complaint Filing

### 2. Tagline (1 sentence)
> Speak your NYC complaint and let AI file it for you. No app downloads, no forms, no friction — just talk.

### 3. What problem does it solve?
Filing a 311 complaint in NYC is a bureaucratic maze. Residents must:
- Navigate 2,000+ service categories to find the right one
- Fill out lengthy forms with precise location codes
- Know categorical values (agency, problem, problemDetails) that are **not publicly documented**
- Repeat this for every new complaint

**311 Voice** eliminates this friction entirely. The user simply *speaks* their complaint ("there's no heat in my apartment"), and the system handles classification, form population, and submission — all through a voice-first interface.

### 4. How does it work? (Technical overview)
```
User speaks complaint
  → Gemini 3.1 Flash transcribes audio (multimodal STT)
  → Pinecone vector search (top-10 matches from 2,084 311 articles)
  → LangChain agent reasons over top-5, picks best match
  → Agent extracts address/details from transcript
  → Auto-populates service request form
  → Gemini 3.1 Flash TTS reads agent reply aloud
  → User reviews / edits via voice or keyboard
  → Mock submission to NYC 311 API (validated, not sent)
```

**Stack:**
- Frontend: React + Vite + Tailwind (iPhone frame mockup)
- Backend: FastAPI + LangChain + Gemini 3.1 Flash
- Vector DB: Pinecone (2,084 NYC 311 articles, 1024-dim embeddings)
- RAG: llama-text-embed-v2 + bge-reranker-v2-m3
- TTS: Gemini 3.1 Flash TTS Preview (Aoede voice)
- A/B LLM: Gemini vs local SLM (llama.cpp + Qwen3.5-2B)

### 5. Key Features
- **Voice-first** — Every interaction starts with speech
- **Per-field STT** — Tap a mic button next to any form field to edit it by voice
- **Agent TTS replies** — The AI speaks back, not just text
- **Auto borough detection** — GPS fills address + borough automatically
- **RAG classification** — 2,084 article vector search, not keyword matching
- **Multi-turn agent** — Can correct misclassifications, update fields, handle emergencies
- **A/B LLM evaluation** — 200-sample bake-off comparing Gemini vs local SLM

### 6. Demo Script (2-3 minutes)

**Scenario 1: No Heat (The Classic)**
1. "There's no heat in my apartment. It's been freezing for three days."
2. Agent shows 5 matches, picks "HPD Heat/Hot Water Complaint"
3. TTS: "I found the right service. Let me fill out the form for you."
4. Form auto-populates with description
5. Tap GPS → auto-fills address + borough
6. Tap general mic: "Make it apartment 5C"
7. Agent updates form, TTS confirms
8. Submit → mock confirmation with SR number

**Scenario 2: Pothole (Infrastructure)**
1. "There's a huge pothole on my street."
2. Matches to "Street Condition"
3. GPS auto-fills location
4. Tap location details mic: "It's right by the fire hydrant"
5. Submit

**Scenario 3: Reclassification (Emergency)**
1. "A tree fell and is blocking the sidewalk"
2. Agent initially flags as emergency
3. User: "No, it's not dangerous"
4. Agent reclassifies, removes emergency banner, proceeds to form

### 7. What was built during the hackathon?
- Full FastAPI backend with agent tool-calling (search/recommend/update_form/submit)
- Pinecone vector DB with 2,084 NYC 311 articles + reranker
- 200 synthetic voice test corpus for STT accuracy evaluation
- React frontend with iPhone frame mockup, per-field STT, TTS playback
- End-to-end voice flow: speech → classification → form → submission
- Mock NYC 311 API submission (validated but not sent)

### 8. What was pre-existing?
- NYC 311 API documentation and test scripts (from prior research)
- Pinecone account setup
- General knowledge of LangChain / FastAPI (no pre-built code)

### 9. Team Members
- **Nicholas Pate** — Full stack (frontend + backend + agent + RAG pipeline)
- **Claude** — Backend agent architecture, TTS integration, STT pipeline
- **Hermes** — Frontend UI, voice interactions, per-field STT, TTS playback

### 10. Prizes / Categories
**Best use of AI for civic engagement** — 311 is the primary interface between NYC residents and city services. Making it voice-accessible democratizes civic participation for:
- Elderly residents who struggle with forms
- Non-native English speakers (Gemini STT supports multilingual)
- People with disabilities (motor impairments, vision impairments)
- Anyone who wants to report an issue while walking/driving

### 11. Future Work
- Connect to real 311 API submission (live mode)
- Add multilingual support (Spanish, Chinese, etc.)
- Photo upload + vision analysis ("this is the pothole")
- Offline mode with local SLM (Qwen3.5-2B already tested)
- iOS app wrapper with native voice recording
- SMS fallback for non-smartphone users

### 12. Repository
https://github.com/CuriosityQuantified/311-voice

---

## Quick Submission Checklist

- [ ] Fill out the Google Form (link above)
- [ ] Submit **today** for prize eligibility + demo slot
- [ ] If not ready to demo: still submit for event recap promotion
- [ ] Include the GitHub repo link
- [ ] Mention Pinecone (sponsor) and Gemini (sponsor) usage

## Notes

- **Mock submission only** — we don't actually file 311 complaints
- **Demo via iPhone** — Tailscale to Mac host, browser-based
- **Voice-first** — The entire UX is designed around speech, not typing
- **Emergency detection** — Agent flags true emergencies and redirects to 911
