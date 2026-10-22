"""Assemble index.html from src/template.html + data/states.js + data/districts.js + data/odds.json."""
import json, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
tpl = (root/'src/template.html').read_text(encoding='utf-8')
states = (root/'data/states.js').read_text(encoding='utf-8')
districts = (root/'data/districts.js').read_text(encoding='utf-8')
data = json.loads((root/'data/odds.json').read_text(encoding='utf-8'))

def history():
    """Fold data/history/*.json into series of [unix_seconds, democratic_price] per race, oldest first."""
    from datetime import datetime, timezone
    series = {'senate': {}, 'house': {}, 'governor': {}, 'control': {'senate': [], 'house': []}}
    files = sorted((root/'data/history').glob('*.json')) if (root/'data/history').exists() else []
    for f in files:
        snap = json.loads(f.read_text(encoding='utf-8'))
        t = int(datetime.fromisoformat(snap['updated'].replace('Z', '+00:00')).astimezone(timezone.utc).timestamp())
        for ch in ('senate', 'house', 'governor'):
            for k, v in snap.get(ch, {}).items():
                if v is None: continue
                series[ch].setdefault(k, []).append([t, v])
        for ch in ('senate', 'house'):
            v = snap.get('control', {}).get(ch)
            if v is not None: series['control'][ch].append([t, v])
    return series
hist = history()
body = tpl.replace('/*STATES*/', states).replace('/*DISTRICTS*/', districts).replace('/*DATA*/', 'const DATA=' + json.dumps(data, ensure_ascii=False, separators=(',',':')) + ';\nconst HIST=' + json.dumps(hist, separators=(',',':')) + ';')
page = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' + body.replace('</style>', '</style>\n</head>\n<body>', 1) + '\n</body>\n</html>\n'
(root/'index.html').write_text(page, encoding='utf-8')
print(f"index.html: {len(page)//1024} KB · {len(data['senate']['races'])} Senate races · {len(data['house']['races'])} House districts · {len(data['governor']['races'])} Governor races · odds as of {data['updated']} · {sum(len(v) for v in hist['house'].values())//max(1,len(hist['house']))} history points/race")
