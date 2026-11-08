"""Build data/results_2026.json: every 2026 race's final pre-election odds next to how its market resolved.

  Final odds   data/odds_2026_final.json, the last feed snapshot before polls closed (2026-11-03 14:04 UTC), saved from git.
  Results      Polymarket's Gamma API: a resolved candidate market shows Yes = 1 for the winner.

Usage: python3 scripts/build_2026_archive.py        (about 500 Gamma requests the first time; afterwards only races
                                                    still pending in data/results_2026.json are asked again, so the
                                                    hourly workflow can run it until everything has resolved)
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pmlib import gamma_event, market_outcomes

root = pathlib.Path(__file__).resolve().parent.parent
final = json.loads((root/'data/odds_2026_final.json').read_text(encoding='utf-8'))
base = json.loads((root/'data/baseline.json').read_text(encoding='utf-8'))
OUT = root/'data/results_2026.json'
prev = json.loads(OUT.read_text(encoding='utf-8')) if OUT.exists() else None
def previous(ch, key):
    """A race already graded in the last run; its result cannot change, so it is not asked again."""
    if not prev: return None
    for x in prev['races'].get(ch, []):
        if (x.get('state') or x.get('id')) == key and x.get('winner'): return x
    return None

def fav(cands): return max(cands, key=lambda c: c['price'])

def resolve(slug):
    """winner {name, party} from the resolved event, plus every outcome's final Yes price; None if the event is unknown."""
    try: ev = gamma_event(slug, cache=False)
    except Exception as e:
        print(f'  {slug}: {e}'); return None
    if not ev: return None
    outs = market_outcomes(ev)
    won = [o for o in outs if o['won']]
    return {'closed': bool(ev.get('closed')), 'winner': won[0] if len(won) == 1 else None, 'outcomes': outs}

def norm(s): return ''.join(ch for ch in s.lower() if ch.isalnum())
def fill_party(winner, cands):
    """Markets that list candidates without a party label (California governor, say): take the party from our odds data."""
    if winner['party'] in ('D', 'R') or not cands: return winner
    m = next((c for c in cands if norm(c['name']) == norm(winner['name'])), None)
    if m and m.get('party'): winner = dict(winner, party=m['party'])
    return winner

def grade(fav_party, winner):
    if not winner: return None
    return fav_party == winner['party'] if winner['party'] in ('D', 'R') else False

races = {'senate': [], 'governor': [], 'house': []}
for ch in ('senate', 'governor'):
    for r in final[ch]['races']:
        old = previous(ch, r['state'])
        if old: races[ch].append(old); continue
        f = fav(r['cands']); res = resolve(r['market'])
        rec = {'state': r['state'], 'name': r['name'], 'market': r['market'], 'rating': r.get('rating'), 'volume': r.get('volume'),
               'cands': r['cands'], 'fav': {'name': f['name'], 'party': f['party'], 'price': f['price']}, 'kalshi': r.get('kalshi'),
               'holder': base[ch]['holders'].get(r['state'])}
        if res and res['winner']:
            w = fill_party(res['winner'], r['cands']); rec['winner'] = {'name': w['name'], 'party': w['party']}
            # price the market gave the eventual winner before the election
            wc = next((c for c in r['cands'] if c['party'] == w['party'] and w['party']), None) or next((c for c in r['cands'] if c['name'] == w['name']), None)
            rec['winner_price'] = wc['price'] if wc else None
            rec['correct'] = grade(f['party'], w)
            if rec.get('kalshi') and w['party'] in ('D', 'R') and rec['kalshi'].get(w['party']) is not None: rec['kalshi_winner_price'] = rec['kalshi'][w['party']]
        else:
            rec['winner'] = None; rec['correct'] = None; rec['pending'] = True
        races[ch].append(rec)
    print(f'{ch}: {sum(1 for x in races[ch] if x["winner"])}/{len(races[ch])} resolved, {sum(1 for x in races[ch] if x["correct"])} favourites won')
for r in final['house']['races']:
    old = previous('house', r['id'])
    if old: races['house'].append(old); continue
    d, R = r['D']['price'], r['R']['price']; fp = 'D' if d >= R else 'R'
    res = resolve(r['market'])
    rec = {'id': r['id'], 'market': r['market'], 'rating': r.get('rating'), 'volume': r.get('volume'), 'D': r['D'], 'R': r['R'],
           'fav': {'name': r[fp]['name'], 'party': fp, 'price': max(d, R)}}
    if r.get('other'): rec['other'] = r['other']
    if res and res['winner']:
        w = fill_party(res['winner'], [dict(r['D'], party='D'), dict(r['R'], party='R')] + ([dict(r['other'], party='')] if r.get('other') else []))
        rec['winner'] = {'name': w['name'], 'party': w['party']}
        rec['winner_price'] = r[w['party']]['price'] if w['party'] in ('D', 'R') else (r.get('other') or {}).get('price')
        rec['correct'] = grade(fp, w)
    else:
        rec['winner'] = None; rec['correct'] = None; rec['pending'] = True
    races['house'].append(rec)
print(f'house: {sum(1 for x in races["house"] if x["winner"])}/{len(races["house"])} resolved, {sum(1 for x in races["house"] if x["correct"])} favourites won')

# chamber control markets
control = {}
for ch, slug in (('senate', 'which-party-will-win-the-senate-in-2026'), ('house', 'which-party-will-win-the-house-in-2026')):
    if prev and prev.get('control', {}).get(ch, {}).get('winner'): control[ch] = prev['control'][ch]; continue
    res = resolve(slug); w = res and res['winner']
    control[ch] = {'market': slug, 'final': final[ch]['control'], 'winner': ('D' if w['name'].startswith('Dem') else 'R' if w['name'].startswith('Rep') else w['name']) if w else None}
out = {'built': __import__('datetime').date.today().isoformat(), 'final_odds_at': final['updated'], 'control': control, 'baseline': base, 'races': races,
       'sources': {'final_odds': 'PolymarketTrader.com feed (CC BY 4.0), snapshot of 2026-11-03 14:04 UTC', 'results': 'Polymarket market resolutions via the Gamma API'}}
OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print('results_2026.json written; control:', control)
