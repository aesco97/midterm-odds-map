"""Build county-level results for the shift maps: data/shift/results.json

Sources (all public, fetched from GitHub, so this runs in the Action or locally):
  Heideman, Paul (2026). U.S. county-level election results: President, U.S. House and U.S. Senate, 1990-2024 (v1.0.0). CC BY 4.0.
      https://github.com/pmheideman/us-county-election-results  -> President 2000-2024 and House 2000-2024, 48 states
  tonmcg/US_County_Level_Election_Results_08-24 (MIT)  -> Hawaii counties and Alaska statewide, President 2008-2024

Output: {"president": {"2000": {"01001": [dem, rep, total, flag], ...}, ...}, "house": {...}, "meta": {...}}
  flag: 0 = fine; 1 = one-party or partly-unopposed House race in that county, so a shift against it means little.
  Alaska is one row, "02000" (its returns are by election district, not borough). Hawaii and Alaska start in 2008.
  FIPS harmonised to the current map: Oglala Lakota SD = 46102; Bedford City VA (51515) folded into Bedford County (51019).

Usage: python3 scripts/build_shift.py
"""
import csv, io, json, pathlib, urllib.request
root = pathlib.Path(__file__).resolve().parent.parent
OUT = root/'data/shift/results.json'
H = 'https://github.com/pmheideman/us-county-election-results/releases/download/v1.0.0/'
T = 'https://raw.githubusercontent.com/tonmcg/US_County_Level_Election_Results_08-24/master/'
UA = {'User-Agent': 'presidentl.app shift-map builder'}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
        return r.read().decode('utf-8', 'replace')

I = lambda v: int(round(float(v or 0)))  # a few sources carry apportioned (fractional) county votes

def fips(f):
    f = f.zfill(5)
    return '46102' if f == '46113' else f

res = {'president': {}, 'house': {}}
def add(office, year, f, dem, rep, tot, flag=0):
    y = res[office].setdefault(str(year), {})
    if f == '51515': f = '51019'  # Bedford City -> Bedford County
    if f in y:  # merge (Bedford)
        d, r, t, fl = y[f]; y[f] = [d+dem, r+rep, t+tot, max(fl, flag)]
    else:
        y[f] = [dem, rep, tot, flag]

print('downloading county summary (12 MB)...')
for row in csv.DictReader(io.StringIO(get(H + 'us_county_results_summary.csv'))):
    yr = int(row['year']); off = row['office']
    if yr < 2000 or off not in res: continue
    q = row['quality_flag'] or ''
    flag = 1 if ('one_party_race' in q or 'excludes_unopposed_seat' in q) else 0
    add(off, yr, fips(row['county_fips']), I(row['dem_votes']), I(row['rep_votes']), I(row['total_votes']), flag)

print('downloading Hawaii / Alaska presidential rows...')
t = csv.DictReader(io.StringIO(get(T + 'US_County_Level_Presidential_Results_08-16.csv')))
for row in t:
    f = row['fips_code'].zfill(5)
    if not f.startswith('15'): continue
    for yr in (2008, 2012, 2016):
        add('president', yr, f, int(row[f'dem_{yr}']), int(row[f'gop_{yr}']), int(row[f'total_{yr}']))
for yr in (2020, 2024):
    for row in csv.DictReader(io.StringIO(get(T + f'{yr}_US_County_Level_Presidential_Results.csv'))):
        f = row['county_fips'].zfill(5)
        if f.startswith('15'): add('president', yr, f, int(row['votes_dem']), int(row['votes_gop']), int(row['total_votes']))
# Alaska statewide, 2008-2024 (tonmcg 2016 file carries 2008/2012/2016 statewide rows; later files have AK districts summed here)
ak = {}
for row in csv.DictReader(io.StringIO(get(T + '2016_US_County_Level_Presidential_Results.csv'))):
    if row['state_abbr'] == 'AK' and row['county_name'] == 'Alaska':
        ak[int(row['combined_fips'])] = (int(float(row['votes_dem'])), int(float(row['votes_gop'])), int(float(row['total_votes'])))
# combined_fips in that file is 2013/2016/2020 for the three statewide rows (2008, 2012, 2016 results respectively)
for key, yr in ((2013, 2008), (2016, 2012), (2020, 2016)):
    if key in ak: add('president', yr, '02000', *ak[key])
for yr in (2020, 2024):
    d = r = tt = 0
    for row in csv.DictReader(io.StringIO(get(T + f'{yr}_US_County_Level_Presidential_Results.csv'))):
        if row['county_fips'].startswith('02'): d += int(row['votes_dem']); r += int(row['votes_gop']); tt += int(row['total_votes'])
    if tt: add('president', yr, '02000', d, r, tt)

res['meta'] = {
  'sources': ['Heideman (2026), U.S. county-level election results 1990-2024, v1.0.0, CC BY 4.0, doi:10.5281/zenodo.22976553',
              'tonmcg/US_County_Level_Election_Results_08-24 (Hawaii, Alaska 2008-2024)'],
  'notes': 'Values are [dem, rep, total, flag]. flag=1: House county where a race was one-party or a seat was unopposed and off the ballot. Alaska is statewide (02000). Hawaii/Alaska not available before 2008 here. Broomfield CO (08014) exists from 2004.',
  'years': {o: sorted(res[o]) for o in ('president', 'house')},
}
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(res, separators=(',', ':')), encoding='utf-8')
for o in ('president', 'house'):
    print(o, {y: len(v) for y, v in res[o].items()})
print('wrote', OUT, OUT.stat().st_size // 1024, 'KB')
