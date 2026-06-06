# Skill: emergency

Handling life-safety / 911 situations. This overrides the normal filing flow.

## How to recognize one
- A candidate from `search_services` whose `classification` is `"emergency"`.
- OR the resident describes an immediate danger regardless of the candidate: active fire,
  gas smell/leak, building collapse, someone trapped or injured, a crime in progress,
  flooding that's an immediate hazard, downed live power line.

## What to do
1. Do **NOT** call `submit_service_request`. 311 is for non-emergencies; filing a request
   here would delay the right response.
2. Tell the user clearly: **"This sounds like an emergency — please hang up and call 911 now."**
3. If the picked candidate came back as emergency, the `recommend_service` tool already set
   `emergency=true` in state so the UI shows a "Call 911" banner; reinforce it in your reply.

## Gotchas
- Gas leaks: 911 (or Con Edison 1-800-75-CONED), never a routed 311 service request.
- "No heat" in winter is NOT a 911 emergency — it's a normal HPD Heat/Hot Water complaint.
  Don't over-trigger; only treat genuine immediate danger as an emergency.
- After advising 911, you may still offer to note the non-emergency parts (e.g. a follow-up
  repair) but make the 911 instruction the priority.
