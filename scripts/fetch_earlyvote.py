"""Refresh early-vote turnout data (runs in the hourly GitHub Action, which has full network access).

  data/earlyvote/YYYY-MM-DD.json   one snapshot per UTC day of the UF Election Lab 2026 tracker (US.csv), latest fetch wins
  data/earlyvote_ref.json          static reference (2018/2022 turnout, 2022 early-vote finals); only the `tx` series is refreshed here

Sources
  UF Election Lab 2026 early vote tracker  https://election.lab.ufl.edu/early-vote/2026-early-voting/  (US.csv behind the map)
  Texas day-by-day, 2018/2022/2024/2026    https://github.com/Seeker-Cliff/tx-early-vote-live  (Texas SOS daily turnout)
  Wayback Machine                          used once to backfill UF snapshots for days before this script first ran

Usage: python3 scripts/fetch_earlyvote.py [--backfill]
"""
import csv, io, json, pathlib, sys, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

root = pathlib.Path(__file__).resolve().parent.parent
EV = root/'data/earlyvote'; EV.mkdir(exist_ok=True)
REF = root/'data/earlyvote_ref.json'
UF = 'https://election.lab.ufl.edu/data-downloads/earlyvote/2026/US.csv'
TX_HIST = 'https://raw.githubusercontent.com/Seeker-Cliff/tx-early-vote-live/main/data/history/daily_history.csv'
TX_2026 = 'https://raw.githubusercontent.com/Seeker-Cliff/tx-early-vote-live/main/data/daily_2026.csv'
KEEP = ['last_update', 'data_source', 'request_all', 'request_dem', 'request_rep', 'request_none',
        'accept_all', 'accept_dem', 'accept_rep', 'accept_none', 'inperson_all', 'inperson_dem', 'inperson_rep', 'inperson_none',
        'voted_all', 'voted_dem', 'voted_rep', 'voted_none']
UA = {'User-Agent': 'presidentl.app early-vote tracker (github.com/aesco97/midterm-odds-map)'}

def get(url, timeout=60):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
            return r.read().decode('utf-8', 'replace')
    except urllib.error.URLError as e:  # python.org builds often lack root certs; curl has its own
        if 'CERTIFICATE_VERIFY_FAILED' not in str(e): raise
        import subprocess
        out = subprocess.run(['curl', '-sSL', '--max-time', str(timeout), '-A', UA['User-Agent'], url], check=True, capture_output=True)
        return out.stdout.decode('utf-8', 'replace')

def parse_uf(text):
    """UF US.csv -> {state_abbv: {kept fields}}; dates normalised to YYYY-MM-DD, numbers to int."""
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        st = (row.get('state_abbv') or '').strip()
        if not st: continue
        rec = {}
        for k in KEEP:
            v = (row.get(k) or '').strip()
            if k == 'last_update':
                try: m, d, y = v.split('/'); v = f'{int(y)}-{int(m):02d}-{int(d):02d}'
                except ValueError: pass
            elif k != 'data_source':
                try: v = int(float(v or 0))
                except ValueError: v = 0
            rec['source' if k == 'data_source' else k] = v
        out[st] = rec
    return out

def write_snapshot(states, fetched_iso, day):
    path = EV/f'{day}.json'
    snap = {'fetched': fetched_iso, 'source': UF, 'states': states}
    path.write_text(json.dumps(snap, separators=(',', ':')), encoding='utf-8')
    return path

def fetch_today():
    now = datetime.now(timezone.utc)
    states = parse_uf(get(UF))
    if len(states) < 30: raise SystemExit(f'UF feed returned only {len(states)} states; not saving')
    p = write_snapshot(states, now.strftime('%Y-%m-%dT%H:%M:%SZ'), now.strftime('%Y-%m-%d'))
    print(f'earlyvote: {p.name} · {len(states)} states · {sum(s["voted_all"] for s in states.values()):,} ballots')

def backfill():
    """Fill missing days from the Wayback Machine, one capture per day (closest to 23:00 UTC), oldest first."""
    have = {p.stem for p in EV.glob('????-??-??.json')}
    day = datetime(2026, 10, 1, tzinfo=timezone.utc)
    today = datetime.now(timezone.utc).date()
    n = 0
    while day.date() < today:
        d = day.strftime('%Y-%m-%d')
        if d not in have:
            try:
                q = 'https://archive.org/wayback/available?' + urllib.parse.urlencode({'url': UF, 'timestamp': day.strftime('%Y%m%d2300')})
                info = json.loads(get(q, 30)).get('archived_snapshots', {}).get('closest')
                if info and info.get('available') and info['timestamp'][:8] == day.strftime('%Y%m%d'):
                    raw = get(info['url'].replace('/web/', '/web/') .replace(info['timestamp'], info['timestamp'] + 'id_'), 60)
                    states = parse_uf(raw)
                    if len(states) >= 30:
                        write_snapshot(states, datetime.strptime(info['timestamp'], '%Y%m%d%H%M%S').strftime('%Y-%m-%dT%H:%M:%SZ') + ' (wayback)', d); n += 1
            except Exception as e:
                print(f'backfill {d}: {e}')
        day += timedelta(days=1)
    if n: print(f'earlyvote: backfilled {n} day(s) from the Wayback Machine')

def texas():
    """Statewide cumulative in-person early vote per day of the EV period, 2018/2022/2024 from history, 2026 from the live file."""
    ref = json.loads(REF.read_text(encoding='utf-8')) if REF.exists() else {}
    tx = ref.get('tx', {})
    try:
        best = {}
        for r in csv.DictReader(io.StringIO(get(TX_HIST))):
            k = (r['year'], int(r['day_n'])); v = int(float(r.get('cum_in_person') or 0))
            if v > best.get(k, 0): best[k] = v   # the file carries a STATEWIDE row per day; the max per day is that row
        series = {}
        for (y, n), v in sorted(best.items()): series.setdefault(y, []).append([n, v])
        tx.update(series)
    except Exception as e:
        print(f'texas history: {e}')
    try:
        agg, dates, total = {}, {}, {}
        for r in csv.DictReader(io.StringIO(get(TX_2026))):
            n = int(r['day_n']); ip = int(float(r.get('cum_in_person') or 0)); m = int(float(r.get('cum_mail') or 0))
            dates[n] = r['date']
            if (r.get('county') or '').upper() in ('STATEWIDE', 'TOTAL', 'STATE', 'TEXAS'): total[n] = [ip, m]
            else: a = agg.setdefault(n, [0, 0]); a[0] += ip; a[1] += m
        tx['2026'] = [[n, dates[n]] + (total.get(n) or agg[n]) for n in sorted(set(agg) | set(total))]
    except Exception as e:
        print(f'texas 2026: {e}')
    tx['note'] = ('Texas in-person early vote, cumulative by day of the early-voting period (Day 1 = first day). 2018 covers the 30 largest '
                  'counties only; 2022, 2024 and 2026 all 254. Source: github.com/Seeker-Cliff/tx-early-vote-live (Texas SOS daily turnout).')
    ref['tx'] = tx
    REF.write_text(json.dumps(ref, indent=1), encoding='utf-8')
    print(f"earlyvote: Texas series {', '.join(f'{y}:{len(v)}d' for y, v in tx.items() if isinstance(v, list))}")

if __name__ == '__main__':
    fetch_today()
    if '--backfill' in sys.argv: backfill()  # opt-in: the Wayback API rate-limits and rarely has these CSVs, so don't do it hourly
    texas()
