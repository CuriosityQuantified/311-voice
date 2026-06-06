# 311-voice — Specifications (NYC 311 API)

## Important: NYC is NOT Open311

NYC does **not** run an Open311 GeoReport v2 server. It exposes a **custom REST API**
behind an Azure API Management gateway. Field names, paths, and auth all differ from
the Open311 standard. Any Open311 assumptions in earlier planning are void.

| Open311 standard | NYC custom API |
|---|---|
| `/services.json`, `/requests.json` | `/create-sr/api/CreateServiceRequest`, `/public/api/GetServiceRequest` |
| Any jurisdiction URL | `api.nyc.gov` (Azure APIM gateway) |
| API key (various) | `Ocp-Apim-Subscription-Key` header (Azure-specific) |
| `service_code`, `service_request_id`, `lat`, `long` | `SRNumber`, `Agency`, `Problem`, `ProblemDetails`, `fullAddress` |
| `discovery.xml` service discovery | None (portal-based only) |

## Gateways

- **Read endpoints:** `https://api.nyc.gov/public/api/`
- **Create endpoint:** `https://api.nyc.gov/create-sr/api/CreateServiceRequest` (separate path)
- **Auth header:** `Ocp-Apim-Subscription-Key: <key>` (see `API.md`)
- **Rate limit:** ~30 requests/minute (429s observed during bulk fetch)

## Endpoint Map

### Active (✅)

| Endpoint | Method | What it does |
|---|---|---|
| `GetCategory` | GET | 115 service categories (98 leaf nodes) |
| `GetContentList` | GET | Content articles by category ID (1102+ items across 30 categories) |
| `GetServiceRequest` | GET | Status of a single SR by `SRNumber` |
| `GetServiceRequestList` | POST | Batch SR status lookup (requires body) |
| `Status/CodeBlue` | GET | `{"inEffect": false}` |
| `Status/SnowOnSidewalk` | GET | `{"inEffect": ...}` |
| `Status/SnowOnStreet` | GET | `{"inEffect": ...}` |
| `Status/FireHydrant` | GET | `{"inEffect": ...}` |
| `Status/OEM` | GET | `{"eventName": "", "inEffect": ...}` |

### Broken / undocumented (❌)

| Endpoint | Issue |
|---|---|
| `GetAssets` | NotFound for all tested asset numbers |
| `GetCalendar` | 404 even with valid date ranges |
| `GetContent` | 404 for all tested KANumbers |
| `GetSites` | 404 for all tested cities |
| `GetServiceRequestList` (no body) | BadRequest without a body |

## Service catalog reality

- "Service types" are **not numeric codes**. They are category names + KA article IDs.
  - Category IDs look like `311-64`, `311-62`, etc.
  - Article IDs look like `KA-01036`, `KA-02262`, etc.
- The portal "All A-Z" tab (`https://portal.311.nyc.gov/report-problems/` → "All A-Z")
  was scraped: **669 items (668 unique; 1 dup KA-03552)**.
- All 668 matched against the API content (2,084 items). The A-Z tab is a curated
  subset — only ~32% of API content items appear there; **1,416** API-only items exist.

### Classification of scraped portal items

| Classification | Count | Action |
|---|---|---|
| Submittable | 562 | Present as complaint options |
| Informational | 52 | "Learn more" (no SR) |
| Emergency (911) | 37 | Flag "Call 911" — exclude from MVP |
| Unclear | 17 | Present as complaint options |

> The MVP target pool is the **562 submittable** items. For the build the user wants
> **all ~2,084** API content items in the vector DB (**Pinecone**). Source regenerated
> locally from the live API via `scripts/fetch_311_content.py` → `data/311-content.json`,
> then upserted to Pinecone via `scripts/ingest_pinecone.py`.

## CreateServiceRequest — data model

The submission requires a `{agency, problem, problemDetails}` string triple (plus
`locationType`). These categorical values are **not discoverable via the API** — the
content endpoints return help articles (KA-xxxxx), not submission schemas. They must
be mapped/hardcoded.

### Categorical fields (must match known values)

