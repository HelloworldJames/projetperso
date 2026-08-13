# PC Hunter AI — Codex Handoff

## What this project is

PC Hunter AI is a Python-based opportunity radar for the used-computer market. It is being built incrementally as both a practical resale tool and a learning project.

The intended pipeline is:

`source -> normalization -> deduplication -> geographic validation -> persistence -> classification -> component extraction -> consistency -> valuation -> repair/risk -> profitability -> opportunity score -> ranking -> Discord/Top`

## Current state

The project is already a working prototype, not a greenfield rewrite.

Working pieces include:

- multi-provider architecture
- ParuVendu real collection
- Vivastreet real collection
- strict geographic filtering around Tonnay-Charente
- SQLite listing memory and price history
- presence/disappearance tracking
- classification
- component extraction
- consistency checks
- desktop component valuation
- Apple complete-machine valuation
- initial Windows laptop complete-machine valuation
- profitability/opportunity/ranking
- Discord notifications
- Top snapshot
- 5-minute radar loop

## Recent bugs already fixed

### 1. Unknown locations passed the local filter

Old behavior kept unresolved locations.

Correct behavior is now fail-closed for the local radar.

Examples that were correctly rejected after the fix:

- Mortain / Mortain-Bocage ~294 km
- Paris 12e ~403 km
- Condé-sur-l'Escaut ~601 km

### 2. Vivastreet thousands separator

A Vivastreet price such as:

`1.250 €`

was once parsed as:

`1.25 €`

It must be:

`1250 €`

This has been fixed.

### 3. `geo.py` accidental truncation

An accidental file replacement removed the final return from `filtrer_par_distance`, which caused `NoneType` errors in `scraper.py`.

The current `geo.py` has been restored and validated.

## Vivastreet pagination discovery

A dedicated probe produced:

- HTTP 200 on national page
- total announced: 42
- main page: 25 listing IDs
- one pagination link: `/achat-vente-informatique/fr/t+2`
- page 2: 17 listings
- 17 new IDs
- 0 overlap with page 1
- total unique IDs seen: 42

The Charente-Maritime category page returned 0 at that moment.

Therefore, for the current prototype, the good approach is:

1. collect the national computer category pages,
2. normalize listing location,
3. apply PC Hunter's own strict 50 km geographic filter.

Do not assume a department page is sufficient.

## Important product direction

PC Hunter should eventually scan broad used-computer listings, not only the string “PC gamer”.

The classifier should decide whether an item is:

- desktop
- gaming PC
- laptop
- gaming laptop
- component
- accessory
- unknown

Longer term the project may evolve into a broader “Opportunity AI” for used-market deals.

## Data minimization

Do not collect seller identity or seller contact details.

Store only what is useful for analyzing the listing, such as:

- source/platform
- listing ID
- title
- price
- description/specs
- condition signals
- location
- publication/observation date
- URL
- derived hardware/valuation/risk information

## Financial logic

Do not present internal reference values as live guaranteed resale prices.

The system should progressively learn from real observations and comparable listings.

Conservative behavior is preferred over false-positive “amazing deal” alerts.

## First task for Codex

Before changing anything:

1. Read `AGENTS.md`.
2. Inspect the current versions of:
   - `collector/providers/vivastreet.py`
   - `collector/scraper.py`
   - `collector/geo.py`
   - `analyzer/components.py`
   - `analyzer/value.py`
3. Run syntax checks only.
4. Report whether Vivastreet pagination is already integrated in the current working tree.

If it is NOT integrated, implement only this change:

- page 1 = `/achat-vente-informatique/fr`
- discover the real pagination links from the HTML
- collect `t+2` when exposed
- deduplicate by Vivastreet listing ID across pages
- stop on 401/403/429
- do not bypass protections
- preserve the current price/location fixes
- preserve `rechercher(limite=None)`
- print per-page counts
- return a normal list in all expected paths

Validation target when source content has not changed materially:

- page 1 roughly 25 IDs
- page 2 roughly 17 new IDs
- roughly 42 total unique IDs before listing parser rejection

Then run:

```powershell
python -m py_compile .\collector\providers\vivastreet.py
python -m collector.providers.vivastreet
python .\main.py
```

Do not change unrelated modules during this task.

## Second task after pagination

Audit the real local laptop/Mac output from `main.py`.

Check especially that complete-machine valuation:

- does not sum soldered Apple components,
- refuses valuation when the model is too ambiguous,
- does not overvalue an old Intel Mac merely because it has a large HDD,
- requires sufficiently precise CPU/GPU information for Windows gaming laptops,
- produces conservative low/probable/high ranges.

Do not widen the reference tables aggressively without evidence.
