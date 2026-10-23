# Midterm Odds Map

Live: https://presidentl.app

A single-page US map of the 2026 midterms shaded by Polymarket odds. Senate, House and Governors tabs; every Senate and governor race links straight to its Polymarket market, and on the House tab you can zoom in to any state to see its congressional districts, each shaded by its own market.

## Run it

`index.html` is fully self-contained (geometry and odds are baked in), so any static server works:

```bash
python3 -m http.server 8000      # then open http://localhost:8000
```

Opening `index.html` directly from Finder also works.

## Refresh the odds

The page is a static snapshot, refreshed automatically: a GitHub Actions workflow (`.github/workflows/refresh-odds.yml`) runs every hour, and whenever the feed has new prices it commits the updated `data/odds.json` and `index.html`, which redeploys the site. The feed itself updates about twice a day, so most hourly runs change nothing. To refresh by hand:

```bash
python3 scripts/fetch_odds.py
```

That downloads PolymarketTrader.com's free JSON of Polymarket prices (CC BY 4.0, refreshed twice a day), rewrites `data/odds.json`, and regenerates `index.html`. No dependencies beyond Python 3. (If you already have a copy of the feed, pass its path: `python3 scripts/fetch_odds.py feed.json`.)

## Layout

```
index.html           built page (don't edit by hand; run scripts/build.py)
src/template.html    page source: markup, CSS, and the map/panel logic
data/states.js       projected SVG path data for the 50 states (us-atlas, Albers USA)
data/districts.js    projected SVG paths for the 429 multi-district House seats (Census, 119th Congress)
data/odds.json       Senate + House + Governor odds in the page's schema
data/history/        one compact snapshot per feed update (Democratic price per race); feeds the deltas and sparklines
scripts/build.py     template + data -> index.html
scripts/fetch_odds.py  refresh data/odds.json from the feed, then build
scripts/build_districts.js  regenerate data/districts.js from the Census shapefile (needs node)
```

### Regenerating the district shapes

You only need this if district lines change (next redistricting). It needs Node plus two packages:

```bash
npm i mapshaper d3-geo
curl -LO https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_cd119_500k.zip && unzip cb_2024_us_cd119_500k.zip
node scripts/build_districts.js cb_2024_us_cd119_500k.shp && python3 scripts/build.py
```

The script simplifies the boundaries (topology-preserving) and projects them with the same Albers USA settings us-atlas uses for the states, so districts sit exactly on top of their state. At-large states reuse the state outline.

## How the shading works

Color = the favourite's Polymarket price in that race. Safe ≥95%, Likely 80–95%, Lean 60–80%, Toss-up <60%; blue for the Democrat, red for the Republican. On the House tab a state's color reflects the share of its districts each party is favoured in; click a state to zoom in and see each district shaded by its own market (Esc or "All states" zooms back out). The Governors tab shades the 36 states with a 2026 governor race; there is no chamber-control market for governors, so the bar shows how many races each party is favoured in.

Deep links: `#senate`, `#house`, `#governor`, or `#house/TX` to open zoomed in to a state.

## Movement over time

Every time the workflow sees new prices it also drops a small snapshot in `data/history/` (about two a day). `build.py` folds those into the page, which then shows for every race the change in the favourite's price (▲/▼ points), a sparkline, and a "Biggest movers" strip with a toggle to sort the ledger by movement instead of closeness. The comparison window is 7 days once there is a week of history; until then it is "since <first snapshot>". The history started on Oct 22, 2026, so the first few days show small or no deltas.

## Election night

The "Election night" button (and automatically from 6 PM ET on Nov 3) switches the page into results mode: the ledger is ordered by poll-closing time, each row shows when its state's polls close, and any race whose Polymarket favourite is priced at 98.5% or higher is marked **Called** (solid navy / dark red on the map, a ✓ on the state label). The control bar becomes a called-seats tally with open races in grey. Poll-closing times live in `src/template.html` (`CLOSE`), using each state's last closing time in Eastern. Before Election Day the button is a preview: a 98.5% price then just means a safe seat.

## Site settings (`site.json`)

Everything that turns the site into a business lives in one file; `scripts/build.py` bakes it into the pages.

| Key | What it does |
|---|---|
| `referral.polymarket` | Your Polymarket referral code; appended as `?r=CODE` to every market link. Polymarket pays 10% of referred users' net fees for 30 days once your own account has $10K lifetime volume. |
| `referral.kalshi` | Your Kalshi referral code; appended as `?referral=CODE` to Kalshi links ($25 credit per referral, capped at 40). **Check the Kalshi market URL pattern** in `KL()` in `src/template.html` against a real market page before relying on it. |
| `sponsor` | `name`, `url`, `text`, `from`, `to` (ISO dates). A "presented by" band shows under the header only inside the window. Links carry `rel="sponsored"`. |
| `newsletter.action` | A form endpoint that accepts `POST email=…`, e.g. Buttondown's `https://buttondown.com/api/emails/embed-subscribe/<username>`. The signup box is hidden until this is set. |
| `embed.whitelabel_price` | Price shown on `embed.html`. |
| `contact.email` / `contact.url` | Where the embed and data pages send inquiries. |

## Pages

- `/` — the map. Tabs: Senate, House, Governors, 2028 (winner and both nominee markets, from `data/odds_2028.json`).
- `/?embed=1&chamber=senate|house|governor[&state=TX][&night=1]` — embed mode: map, legend and a badge, nothing else. Built from the same `index.html`.
- `/embed.html` — snippet generator, live preview, and the white-label offer.
- `/data.html` — the dataset page: `data/odds.json`, `data/odds_2028.json`, `data/history.csv` (long format, one row per race per snapshot) with the schema and CC BY terms.

Kalshi prices (`kalshi` on each Senate and governor race) show as a second line in the ledger with the Polymarket–Kalshi gap; gaps of 3+ points are highlighted.

## Ideas for next steps

- Live prices in the browser: Polymarket's Gamma API (`https://gamma-api.polymarket.com/events?slug=<market>`) is public; each race's `market` slug in `odds.json` is the event slug.
- Backfill `data/history/` from Polymarket's CLOB `prices-history` endpoint so the sparklines start with 30+ days instead of a few.
- An OG image (screenshot of the Senate map) so links unfurl on X and iMessage.

Attribution: odds data from PolymarketTrader.com (CC BY 4.0), via Polymarket. Prices are market odds, not polls. State shapes from us-atlas; district shapes from the US Census Bureau's 2024 cartographic boundary files.
