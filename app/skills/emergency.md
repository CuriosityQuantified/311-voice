# Skill: emergency

Handling life-safety / 911 situations. This overrides the normal filing flow.

## How to recognize one
- A candidate from `search_services` whose `classification` is `"emergency"`.
- OR the resident describes an immediate danger regardless of the candidate: active fire,
  gas smell/leak, building collapse, someone trapped or injured, a crime in progress,
  flooding that's an immediate hazard, downed live power line.

## What to do
1. Tell the user clearly and FIRST: **"This sounds like an emergency — please call 911 now."**
   The 911 instruction is always the priority.
2. You may **still file the report** normally (every service is fileable). Filing the 311
   record does not replace 911 — advise 911 first, then proceed with the form if the user wants.
3. If the picked candidate came back as emergency, the `recommend_service` tool already set
   `emergency=true` in state so the UI shows a "Call 911" banner; reinforce it in your reply.

## Gotchas
- Gas leaks: advise 911 (or Con Edison 1-800-75-CONED) FIRST; you may still file the 311 record.
- "No heat" in winter is NOT a 911 emergency — it's a normal HPD Heat/Hot Water complaint.
  Don't over-trigger; only treat genuine immediate danger as an emergency.
- The 911 advisory and filing are independent: advise 911 for safety, file for the city record.
