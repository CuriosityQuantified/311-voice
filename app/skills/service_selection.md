# Skill: service_selection

Choosing the single best NYC 311 service from the reranked candidates returned by
`search_services`.

## How the candidates arrive
- `search_services` returns the top ~5 candidates AFTER Pinecone reranking, already ordered
  best-first by relevance.
- Each candidate has `ka`, `title`, `description`, `score`, `classification`.

## Gotchas
- **Rerank `score` is for ordering only.** Absolute values are small and can look low or even
  negative — that is NORMAL. Never tell the user "low confidence" just because the score is a
  small number. Compare candidates to each other, not to an absolute threshold.
- **`picked_ka` MUST be one of the returned candidate KA ids.** Never invent or guess a KA.
- The top-ranked candidate is usually correct, but read the `title`/`description` — a lower
  candidate sometimes matches the resident's actual problem better (e.g. they said "no hot
  water" but mean the boiler, not the faucet).

## Examples
- Complaint "my apartment is freezing and there's no hot water" → candidates include
  `Heat or Hot Water` (HPD). Pick that; reasoning: "Reported lack of heat/hot water in a
  residential unit, which HPD handles."
- Complaint "huge pothole on my street" → pick the `Street Condition / Pothole` (DOT) item.

## When to ask vs. auto-pick
- If one candidate is a clear match, call `recommend_service` with it and ONE sentence of
  reasoning, then ask the user to confirm or choose another.
- If two candidates are genuinely plausible and materially different, recommend the best one
  but explicitly mention the alternative so the user can correct you.
