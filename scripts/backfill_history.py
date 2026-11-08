"""Backfill data/history/ with one daily snapshot per day back to each market's launch, from Polymarket's CLOB.

For every 2026 race (final feed snapshot in data/odds_2026_final.json) and every 2028 candidate (data/odds_2028.json)
this looks up the market's Yes token in Gamma, pulls prices-history (daily fidelity, full range) from the CLOB, and
writes data/history/YYYY-MM-DDT00-00.json files for days before the first live snapshot, in the same shape the hourly
snapshots use (Democratic price per race; p2028 per candidate). Existing files are never touched.

Usage: python3 scripts/backfill_history.py            (about 1,100 requests the first time; Gamma responses are cached)
"""
import json, pathlib, sys, time
from datetime import datetime, timezone
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pmlib import get_json, gamma_event, market_outcomes

root = pathlib.Path(__file__).resolve().parent.parent
HIST = root/'data/history'
final = json.loads((root/'data/odds_2026_final.json').read_text(encoding='utf-8'))
odds28 = json.loads((root/'data/odds_2028.json').read_text(encoding='utf-8')) if (root/'data/odds_2028.json').exists() else {'markets': []}
existing = sorted(HIST.glob('*.json'))
first_live = existing[0].stem[:10] if existing else '2099-01-01'
print(f'first live snapshot: {first_live}; backfilling days before it')

def token_for(slug, want):
    """Yes token for the outcome matching `want`: a party letter for 2026 races, or a candidate name for 2028 markets."""
    ev = gamma_event(slug)
    if not ev: return None
    outs = market_outcomes(ev)
    if want in ('D', 'R'):
        o = next((o for o in outs if o['party'] == want), None)
    else:
        key = want.lower().replace('.', '').replace(' ', '')
        o = next((o for o in outs if o['name'].lower().replace('.', '').replace(' ', '') == key), None)
    return o['yes_token'] if o else None

def daily(token):
    """{'YYYY-MM-DD': price} from the CLOB, one point per UTC day (the last point of each day wins)."""
    data = get_json(f'https://clob.polymarket.com/prices-history?market={token}&interval=max&fidelity=1440')
    out = {}
    for p in data.get('history', []):
        d = datetime.fromtimestamp(p['t'], timezone.utc).strftime('%Y-%m-%d')
        out[d] = round(float(p['p']), 4)
    return out

days = {}  # day -> snapshot dict
def put(day, path, value):
    snap = days.setdefault(day, {'updated': day + 'T00:00:00+00:00', 'control': {}, 'senate': {}, 'governor': {}, 'house': {}, 'p2028': {}})
    node = snap
    for k in path[:-1]: node = node.setdefault(k, {})
    node[path[-1]] = value

jobs = []
for ch in ('senate', 'governor'):
    for r in final[ch]['races']: jobs.append((r['market'], 'D', (ch, r['state'])))
for r in final['house']['races']: jobs.append((r['market'], 'D', ('house', r['id'])))
jobs.append(('which-party-will-win-the-senate-in-2026', 'D', ('control', 'senate')))
jobs.append(('which-party-will-win-the-house-in-2026', 'D', ('control', 'house')))
for m in odds28['markets']:
    for o in m['outcomes']: jobs.append((m['slug'], o['name'], ('p2028', m['slug'], o['name'])))
print(f'{len(jobs)} series to pull')
done = fail = 0
for i, (slug, want, path) in enumerate(jobs, 1):
    try:
        tok = token_for(slug, want)
        if not tok: fail += 1; continue
        for day, price in daily(tok).items():
            if day < first_live: put(day, path, price)
        done += 1
    except Exception as e:
        fail += 1; print(f'  {slug} {want}: {e}')
    if i % 50 == 0: print(f'  {i}/{len(jobs)} ({fail} without data)'); time.sleep(0.5)
written = 0
for day in sorted(days):
    f = HIST / f'{day}T00-00.json'
    if f.exists(): continue
    snap = days[day]
    if not snap['p2028']: del snap['p2028']
    f.write_text(json.dumps(snap, separators=(',', ':')), encoding='utf-8'); written += 1
print(f'backfill: {done} series, {fail} without data, {written} daily snapshot files written ({min(days) if days else "-"} to {max(days) if days else "-"})')
