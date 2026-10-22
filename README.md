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

Odds are a snapshot, not a live feed. To pull the latest prices and rebuild the page:

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

## Ideas for next steps

- Live prices in the browser: Polymarket's Gamma API (`https://gamma-api.polymarket.com/events?slug=<market>`) is public; each race's `market` slug in `odds.json` is the event slug.
- Kalshi prices alongside Polymarket: the feed carries a `kalshi` block for most Senate and governor races.

Attribution: odds data from PolymarketTrader.com (CC BY 4.0), via Polymarket. Prices are market odds, not polls. State shapes from us-atlas; district shapes from the US Census Bureau's 2024 cartographic boundary files.