| Field | Type | Example values |
|---|---|---|
| `agency` | String | `HPD`, `DSNY`, `DOT`, `DOHMH`, `DEP`, `NYPD` |
| `problem` | String | `Heat/Hot Water`, `Missed Collection`, `Street Light Condition` |
| `problemDetails` | String | `Apartment Only`, `Building-Wide`, `Street Light Out` |
| `locationType` | String | `Apartment`, `Building-Wide`, `Street`, `Sidewalk` |
| `srsource` | Integer | `614110000` Android, `614110008` iPhone, `614110005` Other, `614110004` Default |
| `anonymousRequired` | String | `Yes` / `No` |
| `whattimeofdaydoestheproblemoccur` | Integer | `614110000` 9a-12p, `…001` 12p-4p, `…002` 4p-9p, `…003` 9p-11p, `…004` 11p-9a, `…005` all the time |
| `siteBorough` | String | `MANHATTAN`, `BROOKLYN`, `QUEENS`, `BRONX`, `STATEN ISLAND` |
| `Status` (response) | Integer | `614110000` Cancelled, `…001` Open, `…002` In Progress, `…003` Closed |

### Open-text fields (free-form, from voice)

| Field | Example |
|---|---|
| `description` | `N/A` (general; often ignored by HPD) |
| `additionalDetails` | `No Heat` (the actual complaint text) |
| `fullAddress` | `1681 Madison Ave, Manhattan` |
| `locationDetails` | `Bedroom`, `Building lobby` |
| `dateTimeObserved` | `10/02/2018 15:31:33` |
| `apartmentNumber` | `1A` |
| `contact.firstName` / `.lastName` | `Alfred` / `Eng` |
| `contact.notificationEmail` | `aeng@example.com` |
| `contact.primaryPhone` | `1234567890` |
| `contact.street1` / `.street2` | `102` / `Broadway` |
| `contact.borough` / `.city` / `.state` / `.zipCode` | `Manhattan` / `New York` / `NY` / `10029` |

### Starter mapping table (demo subset)

| Voice input | agency | problem | problemDetails | locationType |
|---|---|---|---|---|
| "No heat" / "No hot water" | HPD | Heat/Hot Water | Apartment Only | Apartment |
| "Trash wasn't picked up" | DSNY | Missed Collection | All Materials | Street |
| "Street light is out" | DOT | Street Light Condition | Street Light Out | Street |
| "Pothole" | DOT | Street Condition | Pothole | Street |
| "Broken sidewalk" | DOT | Sidewalk Condition | Broken Sidewalk | Sidewalk |
| "Rats" | DOHMH | Rodent | Rat Sighting | Street |
| "Mold" | HPD | Mold | Apartment Only | Apartment |
| "Plumbing leak" | HPD | Plumbing | Apartment Only | Apartment |
| "Noise from neighbor" | NYPD | Noise | Residential | Apartment |

> Full build goal: map all 2,084 items. Vector DB does the initial lookup; the agent
> reasons over the reranked top-5; the chosen item resolves to its triple.

## Mock submission plan (hackathon)

- Do **not** actually POST to `CreateServiceRequest`.
- Build the exact JSON payload the real endpoint expects, validate it
  (required fields present, categorical values legal), and return a mocked success
  response with a fake `SRNumber` on both backend and frontend.
- Read endpoints (`GetServiceRequest`, `GetCategory`, etc.) may be hit live since the
  subscription key works and they're non-mutating.

## Useful KA references (overlap with MVP)

`Heat or Hot Water` KA-01036 · `Missed Trash` KA-01788 · `Noise from Neighbor` KA-01017 ·
`Illegal Parking` KA-01986 · `Mold Complaint` KA-02262 · `Rat or Mouse` KA-01107 ·
`Pothole` KA-01093 · `Street Light` KA-01089 · `Sidewalk Condition` KA-02235 ·
`Bed Bug` KA-01236

## Source data artifacts

### Local (regenerated from live API — primary)

In `data/` (produced by `scripts/fetch_311_content.py`):
- `311-categories.json` — raw category tree (115 categories)
- `311-content.json` — deduped content articles `[{id, title, description, categories}]`
- `311-content.jsonl` — one article per line (for embedding pipelines)

### On Mac mini vault (original; not required anymore)

In `NAP1320/Projects/311-voice/` — superseded by the local regeneration, kept only
for the classification labels and any hand edits:
- `311-complaint-types.json` / `.md` — 669 scraped portal types
- `311-complaint-types-classified.json` / `.md` — 668 with classification
- `311-vector-db-source.json` — original embedding source data
- `chroma_db/` — original ChromaDB store (regenerable, no need to retrieve)
- `query_vector_db.py`, `VECTOR-DB-README.md`, `STACK-RECOMMENDATION.md`,
  `ARCHITECTURE.md`, `NYC-311-API-ENDPOINT-MAP.md`
