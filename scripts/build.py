"""Assemble index.html from src/template.html + data/states.js + data/districts.js + data/odds.json."""
import json, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
tpl = (root/'src/template.html').read_text(encoding='utf-8')
states = (root/'data/states.js').read_text(encoding='utf-8')
districts = (root/'data/districts.js').read_text(encoding='utf-8')
data = json.loads((root/'data/odds.json').read_text(encoding='utf-8'))
body = tpl.replace('/*STATES*/', states).replace('/*DISTRICTS*/', districts).replace('/*DATA*/', 'const DATA=' + json.dumps(data, ensure_ascii=False, separators=(',',':')) + ';')
page = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n' + body.replace('</style>', '</style>\n</head>\n<body>', 1) + '\n</body>\n</html>\n'
(root/'index.html').write_text(page, encoding='utf-8')
print(f"index.html: {len(page)//1024} KB · {len(data['senate']['races'])} Senate races · {len(data['house']['races'])} House districts · {len(data['governor']['races'])} Governor races · odds as of {data['updated']}")
