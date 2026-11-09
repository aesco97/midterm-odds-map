# presidentl.app — post-midterm roadmap

**What the site is:** the daily record of what prediction markets think about American politics. Not an election-night window (election.run owns that); a dataset with a good face on it.

**Self-sustaining means:** hosting + domain + email tool, roughly $0–300/year. Revenue has to be passive: things that pay a little, forever, with no weekly hand-work.

## Revenue, in priority order

1. **Referral links on the 2028 markets.** Already wired through `site.json` (`referral.polymarket`, `referral.kalshi`). Make 2028 the home page so the most-traded political markets of the next two years carry the links. Polymarket: 10% of referred users' fees for 30 days (needs $10K own volume first). Kalshi: $25 per referral.
2. **Sell the dataset.** Free: today's `odds.json` and `history.csv` (CC BY). Paid, one-time ($29–99, Gumroad or Lemon Squeezy): the full daily archive back to each market's launch, with candidate metadata and both exchanges. Needs the CLOB backfill below.
3. **Weekly "biggest movers" email, one sponsor slot.** Generated from `data/history/` by the Action; sent through Buttondown. Sponsor at $50–200/issue once the list clears ~1,000.
4. **Embed sponsorship.** Keep `/embed.html`; swap the white-label price for a "sponsored by" line. Bursty: 2027 VA/NJ governors, 2028 primaries.
5. **Tips / GitHub Sponsors.** A "keep this running" link in the footer.

Skip: display ads, a paid tier for the map, anything that needs hand-written content every week.

## Phase 1 — next two weeks

- [ ] **Midterm archive page** (`/2026.html`): final odds vs. results for every race. Where the markets were wrong, by how much, Polymarket vs Kalshi. Keep the election-night replay data.
- [ ] **2028 home page**: winner, Democratic and Republican nominee, VP markets; Senate 2028 map (33 seats; markets fill in over time); movers strip and sparklines up top.
- [ ] **CLOB backfill**: `scripts/backfill_history.py` pulls `prices-history` for every market token back to launch so sparklines open with months of data (runs once in the Action; the Action has network, local shells don't).
- [ ] Turn on the newsletter form (`site.json` → `newsletter.action`).
- [ ] Footer: tips link, "data" and "about" links.

## Phase 2 — by spring 2027

- [ ] Weekly email generator (`scripts/weekly_email.py` → Markdown draft in the Action's artifacts, or straight to the Buttondown API).
- [ ] Dataset archive as a product: zip + README + schema, listed on `/data.html`.
- [ ] Off-year pages: Virginia and New Jersey governor 2027, same template.
- [ ] **Calibration page**: Polymarket vs Kalshi vs result on every 2026 race (Brier score, by rating band), updated as 2027 races resolve.

## Phase 3 — 2028 primaries

- [ ] Primary calendar map with per-state nominee odds.
- [ ] Election-night mode for primary nights (already built for the general).
- [ ] Early-vote tab re-enabled for the general, with the 2026 snapshots as the comparison year.

## Principles (borrowed from election.run, applied to a data site)

Nonpartisan. No ads, no trackers beyond page counts. Say plainly what the numbers are (market prices, not polls or predictions) and where they come from. Do few things.

## Shift maps (added Nov 8)

County-level "shift from last time" arrow maps, 2000–2024, for President and House. Data is in place:

- `data/shift/results.json` — `{office: {year: {fips: [dem, rep, total, flag]}}}` for President 2000–2024 (7 elections) and House 2000–2024 (13), ~3,100 counties each. Built by `scripts/build_shift.py` from Heideman's county dataset (CC BY 4.0; 48 states) plus tonmcg's files for Hawaii and statewide Alaska (2008 on).
- `data/shift/counties.json` — county centroids in the site's map projection, from `scripts/build_county_centroids.mjs` (us-atlas, Albers USA, same scale/translate as `data/states.js`).
- `scripts/render_shift_svg.py` — reference renderer; its arrow rules (angle, scale, cap, width by turnout, skip flagged counties) are what `src/shift.html` should implement with a year slider and office toggle.

Known gaps: Hawaii and Alaska before 2008 (MEDSL's county file on Harvard Dataverse has them; add when a fetch path exists). Alaska is one statewide arrow. House arrows skip counties where a race was uncontested in either year, so House maps are sparser in the South. **2026 county results are not yet in any open dataset**; the archive page can show the 2026 shift once MEDSL or Heideman publish them (typically spring after the election), or earlier if we transcribe AP county tables.

Credit line for the page: "County results: Paul Heideman, *U.S. county-level election results 1990–2024* (CC BY 4.0); Hawaii and Alaska 2008–24 from tonmcg/US_County_Level_Election_Results_08-24."
