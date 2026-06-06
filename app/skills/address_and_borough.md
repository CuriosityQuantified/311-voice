# Skill: address_and_borough

Capturing the location of the problem correctly for the 311 form.

## Borough — canonical values (send EXACTLY these)
`MANHATTAN`, `BROOKLYN`, `QUEENS`, `BRONX`, `STATEN ISLAND`
- Uppercase, space-separated. Staten Island is two words: `STATEN ISLAND` (never
  `STATEN_ISLAND`). The backend normalizes `_`→space and uppercases as a safety net, but you
  should pass the canonical value via `update_form(borough=...)`.

## Fields and where each piece goes
- `address` — the street address of the PROBLEM (e.g. `1681 Madison Ave`). Not the resident's
  mailing address unless they're the same.
- `apartment` — unit/apt number only (e.g. `4B`). Leave empty for a street/outdoor problem
  (pothole, downed tree).
- `locationDetails` — free text that doesn't fit elsewhere: a cross-street, "in front of the
  deli", "rear courtyard", floor, landmark.
- `borough` — one of the five canonical values above.

## Gotchas
- A spoken intersection ("Madison and 110th") is NOT a street address. Put it in
  `locationDetails` and ask the user for the nearest building number if a street address is
  required.
- GPS may pre-fill `address`/`borough`. If the user spoke a DIFFERENT location than GPS, trust
  what they SAID about the problem location and call `update_form` to correct it.
- If the user gives an apartment but no building address, you still need `address` before
  submitting — ask for it.

## Example
"There are rats behind 240 East 5th Street in Manhattan, by the back alley" →
`update_form(address="240 East 5th Street", borough="MANHATTAN",
locationDetails="back alley behind the building")`.
