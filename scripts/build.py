"""Assemble the site from src/ + data/.

  index.html        <- src/home.html (numbers-first front page; data/home.json)
  2028.html         <- src/template.html + data/states.js + data/districts.js + data/odds.json + data/odds_2028.json + data/history/
  embed.html        <- src/embed.html   (embed snippet generator, white-label pitch)
  data.html         <- src/data.html    (dataset page)
  data/history.csv  <- data/history/*.json flattened to long format

Site settings (referral codes, sponsor slot, newsletter form) live in site.json at the repo root.
"""
import json, pathlib, csv
from datetime import datetime, timezone
root = pathlib.Path(__file__).resolve().parent.parent

def read(p): return (root/p).read_text(encoding='utf-8')
def write(p, s): (root/p).write_text(s, encoding='utf-8')

data = json.loads(read('data/odds.json'))
data2028 = json.loads(read('data/odds_2028.json')) if (root/'data/odds_2028.json').exists() else {"updated": None, "markets": []}
site = json.loads(read('site.json')) if (root/'site.json').exists() else {}
base = json.loads(read('data/baseline.json')) if (root/'data/baseline.json').exists() else {}
fun = json.loads(read('data/funstats.json')) if (root/'data/funstats.json').exists() else {}
s28 = json.loads(read('data/senate_2028.json')) if (root/'data/senate_2028.json').exists() else {}
r26 = json.loads(read('data/results_2026.json')) if (root/'data/results_2026.json').exists() else {}

def history():
    """Fold data/history/*.json into series of [unix_seconds, democratic_price] per race, oldest first."""
    series = {'senate': {}, 'house': {}, 'governor': {}, 'control': {'senate': [], 'house': []}, 'p2028': {}}
    files = sorted((root/'data/history').glob('*.json')) if (root/'data/history').exists() else []
    rows = []
    for f in files:
        snap = json.loads(f.read_text(encoding='utf-8'))
        dt = datetime.fromisoformat(snap['updated'].replace('Z', '+00:00')).astimezone(timezone.utc)
        t = int(dt.timestamp()); stamp = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        for ch in ('senate', 'house', 'governor'):
            for k, v in snap.get(ch, {}).items():
                if v is None: continue
                series[ch].setdefault(k, []).append([t, v]); rows.append((stamp, ch, k, v))
        for ch in ('senate', 'house'):
            v = snap.get('control', {}).get(ch)
            if v is not None: series['control'][ch].append([t, v]); rows.append((stamp, 'control', ch, v))
        for slug, prices in snap.get('p2028', {}).items():  # 2028 markets: price per candidate, keyed by market slug
            for name, v in prices.items():
                series['p2028'].setdefault(slug, {}).setdefault(name, []).append([t, v]); rows.append((stamp, slug, name, v))
    return series, rows, len(files)

hist, rows, nsnap = history()

# What the page embeds is a thinned copy: history.csv keeps every point, but the home page only needs
# daily detail for the last 90 days and a weekly point before that, and the retired 2026 chambers only a tail.
def thin(series, keep_days=90, step=7):
    if not series: return series
    cut = series[-1][0] - keep_days * 86400
    old = [p for p in series if p[0] < cut]; recent = [p for p in series if p[0] >= cut]
    return old[::-1][::step][::-1] + recent  # every `step`th old point, anchored on the most recent old point
def tail(series, n=30): return series[-n:]
hist_page = {'control': {k: thin(v) for k, v in hist['control'].items()},
             'p2028': {slug: {name: thin(v) for name, v in d.items()} for slug, d in hist['p2028'].items()}}
for ch in ('senate', 'house', 'governor'): hist_page[ch] = {k: tail(v) for k, v in hist[ch].items()}

