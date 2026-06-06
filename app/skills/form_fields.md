# Skill: form_fields

The draft form the resident sees before submission, and how `update_form` behaves.

## Fields
- `ka` — the chosen service's KA id (set for you by `recommend_service`; don't normally touch).
- `description` — what's wrong, in the resident's words (defaults to the transcript).
- `address` — street address of the problem. **Required to submit.**
- `borough` — canonical borough. **Required to submit.** (see the address_and_borough skill)
- `apartment` — unit number, optional.
- `locationDetails` — extra location free-text, optional.

## Required to submit
`ka`, `address`, `borough`. `submit_service_request` will refuse and tell you what's missing
if any are blank — gather them with `update_form` first.

## update_form is a PARTIAL merge
- Pass ONLY the fields that changed. Omitted fields keep their current value.
- On user feedback like "actually it's apartment 5C, not 4B" call
  `update_form(apartment="5C")` — do NOT resend the whole form, and do NOT resubmit.
- Calling `update_form` moves the UI to the `form` screen so the user can review.

## Gotchas
- Don't pre-fill `apartment`/`locationDetails` with guesses; leave them empty if unknown.
- Changing the service after the user reconsiders: call `recommend_service` again (it resets
  `ka` and the emergency flag), not `update_form(ka=...)`, so the recommendation stays in sync.
