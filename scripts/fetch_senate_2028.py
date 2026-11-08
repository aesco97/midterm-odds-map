"""Build data/senate_2028.json: the 34 Class 3 Senate seats up in November 2028, with any Polymarket market that exists for them.

  Seats     unitedstates/congress-legislators legislators-current.json (senators with class 3). The Florida and Ohio
            seats were filled by 2026 special elections; their winners come from data/results_2026.json when available.
  Markets   Gamma public search per state ("<State> Senate 2028"); an open event with candidate markets counts.
  Control   which-party-will-win-the-senate-in-2028

Runs in the hourly workflow (about 36 requests). Usage: python3 scripts/fetch_senate_2028.py
"""
import json, pathlib, sys, urllib.parse
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from pmlib import get_json, gamma_event, market_outcomes

root = pathlib.Path(__file__).resolve().parent.parent
NAMES = {"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"}

def main():
    cur = get_json('https://unitedstates.github.io/congress-legislators/legislators-current.json', timeout=120)
    seats = {}
    for m in cur:
        t = m['terms'][-1]
        if t['type'] != 'sen' or t.get('class') != 3: continue
        name = m['name'].get('official_full') or (m['name']['first'] + ' ' + m['name']['last'])
        party = (t.get('party') or '')[:1]
        if party == 'I' and t.get('caucus'): party = t['caucus'][:1]
        seats[t['state']] = {'incumbent': name, 'party': party, 'term_end': t['end'], 'special_2026': t['end'] < '2027-01-01'}
    # seats filled by a 2026 special election: the winner is the incumbent for 2028
    res_path = root/'data/results_2026.json'
    if res_path.exists():
        res = json.loads(res_path.read_text(encoding='utf-8'))
        for r in res['races']['senate']:
            if r['state'] in seats and seats[r['state']]['special_2026'] and r.get('winner'):
                seats[r['state']].update({'incumbent': r['winner']['name'], 'party': r['winner']['party'], 'note': 'won the 2026 special election'})
    # per-state markets, if any exist yet
    markets = {}
    for st in sorted(seats):
        try:
            q = urllib.parse.quote(f'{NAMES[st]} Senate 2028')
            found = get_json(f'https://gamma-api.polymarket.com/public-search?q={q}&limit_per_type=10')
            events = found.get('events', []) if isinstance(found, dict) else found
            for e in events:
                title = (e.get('title') or '').lower()
                if e.get('closed') or '2028' not in title or 'senate' not in title or NAMES[st].lower() not in title: continue
                ev = gamma_event(e['slug'], cache=False)
                outs = [o for o in market_outcomes(ev) if o['yes_price'] is not None]
                if len(outs) < 2: continue
                markets[st] = {'market': e['slug'], 'title': e.get('title'), 'volume': round(float(e.get('volume') or 0)),
                               'cands': [{'name': o['name'], 'party': o['party'], 'price': round(o['yes_price'], 4)} for o in sorted(outs, key=lambda o: -o['yes_price'])[:6]]}
                break
        except Exception as e:
            print(f'  {st}: {e}')
    # chamber control
    control = None
    try:
        ev = gamma_event('which-party-will-win-the-senate-in-2028', cache=False)
        d = {o['name']: o['yes_price'] for o in market_outcomes(ev)}
        control = {'market': 'which-party-will-win-the-senate-in-2028', 'D': d.get('Democratic Party'), 'R': d.get('Republican Party')}
    except Exception as e:
        print(f'  control: {e}')
    out = {'updated': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'seats': seats, 'markets': markets, 'control': control}
    (root/'data/senate_2028.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    d = sum(1 for s in seats.values() if s['party'] == 'D'); r = sum(1 for s in seats.values() if s['party'] == 'R')
    print(f'senate_2028.json: {len(seats)} seats ({d} D, {r} R) · {len(markets)} with a market · control {control}')

if __name__ == '__main__':
    main()