def earlyvote():
    """data/earlyvote/*.json (one per day) + data/earlyvote_ref.json -> {ref, days:[...], latest:{st:{...}}, series:{st:[[day, voted, inperson, mail]]}}."""
    ref = json.loads(read('data/earlyvote_ref.json')) if (root/'data/earlyvote_ref.json').exists() else {}
    files = sorted((root/'data/earlyvote').glob('????-??-??.json')) if (root/'data/earlyvote').exists() else []
    days, series, latest, fetched = [], {}, {}, None
    for f in files:
        snap = json.loads(f.read_text(encoding='utf-8')); day = f.stem; days.append(day); fetched = snap.get('fetched')
        for st, r in snap['states'].items():
            voted = max(r.get('voted_all', 0), r.get('inperson_all', 0) + r.get('accept_all', 0))  # a few states under-report voted_all
            series.setdefault(st, []).append([day, voted, r.get('inperson_all', 0), r.get('accept_all', 0)])
            latest[st] = dict(r, voted=voted, day=day)
    # Texas: extend the day-by-day 2026 series with the UF statewide in-person figure for days the county file hasn't covered yet
    tx = ref.get('tx'); start = (ref.get('tx_ev_start') or {}).get('2026')
    if tx is not None and start and 'TX' in latest:
        from datetime import date as _d
        lu = latest['TX'].get('last_update', '')
        try:
            n = (_d.fromisoformat(lu) - _d.fromisoformat(start)).days + 1
            cur = tx.get('2026') or []
            if 1 <= n <= 12 and (not cur or cur[-1][0] < n):
                cur.append([n, lu, latest['TX'].get('inperson_all', 0), latest['TX'].get('accept_all', 0)]); tx['2026'] = cur
        except ValueError:
            pass
    return {'ref': ref, 'days': days, 'latest': latest, 'series': series, 'fetched': fetched}
ev = earlyvote()

