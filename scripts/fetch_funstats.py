"""Build data/funstats.json: the age of Congress over time against the country it represents.

  Ages      unitedstates/congress-legislators (legislators-historical.json + legislators-current.json): every member's
            birthday and terms. For each Congress we take the members seated at its start (March 4 until 1933, Jan 3
            since 1935) and compute the mean and median age per chamber.
  Life      Our World in Data, "Life expectancy at birth" (UN WPP / HMD), United States, 1880-.
  Median    US Census Bureau: median age of the US population, decennial 1900-2020 plus ACS 2024 (hand-entered below).

Run it once per Congress (or whenever): python3 scripts/fetch_funstats.py [historical.json current.json life.csv]
"""
import csv, io, json, pathlib, statistics, subprocess, sys, urllib.request
from datetime import date, timedelta

root = pathlib.Path(__file__).resolve().parent.parent
SRC = {
    'hist': 'https://unitedstates.github.io/congress-legislators/legislators-historical.json',
    'cur': 'https://unitedstates.github.io/congress-legislators/legislators-current.json',
    'life': 'https://ourworldindata.org/grapher/life-expectancy.csv?v=1&csvType=filtered&useColumnShortNames=true&country=~USA',
}
# Median age of the US population (Census: decennial censuses; 2024 from the ACS 1-year estimate)
MEDIAN_AGE = [[1900, 22.9], [1910, 24.1], [1920, 25.3], [1930, 26.5], [1940, 29.0], [1950, 30.2], [1960, 29.5], [1970, 28.1],
              [1980, 30.0], [1990, 32.9], [2000, 35.3], [2010, 37.2], [2020, 38.8], [2024, 39.1]]
UA = {'User-Agent': 'presidentl.app fun stats (github.com/aesco97/midterm-odds-map)'}

def get(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r: return r.read().decode('utf-8')
    except urllib.error.URLError as e:  # python.org builds often lack root certs; curl has its own
        if 'CERTIFICATE_VERIFY_FAILED' not in str(e): raise
        return subprocess.run(['curl', '-sSL', '-A', UA['User-Agent'], url], check=True, capture_output=True).stdout.decode('utf-8')

def congress_start(n):
    year = 1789 + 2 * (n - 1)
    return date(year, 1, 3) if year >= 1935 else date(year, 3, 4)

def age_at(birthday, d):
    b = date.fromisoformat(birthday)
    return (d - b).days / 365.25

def main():
    if len(sys.argv) == 4:
        hist, cur, life_csv = (pathlib.Path(p).read_text(encoding='utf-8') for p in sys.argv[1:4])
    else:
        hist, cur, life_csv = get(SRC['hist']), get(SRC['cur']), get(SRC['life'])
    members = json.loads(hist) + json.loads(cur)
    today = date.today()
    n_max = (today.year - 1789) // 2 + 1  # Congress in session today
    out = []
    for n in range(1, n_max + 1):
        d = congress_start(n); late = d + timedelta(days=365)  # early Congresses first met months after March 4, so count anyone seated in the first year, aged at the start date
        ages = {'rep': [], 'sen': []}; nobday = {'rep': 0, 'sen': 0}
        for m in members:
            bday = m.get('bio', {}).get('birthday')
            for t in m['terms']:
                if t['type'] not in ages: continue
                ts, te = date.fromisoformat(t['start']), date.fromisoformat(t['end'])
                if ts <= late and te > d:
                    if bday: ages[t['type']].append(age_at(bday, d))
                    else: nobday[t['type']] += 1
                    break
        rec = {'n': n, 'year': d.year}
        for ch, key in (('rep', 'house'), ('sen', 'senate')):
            a = ages[ch]
            if len(a) >= 20:
                rec[key] = {'mean': round(statistics.mean(a), 1), 'median': round(statistics.median(a), 1), 'n': len(a), 'no_birthday': nobday[ch]}
        out.append(rec)
    # life expectancy
    life = []
    for row in csv.DictReader(io.StringIO(life_csv)):
        if row.get('code') == 'USA' and row.get('life_expectancy_0'):
            life.append([int(row['year']), round(float(row['life_expectancy_0']), 1)])
    life.sort()
    # today: the sitting Congress at today's ages
    sitting = []
    for m in json.loads(cur):
        bday = m.get('bio', {}).get('birthday'); t = m['terms'][-1]
        if not bday or t['type'] not in ('rep', 'sen'): continue
        sitting.append({'name': m['name'].get('official_full') or (m['name']['first'] + ' ' + m['name']['last']), 'age': round(age_at(bday, today), 1),
                        'chamber': 'House' if t['type'] == 'rep' else 'Senate', 'state': t['state'], 'party': t.get('party', '')[:1]})
    sitting.sort(key=lambda x: -x['age'])
    le_now = life[-1][1] if life else None
    def chamber_stats(ch):
        a = [x['age'] for x in sitting if x['chamber'] == ch]
        return {'mean': round(statistics.mean(a), 1), 'median': round(statistics.median(a), 1), 'n': len(a),
                'over70': sum(1 for v in a if v >= 70), 'over_le': sum(1 for v in a if le_now and v >= le_now), 'under40': sum(1 for v in a if v < 40)}
    todayrec = {'date': today.isoformat(), 'house': chamber_stats('House'), 'senate': chamber_stats('Senate'),
                'oldest': sitting[:5], 'youngest': sitting[-5:][::-1], 'life_expectancy': life[-1] if life else None}
    data = {'built': today.isoformat(), 'congress': out, 'life': life, 'median_age_us': MEDIAN_AGE, 'today': todayrec,
            'sources': {'ages': 'unitedstates/congress-legislators (public domain)', 'life': 'Our World in Data, life expectancy at birth, United States (UN WPP; HMD before 1950)',
                        'median_age': 'US Census Bureau, decennial censuses and ACS 2024'}}
    (root/'data/funstats.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    last = [r for r in out if 'house' in r][-1]
    print(f"funstats.json: {len(out)} Congresses · latest {last['n']}th ({last['year']}): House {last['house']['mean']} · Senate {last['senate']['mean']} · life expectancy {life[-1]} · today House {todayrec['house']['mean']} Senate {todayrec['senate']['mean']} · oldest {sitting[0]['name']} {sitting[0]['age']}")

if __name__ == '__main__':
    main()
