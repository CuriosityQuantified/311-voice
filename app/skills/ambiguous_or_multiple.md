# Skill: ambiguous_or_multiple

Handling complaints that are vague, or that bundle several distinct issues.

## Vague / underspecified complaint
- If `search_services` returns candidates that span unrelated services (no clear winner), the
  complaint is probably too vague.
- Ask exactly ONE focused clarifying question, then re-run `search_services` with the
  enriched description. Don't interrogate the user with a list.
- Example: "It's broken" → ask "What's broken — something in your apartment, or out on the
  street?" then search again.

## Multiple issues in one utterance
- Residents often report several things at once ("there's no heat AND the trash hasn't been
  picked up AND there's a pothole").
- Pick the PRIMARY / most urgent issue, file that one request end-to-end, and tell the user
  you'll handle the others next. Do not try to file several services in a single submission —
  each 311 request is for one service.
- If one of the issues is an emergency (see the emergency skill), handle the 911 guidance
  first regardless of order.

## Gotchas
- Don't merge two unrelated problems into one `description`; it produces a bad service match.
- Keep the resident's wording in `description` for the issue you're actually filing.
