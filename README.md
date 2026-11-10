# Political Odds Map (presidentl.app)

Live: https://presidentl.app

The daily record of what prediction markets think about American politics. The home page is the 2028 presidential race (winner, both nominees, both VP picks) with a Senate 2028 map; the 2026 midterms are frozen on `2026.html` as final odds against results. Everything rebuilds itself hourly from a GitHub Action.

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
data/baseline.json   current seat counts and who holds each seat up in 2026 (for the projection and flip list)
data/funstats.json   age of Congress per Congress, US life expectancy, median age (Fun stats tab)
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

## Projected seat counts

Under the control bar each chamber shows what the chamber would look like if every race went to its current favourite, next to the change from today's composition, and which seats would flip. The baseline lives in `data/baseline.json`: the current D/R counts, the majority threshold, and the party holding every seat that is up in 2026. Update it when a seat changes hands (a resignation, a special election). Senate D counts include the two independents who caucus with the Democrats. The House projection only covers districts with a market (CA-40 has none at the moment), so its two changes do not sum to zero.

## Election night

The "Election night" button (and automatically from 6 PM ET on Nov 3) switches the page into results mode: the ledger is ordered by poll-closing time, each row shows when its state's polls close, and any race whose Polymarket favourite is priced at 98.5% or higher is marked **Called** (solid navy / dark red on the map, a ✓ on the state label). The control bar becomes a called-seats tally with open races in grey. Poll-closing times live in `src/template.html` (`CLOSE`), using each state's last closing time in Eastern. Before Election Day the button is a preview: a 98.5% price then just means a safe seat.

## Site settings (`site.json`)

Everything that turns the site into a business lives in one file; `scripts/build.py` bakes it into the pages.

| Key | What it does |
|---|---|
| `referral.polymarket` | Your Polymarket referral code; appended as `?r=CODE` to every market link. Polymarket pays 10% of referred users' net fees for 30 days once your own account has $10K lifetime volume. |
| `referral.kalshi` | Your Kalshi referral code; appended as `?referral=CODE` to Kalshi links ($25 credit per referral, capped at 40). **Check the Kalshi market URL pattern** in `KL()` in `src/template.html` against a real market page before relying on it. |
| `sponsor` | `name`, `url`, `text`, `from`, `to` (ISO dates). A "presented by" band shows under the header only inside the window. Links carry `rel="sponsored"`. Leave `name` empty for no band. |
| `newsletter.action` | A form endpoint that accepts `POST email=…`, e.g. Buttondown's `https://buttondown.com/api/emails/embed-subscribe/<username>`. The signup box is hidden until this is set. |

## Pages

Clean URLs (`vercel.json` → `cleanUrls`); the `.html` paths redirect. One shared top bar on every page, from `src/partials/nav.html`, injected by `build.py` with the current page marked.

| URL | Source | What it is |
|---|---|---|
| `/` | `src/home.html` + `data/home.json` | Numbers-first front page: balance-of-power strip (White House 2028 party market, Senate 2028 control, 2026 result), 2028 front-runners with 7-day change and sparklines, biggest moves, one tile per section. Inlines only `home.json` (~14 KB). |
| `/2028` | `src/template.html` | The 2028 markets (winner, nominees, VPs), the Senate 2028 map, the archived 2026 views and Congress by age. |
| `/senate` | redirect → `/2028#senate2028` | Until the Senate map becomes its own page. |
| `/2026` | `src/2026.html` | Final odds vs results, calibration. |
| `/shift` | `src/shift.html` | County shift arrows 2000–2024. |
| `/data` | `src/data.html` | Downloads and schema. |
| `/about` | `src/about.html` | About; `/embed` redirects here. |

## Turnout tab (early vote)

`scripts/fetch_earlyvote.py` (run by the hourly workflow) saves one snapshot a day of the UF Election Lab's 2026 early-vote tracker to `data/earlyvote/YYYY-MM-DD.json`, refreshes the Texas day-by-day series in `data/earlyvote_ref.json` from the Texas SOS daily reports (via github.com/Seeker-Cliff/tx-early-vote-live), and, with `--backfill`, tries to fill earlier days from the Wayback Machine (it rate-limits and had no captures when tried on Oct 30, so this is off in the hourly run). `data/earlyvote_ref.json` also holds static reference data: 2018 and 2022 total ballots and eligible population per state (UF Election Lab turnout files) and the 2022 final early-vote totals per state (US Elections Project 2022 tracker).

The page shows early ballots so far as a share of 2022 and 2018 total turnout and of the 2022 final early vote, in-person vs mail, party registration where states report it, a national day-by-day line built from the snapshots, and a Texas chart that lines up the same day of early voting in 2018, 2022, 2024 and 2026. No national day-by-day series exists for 2018 or 2022, which is why those years appear as final totals.

The hourly workflow runs the script after the odds fetch and rebuilds; if the UF feed is down the last snapshot is kept.

## Fun stats tab

`scripts/fetch_funstats.py` computes the average age of the House and Senate at the start of every Congress from the unitedstates/congress-legislators dataset, pulls US life expectancy at birth from Our World in Data, and adds the Census median age of the population (hand-entered in the script). The tab charts the four lines from 1900, with tiles for today's averages, how many sitting members are older than the national life expectancy, and the oldest and youngest members. Rerun the script at the start of each Congress (or any time, for today's ages): `python3 scripts/fetch_funstats.py`.

## 2026 results page (`2026.html`)

`scripts/build_2026_archive.py` takes the last feed snapshot before polls closed (`data/odds_2026_final.json`, saved from git) and asks Polymarket's Gamma API how every market resolved, writing `data/results_2026.json`. The page grades every race (favourite won / upset / pending), scores Polymarket and Kalshi (Brier, who had the winner higher), and shows accuracy by rating band. Rerun the script as the last markets resolve; it is cheap after the first run because Gamma responses are cached in the temp dir.

## Senate 2028 (`data/senate_2028.json`)

`scripts/fetch_senate_2028.py` (hourly) lists the 34 Class 3 seats from legislators-current, the Florida and Ohio seats taking their 2026 special-election winners, searches Gamma for a per-state market, and reads the Senate-control 2028 market. States are shaded by incumbent party until a market exists.

## Price history backfill

`scripts/backfill_history.py` pulls daily prices from Polymarket's CLOB (`prices-history`) for every 2026 race and every 2028 candidate back to each market's launch and writes them as `data/history/YYYY-MM-DDT00-00.json` snapshots for days before the live snapshots began (Oct 22, 2026). Run once; it skips days that already exist.

## Ideas for next steps

- Live prices in the browser: Polymarket's Gamma API (`https://gamma-api.polymarket.com/events?slug=<market>`) is public; each race's `market` slug in `odds.json` is the event slug.
- Backfill `data/history/` from Polymarket's CLOB `prices-history` endpoint so the sparklines start with 30+ days instead of a few.
- An OG image (screenshot of the Senate map) so links unfurl on X and iMessage.

Attribution: odds data from PolymarketTrader.com (CC BY 4.0), via Polymarket. Prices are market odds, not polls. State shapes from us-atlas; district shapes from the US Census Bureau's 2024 cartographic boundary files.
