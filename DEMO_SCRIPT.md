# 311 Voice — Live Demo Script

5 complaint scenarios designed for a smooth, impressive hackathon demo.

---

## 1. No Heat (The Classic)

**What to say:**
> "There's no heat in my apartment. It's been freezing for three days and my landlord won't do anything."

**Why it works:** Everyone in NYC understands this. The agent should match to **HPD Heat/Hot Water** (KA-01003).

**Demo flow:**
- Agent shows 5 candidates, picks the right one
- Form pre-fills: description = "no heat in my apartment for three days"
- Tap the address field mic: "123 Broadway, Manhattan"
- Agent auto-fills borough = MANHATTAN
- Tap the general mic at top: "Make it apartment 5C"
- Agent updates `apartment` field via `update_form`
- Submit

**Screen flow:** mic → results → form → confirm

---

## 2. Pothole (Infrastructure)

**What to say:**
> "There's a huge pothole on my street. It's going to damage cars."

**Why it works:** Clear DOT (Department of Transportation) issue. Shows the agent handles infrastructure complaints.

**Demo flow:**
- Matches to **Street Condition** (KA-01046)
- Form pre-fills with description
- Tap GPS button → auto-fills address + borough
- Tap general mic: "The pothole is right by the fire hydrant on the northeast corner"
- Agent updates `locationDetails` field
- Submit

**Bonus:** If GPS is slow, say: "I'm in Queens" → borough updates via agent

---

## 3. Noise Complaint (Quality of Life)

**What to say:**
> "My neighbor is playing loud music every night starting at 11 PM. I can't sleep."

**Why it works:** DEP (Environmental Protection) noise complaint. Shows quality-of-life issues that aren't emergencies.

**Demo flow:**
- Matches to **Noise** (KA-01038)
- Form pre-fills: "neighbor playing loud music at 11 PM"
- Tap general mic: "It's the apartment above me, 4B"
- Agent updates `apartment` and `locationDetails`
- Submit

**Edge case to try:** If the agent misclassifies as emergency, say: "No, this is not an emergency, just a noise complaint"
→ Agent should flip `emergency` flag and update screen

---

## 4. Street Light Out (Location-Heavy)

**What to say:**
> "The street light in front of my building has been out for a week. It's really dark at night."

**Why it works:** DOT / Con Ed infrastructure. The agent needs to capture precise location details.

**Demo flow:**
- Matches to **Street Light Out** (KA-01042)
- Form pre-fills description
- Tap general mic: "It's the light on the southeast corner of 5th Avenue and 42nd Street, right by the bank entrance"
- Agent updates `address` and `locationDetails` with rich detail
- Show the form after → both fields populated
- Submit

**This shows the agent's ability to extract multiple location fields from one utterance.**

---

## 5. Fallen Tree (Semi-Emergency)

**What to say:**
> "A tree fell down during the storm and is blocking the sidewalk. People have to walk in the street."

**Why it works:** Parks Department + potentially emergency. Shows the agent's judgment on severity.

**Demo flow:**
- Agent may classify as `emergency: true` initially
- Shows "Call 911" banner if emergency
- Tap general mic: "No, it's not dangerous, it's just blocking the path"
- Agent reclassifies: `emergency: false`, removes banner
- Matches to **Tree** (KA-01033)
- Form pre-fills, add location via GPS or mic
- Submit

**This shows the multi-turn conversation capability.**

---

## Quick Tips for the Demo

| Tip | Why |
|-----|-----|
| Speak clearly and not too fast | STT (Gemini) is accurate but rewards enunciation |
| Mention borough explicitly | Helps the agent even if GPS is slow |
| Use the field mic buttons | Shows the "tap to speak" per-field UX |
| Use the general mic at top | Shows natural language modification |
| Let the agent finish before editing | Shows the full screen flow |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Agent picks wrong service | Say "No, that's not right. I meant [issue]." → agent reruns search |
| Borough missing | Say "I'm in Brooklyn" → agent fills `borough` |
| Address wrong | Tap address field mic, say correct address |
| Form field wrong | Tap that field's mic, say the correction |

---

*Hackathon Demo · Mock Submission Only*
