# Skill: submission_troubleshooting

Recovering when `submit_service_request` does not produce a confirmation.

## Submission is always MOCK
This demo NEVER contacts the real NYC 311 API. A successful submit returns a mock
`sr_number` like `311-MOCK-XXXXXXXX`. Tell the user it's a simulated filing if asked.

## Failure modes and fixes
- **"missing required fields [...]"** — `submit_service_request` was called before
  `ka`/`address`/`borough` were all set. Use `update_form` to fill the named fields, then
  submit again. Ask the user only for what's actually missing.
- **Unmapped service (HTTP 422 at the REST layer / mapping KeyError)** — the picked `ka` has
  no agency mapping. Re-run `recommend_service` and choose a DIFFERENT candidate from the
  search results that is mappable; explain to the user you're switching to a closely related
  service.
- **Tool error / transient failure** — the retry middleware will retry transient errors
  automatically. If it still fails, tell the user plainly and offer to try again; do not loop
  silently.

## Gotchas
- Never claim a request was filed unless `submit_service_request` returned a `submission` with
  an `sr_number`. Read it back to the user.
- Do not re-submit after a SUCCESS; one confirmation is final for the session.
