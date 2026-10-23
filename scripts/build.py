"""Assemble the site from src/ + data/.

  index.html        <- src/template.html + data/states.js + data/districts.js + data/odds.json + data/odds_2028.json + data/history/
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

def history():
    """Fold data/history/*.json into series of [unix_seconds, democratic_price] per race, oldest first."""
    series = {'senate': {}, 'house': {}, 'governor': {}, 'control': {'senate': [], 'house': []}}
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
    return series, rows, len(files)

hist, rows, nsnap = history()

# history.csv: one row per (snapshot, chamber, race); the price is the Democrat's (or the non-Republican share where no Democrat is priced)
with (root/'data/history.csv').open('w', newline='', encoding='utf-8') as f:
    w = csv.writer(f); w.writerow(['updated_utc', 'chamber', 'race', 'democratic_price']); w.writerows(rows)

def page(body):
    head = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    return head + body.replace('</style>', '</style>\n</head>\n<body>', 1) + '\n</body>\n</html>\n'

J = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
site_js = 'const SITE=' + J(site) + ';'
inject = f"const DATA={J(data)};\nconst HIST={J(hist)};\nconst DATA2028={J(data2028)};\n{site_js}"
body = read('src/template.html').replace('/*STATES*/', read('data/states.js')).replace('/*DISTRICTS*/', read('data/districts.js')).replace('/*DATA*/', inject)
write('index.html', page(body))

if (root/'src/embed.html').exists():
    write('embed.html', page(read('src/embed.html').replace('/*SITE*/', site_js)))
stats = {'snapshots': nsnap, 'rows': len(rows), 'first': rows[0][0] if rows else None, 'last': rows[-1][0] if rows else None,
         'races': len(data['senate']['races']) + len(data['house']['races']) + len(data['governor']['races']), 'updated': data['updated']}
if (root/'src/data.html').exists():
    write('data.html', page(read('src/data.html').replace('/*SITE*/', site_js + '\nconst STATS=' + J(stats) + ';')))

print(f"index.html: {len(body)//1024} KB · {len(data['senate']['races'])} Senate · {len(data['house']['races'])} House · "
      f"{len(data['governor']['races'])} Governor · {len(data2028['markets'])} 2028 markets · odds as of {data['updated']} · "
      f"{len(rows)} history rows from {nsnap} snapshots")