# history.csv: one row per (snapshot, chamber, race); the price is the Democrat's (or the non-Republican share where no Democrat is priced)
with (root/'data/history.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['updated_utc', 'chamber', 'race', 'democratic_price']); w.writerows(rows)

def page(body):
    head = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    return head + body.replace('</style>', '</style>\n</head>\n<body>', 1) + '\n</body>\n</html>\n'

J = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
site_js = 'const SITE=' + J(site) + ';'
inject = f"const DATA={J(data)};\nconst HIST={J(hist_page)};\nconst DATA2028={J(data2028)};\nconst BASE={J(base)};\nconst EV={J(ev)};\nconst FUN={J(fun)};\nconst S28={J(s28)};\n{site_js}"
body = read('src/template.html').replace('/*STATES*/', read('data/states.js')).replace('/*DISTRICTS*/', read('data/districts.js')).replace('/*DATA*/', inject)
write('index.html', page(body))

if (root/'src/2026.html').exists():
    write('2026.html', page(read('src/2026.html').replace('/*DATA2026*/', 'const R26=' + J(r26) + ';\n' + site_js)))
if (root/'src/shift.html').exists():
    write('shift.html', page(read('src/shift.html').replace('/*STATES*/', read('data/states.js')).replace('/*SITE*/', site_js)))
if (root/'src/about.html').exists():
    write('about.html', page(read('src/about.html').replace('/*SITE*/', site_js)))
if (root/'src/embed.html').exists():
    write('embed.html', page(read('src/embed.html').replace('/*SITE*/', site_js)))
stats = {'snapshots': nsnap, 'rows': len(rows), 'first': rows[0][0] if rows else None, 'last': rows[-1][0] if rows else None,
         'races': len(data['senate']['races']) + len(data['house']['races']) + len(data['governor']['races']), 'updated': data['updated']}
if (root/'src/data.html').exists():
    write('data.html', page(read('src/data.html').replace('/*SITE*/', site_js + '\nconst STATS=' + J(stats) + ';')))

# ---- Redesign: site-wide nav, home.json and the home page -------------------------------------------------
NAV = read('src/partials/nav.html') if (root/'src/partials/nav.html').exists() else ''
asof_txt = datetime.fromisoformat(data['updated'].replace('Z', '+00:00')).astimezone(timezone.utc).strftime('%b %-d, %H:%M UTC') if data.get('updated') else ''
def with_nav(html, page_key):
    """Insert the shared top bar at the top of <body> (right after the page's </style>) and mark the current page."""
    nav = NAV.replace('<!--ASOF-->', asof_txt).replace(f'data-page="{page_key}"', f'data-page="{page_key}" aria-current="page"')
    if '<!--NAV-->' in html: return html.replace('<!--NAV-->', nav, 1)
    i = html.find('</style>')
    return html if i < 0 else html[:i+8] + '\n' + nav + html[i+8:]

def seven_day(series):
    """Change over the last 7 days from a [[unix_s, price], ...] series; None if under 2 points."""
    if not series or len(series) < 2: return None
    cut = series[-1][0] - 7*86400
    base = None
    for t, v in series:
        if t <= cut: base = v
    if base is None: base = series[0][1]
    return series[-1][1] - base

def build_home():
    p28 = hist.get('p2028', {})
    mk = {m['slug']: m for m in data2028.get('markets', [])}
    # party-to-win market (added to fetch_odds MARKETS_2028); 7-day change from its own history, else from our snapshots
    party = None
    pm = mk.get('which-party-wins-2028-us-presidential-election')
    if pm:
        o = {x['name']: x for x in pm['outcomes']}
        if 'Democratic' in o and 'Republican' in o:
            hD = pm.get('history', {}).get('Democratic') or p28.get(pm['slug'], {}).get('Democratic')
            hR = pm.get('history', {}).get('Republican') or p28.get(pm['slug'], {}).get('Republican')
            party = {'market': pm['slug'], 'D': o['Democratic']['price'], 'R': o['Republican']['price'], 'dD': seven_day(hD), 'dR': seven_day(hR), 'volume': pm.get('volume')}
    # front-runners: top 3 of each nominee market, with 7d change and a 30-day sparkline from our snapshots
    def top3(slug):
        m = mk.get(slug); out = []
        if not m: return out
        for c in sorted(m['outcomes'], key=lambda x: -x['price'])[:3]:
            ser = p28.get(slug, {}).get(c['name'], [])
            cut = ser[-1][0] - 30*86400 if ser else 0
            out.append({'name': c['name'], 'price': c['price'], 'd7': seven_day(ser), 'spark': [[t, v] for t, v in ser if t >= cut][-60:]})
        return out
    front = {'dem': top3('democratic-presidential-nominee-2028'), 'dem_market': 'democratic-presidential-nominee-2028', 'dem_label': 'Democratic nominee',
             'rep': top3('republican-presidential-nominee-2028'), 'rep_market': 'republican-presidential-nominee-2028', 'rep_label': 'Republican nominee'}
    # movers: biggest 7-day moves across the candidate markets, 1 point or more
    movers = []
    for slug, m in mk.items():
        if slug == 'which-party-wins-2028-us-presidential-election': continue
        for c in m['outcomes']:
            d = seven_day(p28.get(slug, {}).get(c['name'], []))
            if d is not None and abs(d) >= 0.01:
                movers.append({'name': c['name'], 'market': slug, 'label': m.get('label', ''), 'party': c.get('party', ''), 'd7': d})
    movers.sort(key=lambda x: -abs(x['d7'])); movers = movers[:8]
    # senate 2028
    seats = s28.get('seats', {}); ctl = s28.get('control', {})
    senate2028 = {'D': ctl.get('D'), 'R': ctl.get('R'), 'seatsD': sum(1 for v in seats.values() if v.get('party') == 'D'), 'seatsR': sum(1 for v in seats.values() if v.get('party') == 'R')}
    # 2026 result + calibration
    r = {'senate': {'D': 0, 'R': 0, 'open': 0}, 'house': {'D': 0, 'R': 0, 'open': 0}, 'ctl': {}}
    favwon = resolved = upsets = 0; brier = []
    if r26:
        races = r26.get('races', {})
        for ch in ('senate', 'house', 'governor'):
            for x in races.get(ch, []):
                w = (x.get('winner') or {}).get('party'); fav = x.get('fav') or {}
                if not w:
                    if ch in r: r[ch]['open'] += 1
                    continue
                resolved += 1
                if w == fav.get('party'): favwon += 1; brier.append((1 - fav.get('price', 0))**2)
                else: upsets += 1; brier.append(fav.get('price', 0)**2)
                if ch in r and w in ('D', 'R'): r[ch][w] += 1
        b = r26.get('baseline', {}).get('senate', {})
        if b:  # seats not up in 2026 keep their holder; add this cycle's winners
            hold_up = {'D': 0, 'R': 0}
            for p in b.get('holders', {}).values():
                if p in hold_up: hold_up[p] += 1
            for p in ('D', 'R'): r['senate'][p] = b['current'][p] - hold_up[p] + r['senate'][p]
        r['ctl'] = {ch: (r26.get('control', {}).get(ch, {}).get('final') or {}).get('D') for ch in ('senate', 'house')}
    # shift: 2024 median county shift
    shift2024 = None
    if (root/'data/shift/results.json').exists():
        S = json.loads(read('data/shift/results.json'))
        a, b2 = S['president'].get('2024', {}), S['president'].get('2020', {})
        mg = lambda v: (v[0]-v[1])/v[2]*100 if v[2] else None
        ds = sorted(mg(v) - mg(b2[f]) for f, v in a.items() if f in b2 and v[2] and b2[f][2])
        if ds: shift2024 = ds[len(ds)//2]
    tiles = {'markets2028': len(mk), 'cands2028': sum(len(m['outcomes']) for m in mk.values()),
             'favWon': round(favwon/resolved*100) if resolved else None, 'brier': f'{sum(brier)/len(brier):.3f}' if brier else '—', 'upsets': upsets,
             'shift2024': shift2024 or 0,
             'earlyVotes': sum(v.get('voted', 0) for v in ev['latest'].values()), 'earlyStates': len(ev['latest']),
             'marketsTracked': sum(len(v) for v in r26.get('races', {}).values()) + sum(len(m['outcomes']) for m in mk.values()),
             'snapshots': nsnap}
    home = {'updated': data2028.get('updated') or data['updated'], 'party': party, 'senate2028': senate2028, 'result2026': r, 'front': front, 'movers': movers, 'tiles': tiles, 'site': {'referral': site.get('referral', {})}}
    write('data/home.json', json.dumps(home, ensure_ascii=False, indent=1))
    return home

home = build_home()
if (root/'src/home.html').exists():
    write('index.html', page(with_nav(read('src/home.html').replace('/*HOME*/', 'const H=' + J(home) + ';'), 'home')))
    write('2028.html', page(with_nav(body, '2028')))          # the former home page: the 2028 boards, Senate 2028 map, 2026 views
else:
    write('index.html', page(body))
for name, key in (('2026', '2026'), ('shift', 'shift'), ('data', 'data'), ('about', 'about'), ('embed', 'about')):
    p = root/f'{name}.html'
    if p.exists():
        html = p.read_text(encoding='utf-8')
        # drop the old per-page <nav> inside the title header; the top bar replaces it
        import re as _re
        html = _re.sub(r'<header>(.*?)<nav>.*?</nav>', r'<header>\1', html, count=1, flags=_re.S)
        p.write_text(with_nav(html, key), encoding='utf-8')
print(f"home: party={'yes' if home['party'] else 'pending'} · front {len(home['front']['dem'])}/{len(home['front']['rep'])} · movers {len(home['movers'])} · 2026 S {home['result2026']['senate']} H {home['result2026']['house']}")

print(f"index.html: {len(body)//1024} KB · {len(data['senate']['races'])} Senate · {len(data['house']['races'])} House · "
      f"{len(data['governor']['races'])} Governor · {len(data2028['markets'])} 2028 markets · odds as of {data['updated']} · "
      f"{len(rows)} history rows from {nsnap} snapshots · early vote: {len(ev['days'])} day(s), {len(ev['latest'])} states")
